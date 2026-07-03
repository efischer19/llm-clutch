"""Unit tests for the LLMClutch orchestrator class."""

from unittest.mock import AsyncMock, patch

import pytest
from testing.conftest import make_mock_backend

from llm_clutch import EngineState, EngineStatus, LLMClutch, ShiftResult
from llm_clutch.backend.base import ModelBackend
from llm_clutch.backend.exceptions import (
    ModelLoadError,
    ModelUnloadError,
)
from llm_clutch.core.infra import InfraManager


class TestLLMClutchInit:
    """Tests for LLMClutch initialization."""

    def test_init_with_valid_parameters(self) -> None:
        """Test LLMClutch initialization with valid parameters."""
        backend = make_mock_backend()
        infra_manager = InfraManager(["10.0.0.1"])

        clutch = LLMClutch(backend, infra_manager, min_nodes=2)

        assert clutch.backend is backend
        assert clutch.infra_manager is infra_manager
        assert clutch.min_nodes == 2
        assert clutch._state == EngineState.IDLE
        assert clutch._active_model is None
        assert clutch._cluster_health is False
        assert clutch._last_shift_result is None

    def test_init_with_default_min_nodes(self) -> None:
        """Test LLMClutch initialization with default min_nodes."""
        backend = make_mock_backend()
        infra_manager = InfraManager(["10.0.0.1"])

        clutch = LLMClutch(backend, infra_manager)

        assert clutch.min_nodes == 1

    def test_init_with_invalid_min_nodes_raises_error(self) -> None:
        """Test that min_nodes < 1 raises ValueError."""
        backend = make_mock_backend()
        infra_manager = InfraManager(["10.0.0.1"])

        with pytest.raises(ValueError, match="min_nodes must be at least 1"):
            LLMClutch(backend, infra_manager, min_nodes=0)


class TestRevMatch:
    """Tests for rev_match method."""

    @pytest.mark.asyncio
    async def test_rev_match_success(self) -> None:
        """Test successful rev_match when topology is healthy and memory sufficient."""
        backend = make_mock_backend(available_memory=1000000)  # 1MB

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager)
            result = await clutch.rev_match(500000)  # 500KB

            assert result is True
            assert clutch._cluster_health is True
            mock_verify.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_rev_match_failure_insufficient_memory(self) -> None:
        """Test rev_match fails when insufficient memory."""
        backend = make_mock_backend(available_memory=100000)  # 100KB

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager)
            result = await clutch.rev_match(500000)  # 500KB required

            assert result is False

    @pytest.mark.asyncio
    async def test_rev_match_failure_nodes_unreachable(self) -> None:
        """Test rev_match fails when cluster nodes are unreachable."""
        backend = make_mock_backend()

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = False

            clutch = LLMClutch(backend, infra_manager)
            result = await clutch.rev_match(500000)

            assert result is False
            assert clutch._cluster_health is False
            mock_verify.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_rev_match_failure_backend_error(self) -> None:
        """Test rev_match fails when backend cannot provide memory info."""
        from llm_clutch.backend.exceptions import BackendError

        backend = AsyncMock(spec=ModelBackend)
        backend.get_available_memory = AsyncMock(
            side_effect=BackendError("Backend error")
        )

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager)
            result = await clutch.rev_match(500000)

            assert result is False

    @pytest.mark.asyncio
    async def test_rev_match_respects_min_nodes(self) -> None:
        """Test that rev_match passes correct min_nodes to verify_topology."""
        backend = make_mock_backend()

        infra_manager = InfraManager(["10.0.0.1", "10.0.0.2", "10.0.0.3"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager, min_nodes=3)
            await clutch.rev_match(500000)

            mock_verify.assert_called_once_with(3)


class TestDisengage:
    """Tests for disengage method."""

    @pytest.mark.asyncio
    async def test_disengage_success(self) -> None:
        """Test successful disengage."""
        backend = make_mock_backend()
        backend.active_model = "llama-7b"

        infra_manager = InfraManager(["10.0.0.1"])
        clutch = LLMClutch(backend, infra_manager)
        clutch._active_model = "llama-7b"

        await clutch.disengage()

        assert clutch._active_model is None
        assert backend.active_model is None

    @pytest.mark.asyncio
    async def test_disengage_skipped_when_no_active_model(self) -> None:
        """Test disengage is skipped when no model is active."""
        backend = make_mock_backend()

        infra_manager = InfraManager(["10.0.0.1"])
        clutch = LLMClutch(backend, infra_manager)

        # Should not raise
        await clutch.disengage()
        assert clutch._active_model is None

    @pytest.mark.asyncio
    async def test_disengage_failure_raises_error(self) -> None:
        """Test disengage failure raises ModelUnloadError."""
        backend = AsyncMock(spec=ModelBackend)
        backend.unload_model = AsyncMock(side_effect=ModelUnloadError("Unload failed"))

        infra_manager = InfraManager(["10.0.0.1"])
        clutch = LLMClutch(backend, infra_manager)
        clutch._active_model = "llama-7b"

        with pytest.raises(ModelUnloadError):
            await clutch.disengage()

        # Active model should not change on error
        assert clutch._active_model == "llama-7b"


class TestEngage:
    """Tests for engage method."""

    @pytest.mark.asyncio
    async def test_engage_success(self) -> None:
        """Test successful engage."""
        backend = make_mock_backend()

        infra_manager = InfraManager(["10.0.0.1"])
        clutch = LLMClutch(backend, infra_manager)

        await clutch.engage("llama-7b")

        assert clutch._active_model == "llama-7b"
        assert backend.active_model == "llama-7b"

    @pytest.mark.asyncio
    async def test_engage_failure_raises_error(self) -> None:
        """Test engage failure raises ModelLoadError."""
        backend = AsyncMock(spec=ModelBackend)
        backend.load_model = AsyncMock(side_effect=ModelLoadError("Load failed"))

        infra_manager = InfraManager(["10.0.0.1"])
        clutch = LLMClutch(backend, infra_manager)

        with pytest.raises(ModelLoadError):
            await clutch.engage("llama-7b")

        # Active model should not change on error
        assert clutch._active_model is None


class TestUpshift:
    """Tests for upshift method."""

    @pytest.mark.asyncio
    async def test_upshift_success(self) -> None:
        """Test successful upshift."""
        backend = make_mock_backend(available_memory=1000000)

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager)
            clutch._active_model = "llama-7b"

            await clutch.upshift("llama-70b", 500000)

            assert clutch._state == EngineState.ENGAGED
            assert clutch._active_model == "llama-70b"
            assert clutch._last_shift_result is not None
            assert clutch._last_shift_result.success is True
            assert clutch._last_shift_result.previous_model == "llama-7b"
            assert clutch._last_shift_result.new_model == "llama-70b"

    @pytest.mark.asyncio
    async def test_upshift_failure_rev_match(self) -> None:
        """Test upshift fails when rev_match fails."""
        backend = make_mock_backend(available_memory=100000)  # Not enough memory

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager)
            clutch._active_model = "llama-7b"

            with pytest.raises(ValueError, match="Cannot upshift"):
                await clutch.upshift("llama-70b", 500000)

            assert clutch._state == EngineState.IDLE
            assert clutch._active_model == "llama-7b"  # Not changed
            assert clutch._last_shift_result is not None
            assert clutch._last_shift_result.success is False

    @pytest.mark.asyncio
    async def test_upshift_failure_disengage(self) -> None:
        """Test upshift failure when disengage fails."""
        backend = AsyncMock(spec=ModelBackend)
        backend.get_available_memory = AsyncMock(return_value=1000000)
        backend.unload_model = AsyncMock(side_effect=ModelUnloadError("Unload failed"))

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager)
            clutch._active_model = "llama-7b"

            with pytest.raises(ModelUnloadError):
                await clutch.upshift("llama-70b", 500000)

            assert clutch._state == EngineState.ERROR
            assert clutch._active_model == "llama-7b"  # Not changed
            assert clutch._last_shift_result is not None
            assert clutch._last_shift_result.success is False

    @pytest.mark.asyncio
    async def test_upshift_failure_engage_logs_critical(self) -> None:
        """Test upshift failure when engage fails logs critical error."""
        backend = AsyncMock(spec=ModelBackend)
        backend.get_available_memory = AsyncMock(return_value=1000000)
        backend.unload_model = AsyncMock()
        backend.load_model = AsyncMock(side_effect=ModelLoadError("Load failed"))

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager)
            clutch._active_model = "llama-7b"

            with pytest.raises(ModelLoadError):
                await clutch.upshift("llama-70b", 500000)

            # Model should be None (disengaged) but engage failed
            assert clutch._active_model is None
            assert clutch._state == EngineState.ERROR
            assert clutch._last_shift_result is not None
            assert clutch._last_shift_result.success is False

    @pytest.mark.asyncio
    async def test_upshift_from_idle_state(self) -> None:
        """Test upshift when no model is currently active."""
        backend = make_mock_backend(available_memory=1000000)

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager)

            await clutch.upshift("llama-70b", 500000)

            assert clutch._state == EngineState.ENGAGED
            assert clutch._active_model == "llama-70b"
            assert clutch._last_shift_result.previous_model is None
            assert clutch._last_shift_result.new_model == "llama-70b"


class TestDownshift:
    """Tests for downshift method."""

    @pytest.mark.asyncio
    async def test_downshift_success(self) -> None:
        """Test successful downshift."""
        backend = make_mock_backend(available_memory=1000000)

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager)
            clutch._active_model = "llama-70b"

            await clutch.downshift("llama-7b", 300000)

            assert clutch._state == EngineState.ENGAGED
            assert clutch._active_model == "llama-7b"
            assert clutch._last_shift_result is not None
            assert clutch._last_shift_result.success is True
            assert clutch._last_shift_result.previous_model == "llama-70b"
            assert clutch._last_shift_result.new_model == "llama-7b"

    @pytest.mark.asyncio
    async def test_downshift_failure_rev_match(self) -> None:
        """Test downshift fails when rev_match fails."""
        backend = make_mock_backend(available_memory=100000)  # Not enough memory

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager)
            clutch._active_model = "llama-70b"

            with pytest.raises(ValueError, match="Cannot downshift"):
                await clutch.downshift("llama-7b", 500000)

            assert clutch._state == EngineState.IDLE
            assert clutch._active_model == "llama-70b"  # Not changed
            assert clutch._last_shift_result is not None
            assert clutch._last_shift_result.success is False

    @pytest.mark.asyncio
    async def test_downshift_failure_engage_logs_critical(self) -> None:
        """Test downshift failure when engage fails logs critical error."""
        backend = AsyncMock(spec=ModelBackend)
        backend.get_available_memory = AsyncMock(return_value=1000000)
        backend.unload_model = AsyncMock()
        backend.load_model = AsyncMock(side_effect=ModelLoadError("Load failed"))

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager)
            clutch._active_model = "llama-70b"

            with pytest.raises(ModelLoadError):
                await clutch.downshift("llama-7b", 300000)

            # Model should be None (disengaged) but engage failed
            assert clutch._active_model is None
            assert clutch._state == EngineState.ERROR


class TestStatus:
    """Tests for status method."""

    def test_status_returns_current_state(self) -> None:
        """Test that status returns current engine state."""
        backend = make_mock_backend()
        infra_manager = InfraManager(["10.0.0.1"])

        clutch = LLMClutch(backend, infra_manager)
        clutch._active_model = "llama-7b"
        clutch._cluster_health = True
        clutch._state = EngineState.ENGAGED

        status = clutch.status()

        assert isinstance(status, EngineStatus)
        assert status.state == EngineState.ENGAGED
        assert status.active_model == "llama-7b"
        assert status.cluster_health is True
        assert status.last_shift_result is None

    def test_status_includes_shift_result(self) -> None:
        """Test that status includes last shift result."""
        backend = make_mock_backend()
        infra_manager = InfraManager(["10.0.0.1"])

        clutch = LLMClutch(backend, infra_manager)
        shift_result = ShiftResult(
            success=True,
            previous_model="llama-7b",
            new_model="llama-70b",
        )
        clutch._last_shift_result = shift_result

        status = clutch.status()

        assert status.last_shift_result == shift_result

    def test_status_with_error_state(self) -> None:
        """Test status when engine is in error state."""
        backend = make_mock_backend()
        infra_manager = InfraManager(["10.0.0.1"])

        clutch = LLMClutch(backend, infra_manager)
        clutch._state = EngineState.ERROR
        clutch._active_model = None
        clutch._cluster_health = False

        status = clutch.status()

        assert status.state == EngineState.ERROR
        assert status.active_model is None
        assert status.cluster_health is False


class TestAtomicity:
    """Tests for atomic operation guarantees."""

    @pytest.mark.asyncio
    async def test_upshift_not_partially_completed_on_rev_match_failure(
        self,
    ) -> None:
        """Test that upshift leaves state unchanged if rev_match fails."""
        backend = AsyncMock(spec=ModelBackend)
        backend.get_available_memory = AsyncMock(return_value=100)  # Too little

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager)
            clutch._active_model = "llama-7b"

            with pytest.raises(ValueError):
                await clutch.upshift("llama-70b", 500000)

            # Verify nothing changed
            assert clutch._active_model == "llama-7b"
            assert backend.unload_model.call_count == 0
            assert backend.load_model.call_count == 0

    @pytest.mark.asyncio
    async def test_downshift_not_partially_completed_on_rev_match_failure(
        self,
    ) -> None:
        """Test that downshift leaves state unchanged if rev_match fails."""
        backend = AsyncMock(spec=ModelBackend)
        backend.get_available_memory = AsyncMock(return_value=100)  # Too little

        infra_manager = InfraManager(["10.0.0.1"])
        with patch.object(
            infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            clutch = LLMClutch(backend, infra_manager)
            clutch._active_model = "llama-70b"

            with pytest.raises(ValueError):
                await clutch.downshift("llama-7b", 500000)

            # Verify nothing changed
            assert clutch._active_model == "llama-70b"
            assert backend.unload_model.call_count == 0
            assert backend.load_model.call_count == 0


class TestEmergencyReset:
    """Tests for emergency_reset method."""

    @pytest.mark.asyncio
    async def test_emergency_reset_success(self) -> None:
        """Test successful emergency reset."""
        backend = AsyncMock(spec=ModelBackend)
        backend.unload_model = AsyncMock()
        backend.load_model = AsyncMock()

        infra_manager = InfraManager(["10.0.0.1", "10.0.0.2"])
        from datetime import datetime

        from llm_clutch.core.infra import NodeStatus

        with patch.object(
            infra_manager, "check_node", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = NodeStatus(
                ip="10.0.0.1",
                reachable=True,
                latency_ms=10.5,
                checked_at=datetime.now(),
            )

            clutch = LLMClutch(backend, infra_manager)
            clutch._active_model = "llama-70b"

            await clutch.emergency_reset(safe_model="llama-7b", primary_node="10.0.0.1")

            assert clutch._active_model == "llama-7b"
            assert clutch._state == EngineState.ENGAGED
            assert clutch._last_shift_result is not None
            assert clutch._last_shift_result.success is True
            assert clutch._last_shift_result.previous_model == "llama-70b"
            assert clutch._last_shift_result.new_model == "llama-7b"

            backend.unload_model.assert_called_once()
            backend.load_model.assert_called_once_with("llama-7b")
            mock_check.assert_called_once_with("10.0.0.1")

    @pytest.mark.asyncio
    async def test_emergency_reset_when_cluster_in_error_state(self) -> None:
        """Test emergency reset works when cluster is in error state."""
        backend = AsyncMock(spec=ModelBackend)
        backend.unload_model = AsyncMock()
        backend.load_model = AsyncMock()

        infra_manager = InfraManager(["10.0.0.1"])
        from datetime import datetime

        from llm_clutch.core.infra import NodeStatus

        with patch.object(
            infra_manager, "check_node", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = NodeStatus(
                ip="10.0.0.1",
                reachable=True,
                latency_ms=10.5,
                checked_at=datetime.now(),
            )

            clutch = LLMClutch(backend, infra_manager)
            clutch._state = EngineState.ERROR
            clutch._active_model = None

            await clutch.emergency_reset(safe_model="llama-7b", primary_node="10.0.0.1")

            assert clutch._active_model == "llama-7b"
            assert clutch._state == EngineState.ENGAGED

    @pytest.mark.asyncio
    async def test_emergency_reset_primary_unreachable(self) -> None:
        """Test emergency reset fails when primary node is unreachable."""
        backend = AsyncMock(spec=ModelBackend)
        backend.unload_model = AsyncMock()

        infra_manager = InfraManager(["10.0.0.1"])
        from datetime import datetime

        from llm_clutch.core.infra import NodeStatus

        with patch.object(
            infra_manager, "check_node", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = NodeStatus(
                ip="10.0.0.1",
                reachable=False,
                latency_ms=None,
                checked_at=datetime.now(),
            )

            clutch = LLMClutch(backend, infra_manager)

            with pytest.raises(OSError, match="unreachable"):
                await clutch.emergency_reset(
                    safe_model="llama-7b", primary_node="10.0.0.1"
                )

            assert clutch._state == EngineState.ERROR
            backend.unload_model.assert_called_once()
            backend.load_model.assert_not_called()

    @pytest.mark.asyncio
    async def test_emergency_reset_unload_failure(self) -> None:
        """Test emergency reset propagates unload failure."""
        backend = AsyncMock(spec=ModelBackend)
        backend.unload_model = AsyncMock(side_effect=ModelUnloadError("Unload failed"))

        infra_manager = InfraManager(["10.0.0.1"])
        clutch = LLMClutch(backend, infra_manager)
        clutch._active_model = "llama-70b"

        with pytest.raises(ModelUnloadError):
            await clutch.emergency_reset(safe_model="llama-7b", primary_node="10.0.0.1")

        assert clutch._state == EngineState.ERROR

    @pytest.mark.asyncio
    async def test_emergency_reset_load_failure(self) -> None:
        """Test emergency reset propagates load failure."""
        backend = AsyncMock(spec=ModelBackend)
        backend.unload_model = AsyncMock()
        backend.load_model = AsyncMock(side_effect=ModelLoadError("Load failed"))

        infra_manager = InfraManager(["10.0.0.1"])
        from datetime import datetime

        from llm_clutch.core.infra import NodeStatus

        with patch.object(
            infra_manager, "check_node", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = NodeStatus(
                ip="10.0.0.1",
                reachable=True,
                latency_ms=10.5,
                checked_at=datetime.now(),
            )

            clutch = LLMClutch(backend, infra_manager)
            clutch._active_model = "llama-70b"

            with pytest.raises(ModelLoadError):
                await clutch.emergency_reset(
                    safe_model="llama-7b", primary_node="10.0.0.1"
                )

            assert clutch._state == EngineState.ERROR
            assert clutch._active_model is None

    @pytest.mark.asyncio
    async def test_emergency_reset_no_active_model(self) -> None:
        """Test emergency reset works when no model is currently active."""
        backend = AsyncMock(spec=ModelBackend)
        backend.unload_model = AsyncMock()
        backend.load_model = AsyncMock()

        infra_manager = InfraManager(["10.0.0.1"])
        from datetime import datetime

        from llm_clutch.core.infra import NodeStatus

        with patch.object(
            infra_manager, "check_node", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = NodeStatus(
                ip="10.0.0.1",
                reachable=True,
                latency_ms=10.5,
                checked_at=datetime.now(),
            )

            clutch = LLMClutch(backend, infra_manager)
            assert clutch._active_model is None

            await clutch.emergency_reset(safe_model="llama-7b", primary_node="10.0.0.1")

            assert clutch._active_model == "llama-7b"
            assert clutch._state == EngineState.ENGAGED
            backend.unload_model.assert_called_once()
            backend.load_model.assert_called_once_with("llama-7b")
