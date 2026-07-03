"""Tests for the Click-based CLI (per ADR-011)."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from llm_clutch.cli import clutch
from llm_clutch.core.clutch import EngineState, EngineStatus, ShiftResult
from llm_clutch.core.infra import NodeStatus


class TestClutchStatusCommand:
    """Tests for the 'clutch status' command."""

    def test_status_success_human_readable(self) -> None:
        """Test status command with human-readable output."""
        runner = CliRunner()

        # Mock the backend and infra manager
        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.ENGAGED,
                active_model="llama-70b",
                cluster_health=True,
                last_shift_result=ShiftResult(
                    success=True,
                    previous_model="llama-7b",
                    new_model="llama-70b",
                ),
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(clutch, ["status"])

            assert result.exit_code == 0
            assert "Engine State: engaged" in result.output
            assert "Active Model: llama-70b" in result.output
            assert "Cluster Health: Healthy" in result.output
            assert "✓ Success" in result.output
            assert "llama-7b" in result.output

    def test_status_success_json(self) -> None:
        """Test status command with JSON output."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.ENGAGED,
                active_model="llama-70b",
                cluster_health=True,
                last_shift_result=ShiftResult(
                    success=True,
                    previous_model="llama-7b",
                    new_model="llama-70b",
                ),
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(clutch, ["status", "--json"])

            assert result.exit_code == 0
            output_json = json.loads(result.output)
            assert output_json["state"] == "engaged"
            assert output_json["active_model"] == "llama-70b"
            assert output_json["cluster_health"] is True
            assert output_json["last_shift_result"]["success"] is True

    def test_status_error_missing_config(self) -> None:
        """Test status command when config is invalid."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_create_clutch.side_effect = ValueError("No node IPs configured")

            result = runner.invoke(clutch, ["status"])

            assert result.exit_code == 1
            assert "Error:" in result.output

    def test_status_unhealthy_cluster(self) -> None:
        """Test status command with unhealthy cluster."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.IDLE,
                active_model=None,
                cluster_health=False,
                last_shift_result=None,
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(clutch, ["status"])

            assert result.exit_code == 0
            assert "Cluster Health: Unhealthy" in result.output


class TestClutchUpshiftCommand:
    """Tests for the 'clutch upshift' command."""

    def test_upshift_success_human_readable(self) -> None:
        """Test upshift command with human-readable output."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.upshift = AsyncMock()
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.ENGAGED,
                active_model="llama-70b",
                cluster_health=True,
                last_shift_result=ShiftResult(
                    success=True,
                    previous_model="llama-7b",
                    new_model="llama-70b",
                ),
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(
                clutch,
                ["upshift", "--model", "llama-70b", "--ram", "500000"],
            )

            assert result.exit_code == 0
            assert "✓ Successfully upshifted to llama-70b" in result.output
            assert "Active model: llama-70b" in result.output
            mock_clutch.upshift.assert_called_once_with(
                heavy_model="llama-70b", required_ram=500000
            )

    def test_upshift_success_json(self) -> None:
        """Test upshift command with JSON output."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.upshift = AsyncMock()
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.ENGAGED,
                active_model="llama-70b",
                cluster_health=True,
                last_shift_result=ShiftResult(
                    success=True,
                    previous_model="llama-7b",
                    new_model="llama-70b",
                ),
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(
                clutch,
                ["upshift", "--model", "llama-70b", "--ram", "500000", "--json"],
            )

            assert result.exit_code == 0
            output_json = json.loads(result.output)
            assert output_json["success"] is True
            assert output_json["model"] == "llama-70b"
            assert output_json["active_model"] == "llama-70b"

    def test_upshift_failure(self) -> None:
        """Test upshift command when upshift fails."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.upshift = AsyncMock(
                side_effect=ValueError("Insufficient memory")
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(
                clutch,
                ["upshift", "--model", "llama-70b", "--ram", "500000"],
            )

            assert result.exit_code == 1
            assert "Error:" in result.output

    def test_upshift_missing_model(self) -> None:
        """Test upshift command without --model option."""
        runner = CliRunner()

        result = runner.invoke(
            clutch,
            ["upshift", "--ram", "500000"],
        )

        assert result.exit_code != 0
        assert "--model" in result.output or "Missing option" in result.output


class TestClutchDownshiftCommand:
    """Tests for the 'clutch downshift' command."""

    def test_downshift_success_human_readable(self) -> None:
        """Test downshift command with human-readable output."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.downshift = AsyncMock()
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.ENGAGED,
                active_model="llama-7b",
                cluster_health=True,
                last_shift_result=ShiftResult(
                    success=True,
                    previous_model="llama-70b",
                    new_model="llama-7b",
                ),
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(
                clutch,
                ["downshift", "--model", "llama-7b", "--ram", "100000"],
            )

            assert result.exit_code == 0
            assert "✓ Successfully downshifted to llama-7b" in result.output
            assert "Active model: llama-7b" in result.output
            mock_clutch.downshift.assert_called_once_with(
                light_model="llama-7b", required_ram=100000
            )

    def test_downshift_success_json(self) -> None:
        """Test downshift command with JSON output."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.downshift = AsyncMock()
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.ENGAGED,
                active_model="llama-7b",
                cluster_health=True,
                last_shift_result=ShiftResult(
                    success=True,
                    previous_model="llama-70b",
                    new_model="llama-7b",
                ),
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(
                clutch,
                ["downshift", "--model", "llama-7b", "--ram", "100000", "--json"],
            )

            assert result.exit_code == 0
            output_json = json.loads(result.output)
            assert output_json["success"] is True
            assert output_json["model"] == "llama-7b"

    def test_downshift_failure(self) -> None:
        """Test downshift command when downshift fails."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.downshift = AsyncMock(
                side_effect=ValueError("Cluster unhealthy")
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(
                clutch,
                ["downshift", "--model", "llama-7b", "--ram", "100000"],
            )

            assert result.exit_code == 1
            assert "Error:" in result.output


class TestClutchCheckCommand:
    """Tests for the 'clutch check' command."""

    def test_check_success_human_readable(self) -> None:
        """Test check command with human-readable output."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_infra = MagicMock()
            mock_infra.check_all_nodes = AsyncMock(
                return_value=[
                    NodeStatus(
                        ip="10.0.0.1",
                        reachable=True,
                        latency_ms=25.5,
                        checked_at=datetime.now(),
                    ),
                    NodeStatus(
                        ip="10.0.0.2",
                        reachable=True,
                        latency_ms=30.2,
                        checked_at=datetime.now(),
                    ),
                ]
            )
            mock_clutch.infra_manager = mock_infra
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(clutch, ["check"])

            assert result.exit_code == 0
            assert "Cluster Topology Health Check" in result.output
            assert "10.0.0.1" in result.output
            assert "10.0.0.2" in result.output
            assert "✓ Reachable" in result.output
            assert "2/2 nodes reachable" in result.output

    def test_check_success_json(self) -> None:
        """Test check command with JSON output."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_infra = MagicMock()
            checked_at = datetime.now()
            mock_infra.check_all_nodes = AsyncMock(
                return_value=[
                    NodeStatus(
                        ip="10.0.0.1",
                        reachable=True,
                        latency_ms=25.5,
                        checked_at=checked_at,
                    ),
                ]
            )
            mock_clutch.infra_manager = mock_infra
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(clutch, ["check", "--json"])

            assert result.exit_code == 0
            output_json = json.loads(result.output)
            assert len(output_json) == 1
            assert output_json[0]["ip"] == "10.0.0.1"
            assert output_json[0]["reachable"] is True

    def test_check_some_nodes_unreachable(self) -> None:
        """Test check command when some nodes are unreachable."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_infra = MagicMock()
            mock_infra.check_all_nodes = AsyncMock(
                return_value=[
                    NodeStatus(
                        ip="10.0.0.1",
                        reachable=True,
                        latency_ms=25.5,
                        checked_at=datetime.now(),
                    ),
                    NodeStatus(
                        ip="10.0.0.2",
                        reachable=False,
                        latency_ms=None,
                        checked_at=datetime.now(),
                    ),
                ]
            )
            mock_clutch.infra_manager = mock_infra
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(clutch, ["check"])

            assert result.exit_code == 0
            assert "✗ Unreachable" in result.output
            assert "1/2 nodes reachable" in result.output


class TestClutchConfigOption:
    """Tests for the --config option."""

    def test_config_option_passed_to_load_config(self) -> None:
        """Test that --config option is passed to _load_config."""
        runner = CliRunner()

        with (
            patch("llm_clutch.cli._load_config") as mock_load_config,
            patch("llm_clutch.cli._create_clutch") as mock_create_clutch,
        ):
            mock_load_config.return_value = {"node_ips": ["10.0.0.1"]}
            mock_clutch = MagicMock()
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.IDLE,
                active_model=None,
                cluster_health=False,
                last_shift_result=None,
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(
                clutch,
                ["--config", "/path/to/config.toml", "status"],
            )

            assert result.exit_code == 0
            mock_load_config.assert_called_once_with("/path/to/config.toml")

    def test_help_text(self) -> None:
        """Test that all commands have help text."""
        runner = CliRunner()

        # Test main help
        result = runner.invoke(clutch, ["--help"])
        assert result.exit_code == 0
        assert "LLM Clutch CLI" in result.output

        # Test status help
        result = runner.invoke(clutch, ["status", "--help"])
        assert result.exit_code == 0
        assert "Display current cluster state" in result.output

        # Test upshift help
        result = runner.invoke(clutch, ["upshift", "--help"])
        assert result.exit_code == 0
        assert "Trigger an upshift" in result.output

        # Test downshift help
        result = runner.invoke(clutch, ["downshift", "--help"])
        assert result.exit_code == 0
        assert "Trigger a downshift" in result.output

        # Test check help
        result = runner.invoke(clutch, ["check", "--help"])
        assert result.exit_code == 0
        assert "Run a topology health check" in result.output


class TestClutchEmergencyResetCommand:
    """Tests for the 'clutch emergency-reset' command."""

    def test_emergency_reset_success_with_force(self) -> None:
        """Test emergency reset command with --force flag."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.emergency_reset = AsyncMock()
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.ENGAGED,
                active_model="llama-7b",
                cluster_health=True,
                last_shift_result=ShiftResult(
                    success=True,
                    previous_model="llama-70b",
                    new_model="llama-7b",
                ),
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(
                clutch,
                [
                    "emergency-reset",
                    "--safe-model",
                    "llama-7b",
                    "--primary-node",
                    "10.0.0.1",
                    "--force",
                ],
            )

            assert result.exit_code == 0
            assert "✓ Emergency Reset Successful" in result.output
            assert "llama-7b" in result.output
            assert "10.0.0.1" in result.output
            mock_clutch.emergency_reset.assert_called_once_with(
                safe_model="llama-7b", primary_node="10.0.0.1"
            )

    def test_emergency_reset_success_json(self) -> None:
        """Test emergency reset command with JSON output."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.emergency_reset = AsyncMock()
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.ENGAGED,
                active_model="llama-7b",
                cluster_health=True,
                last_shift_result=ShiftResult(
                    success=True,
                    previous_model="llama-70b",
                    new_model="llama-7b",
                ),
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(
                clutch,
                [
                    "emergency-reset",
                    "--safe-model",
                    "llama-7b",
                    "--primary-node",
                    "10.0.0.1",
                    "--force",
                    "--json",
                ],
            )

            assert result.exit_code == 0
            output_json = json.loads(result.output)
            assert output_json["success"] is True
            assert output_json["safe_model"] == "llama-7b"
            assert output_json["primary_node"] == "10.0.0.1"
            assert output_json["active_model"] == "llama-7b"

    def test_emergency_reset_missing_safe_model(self) -> None:
        """Test emergency reset command without safe model."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_create_clutch.side_effect = ValueError("No safe model")

            result = runner.invoke(
                clutch,
                [
                    "emergency-reset",
                    "--primary-node",
                    "10.0.0.1",
                    "--force",
                ],
            )

            assert result.exit_code == 1
            assert "Error:" in result.output

    def test_emergency_reset_missing_primary_node(self) -> None:
        """Test emergency reset command without primary node."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_create_clutch.side_effect = ValueError("No primary node")

            result = runner.invoke(
                clutch,
                [
                    "emergency-reset",
                    "--safe-model",
                    "llama-7b",
                    "--force",
                ],
            )

            assert result.exit_code == 1
            assert "Error:" in result.output

    def test_emergency_reset_primary_unreachable(self) -> None:
        """Test emergency reset command when primary node is unreachable."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.emergency_reset = AsyncMock(
                side_effect=OSError("Primary node unreachable")
            )
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.IDLE,
                active_model=None,
                cluster_health=False,
                last_shift_result=None,
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(
                clutch,
                [
                    "emergency-reset",
                    "--safe-model",
                    "llama-7b",
                    "--primary-node",
                    "10.0.0.1",
                    "--force",
                ],
            )

            assert result.exit_code == 1
            assert "unreachable" in result.output or "Error:" in result.output

    def test_emergency_reset_confirmation_prompt_yes(self) -> None:
        """Test emergency reset confirmation prompt with yes response."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.emergency_reset = AsyncMock()
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.ENGAGED,
                active_model="llama-70b",
                cluster_health=True,
                last_shift_result=None,
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(
                clutch,
                [
                    "emergency-reset",
                    "--safe-model",
                    "llama-7b",
                    "--primary-node",
                    "10.0.0.1",
                ],
                input="y\n",
            )

            assert result.exit_code == 0
            assert "Emergency Reset Confirmation" in result.output
            assert "Proceed with emergency reset?" in result.output
            mock_clutch.emergency_reset.assert_called_once()

    def test_emergency_reset_confirmation_prompt_no(self) -> None:
        """Test emergency reset confirmation prompt with no response."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.emergency_reset = AsyncMock()
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.ENGAGED,
                active_model="llama-70b",
                cluster_health=True,
                last_shift_result=None,
            )
            mock_create_clutch.return_value = mock_clutch

            result = runner.invoke(
                clutch,
                [
                    "emergency-reset",
                    "--safe-model",
                    "llama-7b",
                    "--primary-node",
                    "10.0.0.1",
                ],
                input="n\n",
            )

            assert result.exit_code == 0
            assert "Reset cancelled." in result.output
            mock_clutch.emergency_reset.assert_not_called()

    def test_emergency_reset_loads_from_config(self) -> None:
        """Test emergency reset loads safe_model from config."""
        runner = CliRunner()

        with patch("llm_clutch.cli._create_clutch") as mock_create_clutch:
            mock_clutch = MagicMock()
            mock_clutch.emergency_reset = AsyncMock()
            mock_clutch.status.return_value = EngineStatus(
                state=EngineState.IDLE,
                active_model=None,
                cluster_health=False,
                last_shift_result=None,
            )
            mock_create_clutch.return_value = mock_clutch

            with patch("llm_clutch.cli._load_config") as mock_load_config:
                mock_load_config.return_value = {
                    "node_ips": ["10.0.0.1"],
                    "safe_model": "llama-7b",
                    "primary_node": "10.0.0.1",
                }

                result = runner.invoke(
                    clutch,
                    ["emergency-reset", "--force"],
                )

                assert result.exit_code == 0
                mock_clutch.emergency_reset.assert_called_once_with(
                    safe_model="llama-7b", primary_node="10.0.0.1"
                )
