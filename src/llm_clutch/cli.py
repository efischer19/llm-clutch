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
            health_status = "Healthy" if engine_status.cluster_health else "Unhealthy"
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


@clutch.command()
@click.option(
    "--safe-model",
    help=(
        "Name of the safe model to load (e.g., llama-7b). "
        "Can be configured in config file."
    ),
)
@click.option(
    "--primary-node",
    help=(
        "IP address of the primary node to target (e.g., 10.0.0.1). "
        "Can be configured in config file."
    ),
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt and proceed with reset.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON for machine parsing.",
)
@click.pass_context
def emergency_reset(
    ctx: click.Context,
    safe_model: str | None,
    primary_node: str | None,
    force: bool,
    output_json: bool,
) -> None:
    """Perform an emergency reset to restore cluster to a known working state.

    This is the "break glass in case of emergency" feature that restores the
    local cluster to a known working state (typically a single-node configuration
    with a lightweight model) without requiring external agents to be functional.

    The reset sequence:
    - Force-unload any active model
    - Verify primary node is reachable
    - Load the safe model on primary node only

    Defaults for safe_model and primary_node can be configured in the config file
    under the [tool.llm-clutch] section.
    """
    try:
        config = ctx.obj["config"]
        clutch_engine = _create_clutch(config)

        # Get safe_model from CLI arg or config file
        if not safe_model:
            safe_model = config.get("safe_model")
        if not safe_model:
            error_msg = (
                "Safe model not specified. Use --safe-model or configure "
                "in config file."
            )
            raise ValueError(error_msg)

        # Get primary_node from CLI arg or config file
        if not primary_node:
            primary_node = config.get("primary_node")
        if not primary_node:
            # If not configured, use the first node IP
            node_ips = config.get("node_ips", [])
            if node_ips:
                primary_node = node_ips[0]

        if not primary_node:
            error_msg = (
                "Primary node not specified. Use --primary-node or configure "
                "in config file."
            )
            raise ValueError(error_msg)

        # Get current status for confirmation prompt
        current_status = clutch_engine.status()

        # Display current state and ask for confirmation (unless --force)
        if not force:
            click.echo("\n" + "=" * 70)
            click.echo("Emergency Reset Confirmation")
            click.echo("=" * 70)
            click.echo(f"Current State: {current_status.state.value}")
            current_model = current_status.active_model or "None"
            click.echo(f"Active Model: {current_model}")
            health_status = "Healthy" if current_status.cluster_health else "Unhealthy"
            click.echo(f"Cluster Health: {health_status}")
            click.echo()
            click.echo("This operation will:")
            click.echo(f"  1. Force-unload current model: {current_model}")
            click.echo(
                f"  2. Load safe model on primary node: {safe_model} on {primary_node}"
            )
            click.echo("  3. Leave all other nodes idle")
            click.echo()
            click.echo("Warning: This bypasses multi-node cluster checks.")
            click.echo("=" * 70)

            # Ask for confirmation
            if not click.confirm("Proceed with emergency reset?"):
                click.echo("Reset cancelled.")
                raise SystemExit(0)

        # Run the async emergency_reset operation
        asyncio.run(
            clutch_engine.emergency_reset(
                safe_model=safe_model, primary_node=primary_node
            )
        )

        # Get updated status
        engine_status = clutch_engine.status()

        if output_json:
            result = engine_status.last_shift_result
            output_data = {
                "success": result.success if result else False,
                "safe_model": safe_model,
                "primary_node": primary_node,
                "active_model": engine_status.active_model,
                "error": result.error if result else None,
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            click.echo("\n" + "=" * 70)
            click.echo("✓ Emergency Reset Successful")
            click.echo("=" * 70)
            click.echo(f"Safe model loaded: {safe_model}")
            click.echo(f"Primary node: {primary_node}")
            click.echo(f"Active model: {engine_status.active_model}")
            click.echo("=" * 70 + "\n")

    except ValueError as e:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(e)}, indent=2))
        else:
            click.echo(f"Error: {e}", err=True)
        logger.error("emergency_reset_value_error", error=str(e))
        raise SystemExit(1) from None
    except OSError as e:
        if output_json:
            click.echo(
                json.dumps(
                    {"success": False, "error": f"Primary node unreachable: {e}"},
                    indent=2,
                )
            )
        else:
            click.echo(f"Error: Primary node unreachable: {e}", err=True)
        logger.error("emergency_reset_node_error", error=str(e), exc_info=True)
        raise SystemExit(1) from None
    except Exception as e:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(e)}, indent=2))
        else:
            click.echo(f"Emergency reset failed: {e}", err=True)
        logger.error("emergency_reset_error", error=str(e), exc_info=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    clutch()
