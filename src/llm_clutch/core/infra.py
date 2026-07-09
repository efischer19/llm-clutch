"""Infrastructure manager for cluster health checks."""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


@dataclass
class NodeStatus:
    """Status of a cluster node health check.

    Attributes:
        ip: IP address of the node.
        reachable: Whether the node is reachable via TCP socket probe.
        latency_ms: Latency in milliseconds for the TCP probe, or None if unreachable.
        checked_at: Timestamp when the check was performed.
    """

    ip: str
    reachable: bool
    latency_ms: float | None
    checked_at: datetime


class InfraManager:
    """Manager for cluster infrastructure health checks.

    Verifies that worker nodes on the cluster are reachable before
    any model shift is attempted, preventing shifts into a degraded cluster.
    """

    DEFAULT_TIMEOUT_SECONDS = 5
    DEFAULT_PORT = 52415

    def __init__(
        self,
        node_ips: list[str],
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        port: int = DEFAULT_PORT,
    ) -> None:
        """Initialize the InfraManager with target node IPs.

        Args:
            node_ips: List of target node IP addresses to monitor.
            timeout_seconds: Timeout in seconds for each node check. Defaults to 5.
            port: TCP port to probe on each node. Defaults to 52415 (Exo API port).
        """
        self.node_ips = node_ips
        self.timeout_seconds = timeout_seconds
        self.port = port

    async def check_node(self, ip: str) -> NodeStatus:
        """Check if a single node is reachable via TCP socket probe.

        Attempts to establish a TCP connection to the specified IP and port.
        Includes automatic retry logic with exponential backoff on transient
        network failures. Returns a NodeStatus regardless of success or failure.

        Args:
            ip: IP address of the node to check.

        Returns:
            NodeStatus object containing reachability and latency information.
        """
        try:
            return await self._check_node_with_retry(ip)
        except (OSError, TimeoutError):
            checked_at = datetime.now()
            return NodeStatus(
                ip=ip,
                reachable=False,
                latency_ms=None,
                checked_at=checked_at,
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((OSError, TimeoutError)),
        reraise=True,
    )
    async def _check_node_with_retry(self, ip: str) -> NodeStatus:
        """Internal method with retry logic for TCP socket probes.

        Uses exponential backoff with timing: 1s, 2s, 4s, up to 10s max
        between attempts. This provides adaptive retry behavior for
        transient network failures.

        Args:
            ip: IP address of the node to check.

        Returns:
            NodeStatus object containing reachability and latency information.

        Raises:
            OSError or TimeoutError after all retries are exhausted.
        """
        start_time = time.time()

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, self.port),
            timeout=self.timeout_seconds,
        )
        writer.close()
        await writer.wait_closed()

        latency_ms = (time.time() - start_time) * 1000
        checked_at = datetime.now()
        status = NodeStatus(
            ip=ip,
            reachable=True,
            latency_ms=latency_ms,
            checked_at=checked_at,
        )
        logger.info(
            "node_check_success",
            ip=ip,
            latency_ms=round(latency_ms, 2),
            checked_at=checked_at.isoformat(),
        )
        return status

    async def check_all_nodes(self) -> list[NodeStatus]:
        """Check all configured nodes concurrently using asyncio.gather.

        Performs TCP socket probes on all configured nodes in parallel
        and collects the results. Does not raise exceptions on individual
        node failures; instead returns partial results.

        Returns:
            List of NodeStatus objects for all nodes, one per configured IP.
        """
        tasks = [self.check_node(ip) for ip in self.node_ips]
        return await asyncio.gather(*tasks)

    async def verify_topology(self, min_nodes: int = 1) -> bool:
        """Verify that at least min_nodes are reachable.

        Checks all configured nodes and returns True only if at least
        min_nodes are reachable. Useful for validating cluster readiness
        before attempting model shifts.

        Args:
            min_nodes: Minimum number of reachable nodes required. Defaults to 1.

        Returns:
            True if at least min_nodes are reachable, False otherwise.
        """
        statuses = await self.check_all_nodes()
        reachable_count = sum(1 for s in statuses if s.reachable)
        is_healthy = reachable_count >= min_nodes

        logger.info(
            "topology_verified",
            reachable_nodes=reachable_count,
            total_nodes=len(self.node_ips),
            min_required=min_nodes,
            is_healthy=is_healthy,
        )

        return is_healthy
