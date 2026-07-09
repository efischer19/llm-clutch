"""Unit tests for the OpenClaw integration module.

Tests validate tool schema shape, successful invocation, error handling,
and parameter validation for all OpenClaw tools.
"""

from unittest.mock import AsyncMock, patch

import pytest
from testing.conftest import make_mock_backend, make_mock_clutch

from llm_clutch.integrations.openclaw import (
    DownshiftTool,
    StatusTool,
    ToolResult,
    UpshiftTool,
    get_openclaw_tools,
    get_tool_executor,
)


class TestToolSchemas:
    """Tests for tool schema definitions."""

    def test_upshift_tool_schema_structure(self) -> None:
        """Test that upshift tool schema has correct structure."""
        schema = UpshiftTool.tool_schema()

        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "upshift"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]

    def test_upshift_tool_schema_parameters(self) -> None:
        """Test that upshift tool schema has required parameters."""
        schema = UpshiftTool.tool_schema()
        params = schema["function"]["parameters"]

        assert params["type"] == "object"
        assert "properties" in params
        assert "model_name" in params["properties"]
        assert "required_ram" in params["properties"]
        assert "reason" in params["properties"]
        assert "model_name" in params["required"]
        assert "required_ram" in params["required"]
        assert "reason" not in params["required"]  # reason is optional

    def test_downshift_tool_schema_structure(self) -> None:
        """Test that downshift tool schema has correct structure."""
        schema = DownshiftTool.tool_schema()

        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "downshift"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]

    def test_downshift_tool_schema_parameters(self) -> None:
        """Test that downshift tool schema has required parameters."""
        schema = DownshiftTool.tool_schema()
        params = schema["function"]["parameters"]

        assert params["type"] == "object"
        assert "properties" in params
        assert "model_name" in params["properties"]
        assert "required_ram" in params["properties"]
        assert "reason" in params["properties"]
        assert "model_name" in params["required"]
        assert "required_ram" in params["required"]
        assert "reason" not in params["required"]  # reason is optional

    def test_status_tool_schema_structure(self) -> None:
        """Test that status tool schema has correct structure."""
        schema = StatusTool.tool_schema()

        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "status"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]

    def test_status_tool_schema_has_no_required_parameters(self) -> None:
        """Test that status tool schema requires no parameters."""
        schema = StatusTool.tool_schema()
        params = schema["function"]["parameters"]

        assert params["type"] == "object"
        assert "properties" in params
        assert len(params["required"]) == 0


class TestUpshiftToolExecution:
    """Tests for UpshiftTool execution."""

    @pytest.mark.asyncio
    async def test_upshift_success(self) -> None:
        """Test successful upshift operation."""
        clutch = make_mock_clutch()
        # Patch verify_topology to return True
        with patch.object(
            clutch.infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True
            tool = UpshiftTool(clutch)

            result = await tool.execute("llama-70b", 500000)

            assert isinstance(result, ToolResult)
            assert result.success is True
            assert result.active_model == "llama-70b"
            assert result.cluster_health is not None
            assert result.error is None
            assert "Successfully upshifted" in result.message

    @pytest.mark.asyncio
    async def test_upshift_with_reason(self) -> None:
        """Test upshift with audit logging reason."""
        clutch = make_mock_clutch()
        with patch.object(
            clutch.infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True
            tool = UpshiftTool(clutch)
            reason = "Complex multi-step reasoning task detected"

            result = await tool.execute("llama-70b", 500000, reason=reason)

            assert result.success is True
            assert result.active_model == "llama-70b"

    @pytest.mark.asyncio
    async def test_upshift_insufficient_memory_returns_structured_error(self) -> None:
        """Test upshift fails gracefully when insufficient memory."""
        # Create backend with low available memory
        backend = make_mock_backend(available_memory=1000)
        clutch = make_mock_clutch(backend=backend)
        tool = UpshiftTool(clutch)

        result = await tool.execute("llama-70b", 500000)

        assert result.success is False
        assert result.error is not None
        assert "insufficient resources" in result.error.lower()
        assert "Upshift failed" in result.message

    @pytest.mark.asyncio
    async def test_upshift_load_failure_returns_structured_error(self) -> None:
        """Test upshift fails gracefully when model load fails."""
        backend = make_mock_backend(should_load_fail=True)
        clutch = make_mock_clutch(backend=backend)
        tool = UpshiftTool(clutch)

        result = await tool.execute("llama-70b", 500000)

        assert result.success is False
        assert result.error is not None
        assert "failed" in result.error.lower()
        assert result.message != ""


class TestDownshiftToolExecution:
    """Tests for DownshiftTool execution."""

    @pytest.mark.asyncio
    async def test_downshift_success(self) -> None:
        """Test successful downshift operation."""
        clutch = make_mock_clutch()
        with patch.object(
            clutch.infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True
            # First upshift to a heavy model
            await clutch.upshift("llama-70b", 500000)

            tool = DownshiftTool(clutch)
            result = await tool.execute("llama-7b", 100000)

            assert isinstance(result, ToolResult)
            assert result.success is True
            assert result.active_model == "llama-7b"
            assert result.cluster_health is not None
            assert result.error is None
            assert "Successfully downshifted" in result.message

    @pytest.mark.asyncio
    async def test_downshift_with_reason(self) -> None:
        """Test downshift with audit logging reason."""
        clutch = make_mock_clutch()
        with patch.object(
            clutch.infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True
            await clutch.upshift("llama-70b", 500000)

            tool = DownshiftTool(clutch)
            reason = "Complex reasoning phase complete"

            result = await tool.execute("llama-7b", 100000, reason=reason)

            assert result.success is True
            assert result.active_model == "llama-7b"

    @pytest.mark.asyncio
    async def test_downshift_insufficient_memory_returns_structured_error(
        self,
    ) -> None:
        """Test downshift fails gracefully when insufficient memory."""
        backend = make_mock_backend(available_memory=1000)
        clutch = make_mock_clutch(backend=backend)
        tool = DownshiftTool(clutch)

        result = await tool.execute("llama-7b", 100000)

        assert result.success is False
        assert result.error is not None
        assert "insufficient resources" in result.error.lower()

    @pytest.mark.asyncio
    async def test_downshift_load_failure_returns_structured_error(self) -> None:
        """Test downshift fails gracefully when model load fails."""
        backend = make_mock_backend(should_load_fail=True)
        clutch = make_mock_clutch(backend=backend)
        tool = DownshiftTool(clutch)

        result = await tool.execute("llama-7b", 100000)

        assert result.success is False
        assert result.error is not None


class TestStatusToolExecution:
    """Tests for StatusTool execution."""

    def test_status_success(self) -> None:
        """Test successful status check."""
        clutch = make_mock_clutch()
        tool = StatusTool(clutch)

        result = tool.execute()

        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.cluster_health is not None
        assert result.error is None
        assert "Cluster status" in result.message

    @pytest.mark.asyncio
    async def test_status_returns_current_active_model(self) -> None:
        """Test status returns the currently active model."""
        backend = make_mock_backend(available_memory=1000000)
        clutch = make_mock_clutch(backend=backend)
        with patch.object(
            clutch.infra_manager, "verify_topology", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True
            # Set active model by engaging it
            await clutch.engage("llama-7b")

        tool = StatusTool(clutch)
        result = tool.execute()

        assert result.success is True
        # active_model should be set after engage
        assert result.active_model == "llama-7b"

    def test_status_returns_cluster_health(self) -> None:
        """Test status returns cluster health status."""
        clutch = make_mock_clutch()
        tool = StatusTool(clutch)

        result = tool.execute()

        assert result.success is True
        assert isinstance(result.cluster_health, bool)


class TestToolResultDataclass:
    """Tests for the ToolResult dataclass."""

    def test_tool_result_creation(self) -> None:
        """Test ToolResult can be created with all fields."""
        result = ToolResult(
            success=True,
            active_model="llama-70b",
            cluster_health=True,
            message="Operation successful",
            error=None,
        )

        assert result.success is True
        assert result.active_model == "llama-70b"
        assert result.cluster_health is True
        assert result.message == "Operation successful"
        assert result.error is None

    def test_tool_result_with_error(self) -> None:
        """Test ToolResult with error information."""
        result = ToolResult(
            success=False,
            active_model=None,
            cluster_health=False,
            message="Operation failed",
            error="Memory limit exceeded",
        )

        assert result.success is False
        assert result.error == "Memory limit exceeded"


class TestGetOpenclawTools:
    """Tests for the get_openclaw_tools convenience function."""

    def test_get_openclaw_tools_returns_list_of_schemas(self) -> None:
        """Test that get_openclaw_tools returns a list of tool schemas."""
        clutch = make_mock_clutch()
        tools = get_openclaw_tools(clutch)

        assert isinstance(tools, list)
        assert len(tools) == 3

    def test_get_openclaw_tools_includes_all_tools(self) -> None:
        """Test that get_openclaw_tools includes all three tools."""
        clutch = make_mock_clutch()
        tools = get_openclaw_tools(clutch)

        tool_names = [tool["function"]["name"] for tool in tools]
        assert "upshift" in tool_names
        assert "downshift" in tool_names
        assert "status" in tool_names

    def test_get_openclaw_tools_returns_valid_schemas(self) -> None:
        """Test that all returned tools are valid schemas."""
        clutch = make_mock_clutch()
        tools = get_openclaw_tools(clutch)

        for tool in tools:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]


class TestGetToolExecutor:
    """Tests for the get_tool_executor helper function."""

    def test_get_tool_executor_returns_upshift_tool(self) -> None:
        """Test get_tool_executor returns UpshiftTool for 'upshift'."""
        clutch = make_mock_clutch()
        executor = get_tool_executor(clutch, "upshift")

        assert isinstance(executor, UpshiftTool)
        assert executor.clutch is clutch

    def test_get_tool_executor_returns_downshift_tool(self) -> None:
        """Test get_tool_executor returns DownshiftTool for 'downshift'."""
        clutch = make_mock_clutch()
        executor = get_tool_executor(clutch, "downshift")

        assert isinstance(executor, DownshiftTool)
        assert executor.clutch is clutch

    def test_get_tool_executor_returns_status_tool(self) -> None:
        """Test get_tool_executor returns StatusTool for 'status'."""
        clutch = make_mock_clutch()
        executor = get_tool_executor(clutch, "status")

        assert isinstance(executor, StatusTool)
        assert executor.clutch is clutch

    def test_get_tool_executor_returns_none_for_unknown_tool(self) -> None:
        """Test get_tool_executor returns None for unknown tool name."""
        clutch = make_mock_clutch()
        executor = get_tool_executor(clutch, "unknown_tool")

        assert executor is None


class TestErrorMessagesAreAgentReadable:
    """Tests that error messages are formatted for agent consumption."""

    @pytest.mark.asyncio
    async def test_upshift_error_message_is_readable(self) -> None:
        """Test upshift error message is clear and actionable."""
        backend = make_mock_backend(available_memory=1000)
        clutch = make_mock_clutch(backend=backend)
        tool = UpshiftTool(clutch)

        result = await tool.execute("llama-70b", 500000)

        assert result.error is not None
        # Message should explain the problem and suggest action
        assert len(result.error) > 0
        error_lower = result.error.lower()
        assert (
            "insufficient resources" in error_lower or "failed" in error_lower
        )

    @pytest.mark.asyncio
    async def test_downshift_error_message_is_readable(self) -> None:
        """Test downshift error message is clear and actionable."""
        backend = make_mock_backend(available_memory=1000)
        clutch = make_mock_clutch(backend=backend)
        tool = DownshiftTool(clutch)

        result = await tool.execute("llama-7b", 100000)

        assert result.error is not None
        assert len(result.error) > 0

    def test_status_error_message_is_readable(self) -> None:
        """Test status error message is clear."""
        clutch = make_mock_clutch()
        tool = StatusTool(clutch)

        # Status shouldn't error in normal conditions, but if it did,
        # the message should be readable
        result = tool.execute()
        assert isinstance(result.message, str)
        assert len(result.message) > 0


class TestToolInitialization:
    """Tests for tool initialization."""

    def test_upshift_tool_stores_clutch_reference(self) -> None:
        """Test UpshiftTool stores the clutch instance."""
        clutch = make_mock_clutch()
        tool = UpshiftTool(clutch)

        assert tool.clutch is clutch

    def test_downshift_tool_stores_clutch_reference(self) -> None:
        """Test DownshiftTool stores the clutch instance."""
        clutch = make_mock_clutch()
        tool = DownshiftTool(clutch)

        assert tool.clutch is clutch

    def test_status_tool_stores_clutch_reference(self) -> None:
        """Test StatusTool stores the clutch instance."""
        clutch = make_mock_clutch()
        tool = StatusTool(clutch)

        assert tool.clutch is clutch
