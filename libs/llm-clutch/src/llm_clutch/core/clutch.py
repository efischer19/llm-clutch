"""Clutch engine orchestrator for LLM model management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import structlog

from llm_clutch.backend.base import ModelBackend
from llm_clutch.backend.exceptions import (
    BackendError,
    ModelLoadError,
    ModelUnloadError,
)
from llm_clutch.core.infra import InfraManager

logger = structlog.get_logger(__name__)


class EngineState(Enum):
    """States representing the engine's lifecycle."""

    IDLE = "idle"
    SHIFTING = "shifting"
    ENGAGED = "engaged"
    ERROR = "error"


@dataclass
class ShiftResult:
    """Result of a shift operation (upshift or downshift).

    Attributes:
        success: Whether the shift completed successfully.
        previous_model: The model that was active before the shift.
        new_model: The model that is active after the shift.
        error: Error message if the shift failed, None otherwise.
        timestamp: When the shift was attempted.
    """

    success: bool
    previous_model: str | None
    new_model: str | None
    error: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now())


@dataclass
class EngineStatus:
    """Current status of the clutch engine.

    Attributes:
        state: Current engine state (IDLE, SHIFTING, ENGAGED, ERROR).
        active_model: The currently loaded model, or None.
        cluster_health: Whether the cluster is healthy (at least min_nodes reachable).
        last_shift_result: Result of the last shift operation, or None.
    """

    state: EngineState
    active_model: str | None
    cluster_health: bool
    last_shift_result: ShiftResult | None = None


class LLMClutch:
    """Orchestrator that ties ModelBackend and InfraManager together.

    Exposes the transmission-metaphor API (rev_match, disengage, engage,
    upshift, downshift) to manage model loading and unloading with
    automatic cluster health verification and atomic shift operations.
    """

    def __init__(
        self,
        backend: ModelBackend,
        infra_manager: InfraManager,
        min_nodes: int = 1,
    ) -> None:
        """Initialize the clutch engine.

        Args:
            backend: The ModelBackend instance for managing models.
            infra_manager: The InfraManager instance for cluster health checks.
            min_nodes: Minimum number of reachable nodes required for operations.
                Defaults to 1.

        Raises:
            ValueError: If min_nodes is less than 1.
        """
        if min_nodes < 1:
            msg = "min_nodes must be at least 1"
            raise ValueError(msg)

        self.backend = backend
        self.infra_manager = infra_manager
        self.min_nodes = min_nodes

        self._state = EngineState.IDLE
        self._active_model: str | None = None
        self._cluster_health = False
        self._last_shift_result: ShiftResult | None = None

        logger.info(
            "clutch_initialized",
            backend=backend.backend_name,
            min_nodes=min_nodes,
        )

    async def rev_match(self, required_ram: int) -> bool:
        """Check if the cluster topology can accept a model of the given size.

        Verifies that:
        1. The cluster topology is healthy (at least min_nodes are reachable)
        2. There is sufficient available memory

        Args:
            required_ram: Required memory in bytes for the model.

        Returns:
            True if the cluster can accept the model, False otherwise.
        """
        logger.info(
            "rev_match_started",
            required_ram=required_ram,
            min_nodes=self.min_nodes,
        )

        # Check cluster topology
        topology_healthy = await self.infra_manager.verify_topology(self.min_nodes)
        self._cluster_health = topology_healthy

        if not topology_healthy:
            logger.warning(
                "rev_match_failed_topology",
                reason="cluster_nodes_unreachable",
                required_ram=required_ram,
            )
            return False

        # Check available memory
        try:
            available_memory = await self.backend.get_available_memory()
        except BackendError as e:
            logger.error(
                "rev_match_failed_backend",
                reason="could_not_get_available_memory",
                error=str(e),
            )
            return False

        can_fit = available_memory >= required_ram
        logger.info(
            "rev_match_completed",
            available_memory=available_memory,
            required_ram=required_ram,
            can_fit=can_fit,
        )

        return can_fit

    async def disengage(self) -> None:
        """Unload the currently active model with safety checks.

        Raises:
            ModelUnloadError: If the unload operation fails.
        """
        if self._active_model is None:
            logger.info("disengage_skipped", reason="no_active_model")
            return

        previous_model = self._active_model
        logger.info(
            "disengage_started",
            active_model=previous_model,
        )

        try:
            await self.backend.unload_model()
            self._active_model = None
            logger.info(
                "disengage_success",
                previous_model=previous_model,
            )
        except ModelUnloadError as e:
            error_msg = f"Failed to disengage: {str(e)}"
            logger.error(
                "disengage_failed",
                error=error_msg,
                active_model=previous_model,
                exc_info=True,
            )
            raise

    async def engage(self, model_name: str) -> None:
        """Load a model with pre-flight validation.

        Args:
            model_name: Name of the model to load.

        Raises:
            ModelLoadError: If the load operation fails.
        """
        logger.info(
            "engage_started",
            model_name=model_name,
        )

        try:
            await self.backend.load_model(model_name)
            self._active_model = model_name
            logger.info(
                "engage_success",
                model_name=model_name,
            )
        except ModelLoadError as e:
            error_msg = f"Failed to engage: {str(e)}"
            logger.error(
                "engage_failed",
                model_name=model_name,
                error=error_msg,
                exc_info=True,
            )
            raise

    async def upshift(self, heavy_model: str, required_ram: int) -> None:
        """Orchestrate a shift to a heavier model.

        Atomically performs: rev_match() → disengage() → engage().
        If any step fails, logs the failure state and raises an exception.

        If disengage succeeds but engage fails, logs a CRITICAL error
        indicating the cluster is now model-less.

        Args:
            heavy_model: Name of the heavy model to load.
            required_ram: Required memory in bytes for the model.

        Raises:
            ValueError: If rev_match fails (insufficient resources).
            ModelUnloadError: If disengage fails.
            ModelLoadError: If engage fails.
        """
        previous_model = self._active_model
        logger.info(
            "upshift_started",
            heavy_model=heavy_model,
            required_ram=required_ram,
            previous_model=previous_model,
        )

        try:
            # Step 1: Rev match (pre-condition check)
            if not await self.rev_match(required_ram):
                error_msg = (
                    f"Cannot upshift to {heavy_model}: "
                    f"insufficient resources (required {required_ram} bytes)"
                )
                logger.error(
                    "upshift_failed_rev_match",
                    heavy_model=heavy_model,
                    required_ram=required_ram,
                )
                self._last_shift_result = ShiftResult(
                    success=False,
                    previous_model=previous_model,
                    new_model=None,
                    error=error_msg,
                )
                raise ValueError(error_msg)

            # Rev match passed, now we're committed to the shift
            self._state = EngineState.SHIFTING

            # Step 2: Disengage
            await self.disengage()

            # Step 3: Engage
            await self.engage(heavy_model)

            # Success
            logger.info(
                "upshift_success",
                previous_model=previous_model,
                new_model=heavy_model,
            )
            self._state = EngineState.ENGAGED
            self._last_shift_result = ShiftResult(
                success=True,
                previous_model=previous_model,
                new_model=heavy_model,
            )

        except ValueError:
            # Re-raise ValueError from rev_match failure without changing state
            raise
        except Exception as e:
            logger.error(
                "upshift_failed",
                heavy_model=heavy_model,
                previous_model=previous_model,
                error=str(e),
                exc_info=True,
            )

            # If we disengaged but failed to engage, we're in a critical state
            if previous_model != self._active_model and self._active_model is None:
                logger.critical(
                    "upshift_critical_state",
                    message="cluster_is_now_model_less",
                    previous_model=previous_model,
                    current_active_model=self._active_model,
                )

            self._state = EngineState.ERROR
            self._last_shift_result = ShiftResult(
                success=False,
                previous_model=previous_model,
                new_model=heavy_model,
                error=str(e),
            )
            raise

    async def downshift(self, light_model: str, required_ram: int) -> None:
        """Orchestrate a shift to a lighter model.

        Atomically performs: rev_match() → disengage() → engage().
        If any step fails, logs the failure state and raises an exception.

        If disengage succeeds but engage fails, logs a CRITICAL error
        indicating the cluster is now model-less.

        Args:
            light_model: Name of the light model to load.
            required_ram: Required memory in bytes for the model.

        Raises:
            ValueError: If rev_match fails (insufficient resources).
            ModelUnloadError: If disengage fails.
            ModelLoadError: If engage fails.
        """
        previous_model = self._active_model
        logger.info(
            "downshift_started",
            light_model=light_model,
            required_ram=required_ram,
            previous_model=previous_model,
        )

        try:
            # Step 1: Rev match (pre-condition check)
            if not await self.rev_match(required_ram):
                error_msg = (
                    f"Cannot downshift to {light_model}: "
                    f"insufficient resources (required {required_ram} bytes)"
                )
                logger.error(
                    "downshift_failed_rev_match",
                    light_model=light_model,
                    required_ram=required_ram,
                )
                self._last_shift_result = ShiftResult(
                    success=False,
                    previous_model=previous_model,
                    new_model=None,
                    error=error_msg,
                )
                raise ValueError(error_msg)

            # Rev match passed, now we're committed to the shift
            self._state = EngineState.SHIFTING

            # Step 2: Disengage
            await self.disengage()

            # Step 3: Engage
            await self.engage(light_model)

            # Success
            logger.info(
                "downshift_success",
                previous_model=previous_model,
                new_model=light_model,
            )
            self._state = EngineState.ENGAGED
            self._last_shift_result = ShiftResult(
                success=True,
                previous_model=previous_model,
                new_model=light_model,
            )

        except ValueError:
            # Re-raise ValueError from rev_match failure without changing state
            raise
        except Exception as e:
            logger.error(
                "downshift_failed",
                light_model=light_model,
                previous_model=previous_model,
                error=str(e),
                exc_info=True,
            )

            # If we disengaged but failed to engage, we're in a critical state
            if previous_model != self._active_model and self._active_model is None:
                logger.critical(
                    "downshift_critical_state",
                    message="cluster_is_now_model_less",
                    previous_model=previous_model,
                    current_active_model=self._active_model,
                )

            self._state = EngineState.ERROR
            self._last_shift_result = ShiftResult(
                success=False,
                previous_model=previous_model,
                new_model=light_model,
                error=str(e),
            )
            raise

    def status(self) -> EngineStatus:
        """Return the current state of the clutch engine.

        Returns:
            EngineStatus: Current engine state, active model, cluster health,
            and last shift result.
        """
        logger.info(
            "status_requested",
            current_state=self._state.value,
            active_model=self._active_model,
            cluster_health=self._cluster_health,
        )

        return EngineStatus(
            state=self._state,
            active_model=self._active_model,
            cluster_health=self._cluster_health,
            last_shift_result=self._last_shift_result,
        )
