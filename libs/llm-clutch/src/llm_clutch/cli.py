"""Click-based CLI for llm-clutch (per ADR-011)."""

import asyncio
import json
import tomllib
from pathlib import Path
from typing import Any

import click
import structlog

from llm_clutch.backend.exo import ExoBackend
from llm_clutch.core.clutch import LLMClutch
from llm_clutch.core.infra import InfraManager

logger = structlog.get_logger(__name__)


def _load_config(config_path: str | None) -> dict[str, Any]:
    """Load configuration from TOML file.

    Args:
        config_path: Optional path to config file. If not provided,
            uses default path ~/.config/llm-clutch/config.toml.

    Returns:
        Dictionary of configuration values, or empty dict if file not found.
    """
    if config_path:
        path = Path(config_path)
    else:
        path = Path.home() / ".config" / "llm-clutch" / "config.toml"

    if not path.exists():
        return {}

    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logger.error("config_load_failed", path=str(path), error=str(e))
        return {}


def _create_clutch(
    config: dict[str, Any], node_ips: list[str] | None = None
) -> LLMClutch:
    """Create and return an LLMClutch instance from configuration.

    Args:
        config: Configuration dictionary.
        node_ips: Optional list of node IPs to override config.

    Returns:
        LLMClutch instance.

    Raises:
        ValueError: If required configuration is missing.
    """
    # Get node IPs
    if node_ips is None:
        node_ips = config.get("node_ips", [])

    if not node_ips:
        raise ValueError(
            "No node IPs configured. Specify in config file or use --node-ips."
        )

    # Get Exo API URL
    exo_api_url = config.get("exo_api_url", "http://10.0.0.1:52415")

    # Create backend and infra manager
    backend = ExoBackend(base_url=exo_api_url)
    infra_manager = InfraManager(node_ips=node_ips)

    return LLMClutch(backend=backend, infra_manager=infra_manager)


@click.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=False),
    help=(
        "Path to configuration file (TOML). "
        "Defaults to ~/.config/llm-clutch/config.toml."
    ),
)
@click.pass_context
def clutch(ctx: click.Context, config_path: str | None) -> None:
    """LLM Clutch CLI for managing LLM model shifts in clusters.

    This CLI provides commands for checking cluster status, triggering model
    shifts (upshift/downshift), and running diagnostics.
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = _load_config(config_path)


@clutch.command()
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON for machine parsing.",
)
@click.pass_context
def status(ctx: click.Context, output_json: bool) -> None:
    """Display current cluster state: active model, node health, cluster status.

    Shows the current engine state, active model, cluster health,
    and the result of the last shift operation (if any).
    """
    try:
        config = ctx.obj["config"]
        clutch_engine = _create_clutch(config)

        # Get status
        engine_status = clutch_engine.status()

        # Format output
        if output_json:
            from dataclasses import asdict

            output_data = asdict(engine_status)
            output_data["state"] = engine_status.state.value
            if engine_status.last_shift_result:
                output_data["last_shift_result"] = asdict(
                    engine_status.last_shift_result
                )
                output_data["last_shift_result"]["timestamp"] = (
                    engine_status.last_shift_result.timestamp.isoformat()
                )
            click.echo(json.dumps(output_data, indent=2))
        else:
            # Human-readable format
            click.echo(f"Engine State: {engine_status.state.value}")
            click.echo(f"Active Model: {engine_status.active_model or 'None'}")
            health_status = (
                "Healthy" if engine_status.cluster_health else "Unhealthy"
            )
            click.echo(f"Cluster Health: {health_status}")

            if engine_status.last_shift_result:
                result = engine_status.last_shift_result
                status_str = "✓ Success" if result.success else "✗ Failed"
                click.echo(f"Last Shift: {status_str}")
                if result.previous_model:
                    click.echo(f"  Previous: {result.previous_model}")
                if result.new_model:
                    click.echo(f"  New: {result.new_model}")
                if result.error:
                    click.echo(f"  Error: {result.error}")

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None
    except Exception as e:
        click.echo(f"Error getting status: {e}", err=True)
        logger.error("status_error", error=str(e), exc_info=True)
        raise SystemExit(1) from None


@clutch.command()
@click.option(
    "--model",
    required=True,
    help="Name of the heavy model to load.",
)
@click.option(
    "--ram",
    required=True,
    type=int,
    help="Required RAM in bytes for the model.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON for machine parsing.",
)
@click.pass_context
def upshift(ctx: click.Context, model: str, ram: int, output_json: bool) -> None:
    """Trigger an upshift to a heavier model.

    Performs an atomic shift: rev_match → disengage → engage.
    If any step fails, the operation is rolled back with clear error messaging.
    """
    try:
        config = ctx.obj["config"]
        clutch_engine = _create_clutch(config)

        # Run the async upshift operation
        asyncio.run(clutch_engine.upshift(heavy_model=model, required_ram=ram))

        # Get updated status
        engine_status = clutch_engine.status()

        if output_json:

            result = engine_status.last_shift_result
            output_data = {
                "success": result.success if result else False,
                "model": model,
                "active_model": engine_status.active_model,
                "error": result.error if result else None,
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            click.echo(f"✓ Successfully upshifted to {model}")
            click.echo(f"  Active model: {engine_status.active_model}")

    except ValueError as e:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(e)}, indent=2))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None
    except Exception as e:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(e)}, indent=2))
        else:
            click.echo(f"Upshift failed: {e}", err=True)
        logger.error("upshift_error", error=str(e), exc_info=True)
        raise SystemExit(1) from None


@clutch.command()
@click.option(
    "--model",
    required=True,
    help="Name of the light model to load.",
)
@click.option(
    "--ram",
    required=True,
    type=int,
    help="Required RAM in bytes for the model.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON for machine parsing.",
)
@click.pass_context
def downshift(ctx: click.Context, model: str, ram: int, output_json: bool) -> None:
    """Trigger a downshift to a lighter model.

    Performs an atomic shift: rev_match → disengage → engage.
    If any step fails, the operation is rolled back with clear error messaging.
    """
    try:
        config = ctx.obj["config"]
        clutch_engine = _create_clutch(config)

        # Run the async downshift operation
        asyncio.run(clutch_engine.downshift(light_model=model, required_ram=ram))

        # Get updated status
        engine_status = clutch_engine.status()

        if output_json:

            result = engine_status.last_shift_result
            output_data = {
                "success": result.success if result else False,
                "model": model,
                "active_model": engine_status.active_model,
                "error": result.error if result else None,
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            click.echo(f"✓ Successfully downshifted to {model}")
            click.echo(f"  Active model: {engine_status.active_model}")

    except ValueError as e:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(e)}, indent=2))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None
    except Exception as e:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(e)}, indent=2))
        else:
            click.echo(f"Downshift failed: {e}", err=True)
        logger.error("downshift_error", error=str(e), exc_info=True)
        raise SystemExit(1) from None


@clutch.command()
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON for machine parsing.",
)
@click.pass_context
def check(ctx: click.Context, output_json: bool) -> None:
    """Run a topology health check and display node status.

    Probes all configured nodes to verify reachability and measure latency.
    Returns a formatted table of node statuses (human) or JSON (--json).
    """
    try:
        config = ctx.obj["config"]
        clutch_engine = _create_clutch(config)

        # Run the async topology check
        node_statuses = asyncio.run(clutch_engine.infra_manager.check_all_nodes())

        if output_json:
            from dataclasses import asdict

            output_data = [asdict(status) for status in node_statuses]
            for item in output_data:
                item["checked_at"] = item["checked_at"].isoformat()
            click.echo(json.dumps(output_data, indent=2))
        else:
            # Human-readable table format
            click.echo("\n" + "=" * 70)
            click.echo("Cluster Topology Health Check")
            click.echo("=" * 70)
            header = (
                f"{'IP Address':<20} {'Status':<15} "
                f"{'Latency (ms)':<15} {'Checked':<20}"
            )
            click.echo(header)
            click.echo("-" * 70)

            for status in node_statuses:
                ip = status.ip
                status_str = "✓ Reachable" if status.reachable else "✗ Unreachable"
                latency_str = f"{status.latency_ms:.2f}" if status.latency_ms else "N/A"
                checked_str = status.checked_at.strftime("%Y-%m-%d %H:%M:%S")

                click.echo(
                    f"{ip:<20} {status_str:<15} {latency_str:<15} {checked_str:<20}"
                )

            click.echo("=" * 70)

            # Summary
            reachable_count = sum(1 for s in node_statuses if s.reachable)
            total_count = len(node_statuses)
            click.echo(f"Summary: {reachable_count}/{total_count} nodes reachable\n")

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None
    except Exception as e:
        click.echo(f"Check failed: {e}", err=True)
        logger.error("check_error", error=str(e), exc_info=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    clutch()
