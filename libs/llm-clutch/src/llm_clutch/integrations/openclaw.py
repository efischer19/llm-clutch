"""OpenClaw agent tool wrapper for llm-clutch.

This module provides tool definitions that allow llm-clutch to be directly
injected into an OpenClaw agent as executable tools. The tools enable the
agent to self-escalate by detecting complex tasks and autonomously swapping
to a heavier reasoning model, then downshifting when the task is complete.

Note: These tool schemas follow a provisional JSON schema format. The exact
OpenClaw tool specification may change; when finalized, verify schema
compatibility and update if necessary.
"""

from dataclasses import dataclass
from typing import Any

import structlog

from llm_clutch.core.clutch import LLMClutch

logger = structlog.get_logger(__name__)


@dataclass
class ToolResult:
    """Structured result returned by OpenClaw tools.

    Attributes:
        success: Whether the operation completed successfully.
        active_model: The currently loaded model, or None.
        cluster_health: Whether the cluster is healthy.
        message: Human-readable result message for the agent.
        error: Error message if the operation failed, None otherwise.
    """

    success: bool
    active_model: str | None
    cluster_health: bool
    message: str
    error: str | None = None


class UpshiftTool:
    """Tool for escalating to a heavier reasoning model.

    This tool allows an OpenClaw agent to detect complex tasks and
    autonomously upshift to a heavier model for enhanced reasoning.
    """

    def __init__(self, clutch: LLMClutch) -> None:
        """Initialize the upshift tool.

        Args:
            clutch: The LLMClutch instance managing model switching.
        """
        self.clutch = clutch

    @classmethod
    def tool_schema(cls) -> dict[str, Any]:
        """Return the OpenClaw-compatible tool schema.

        Returns:
            A JSON schema definition describing the tool's parameters
            and expected behavior.
        """
        return {
            "type": "function",
            "function": {
                "name": "upshift",
                "description": (
                    "Escalate to a heavier reasoning model for complex tasks. "
                    "Use this when the current model is struggling or when "
                    "multi-step reasoning is needed. Returns cluster health status "
                    "and the active model after the shift."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model_name": {
                            "type": "string",
                            "description": (
                                "Name of the heavier model to load "
                                "(e.g., 'llama-70b', 'claude-opus')"
                            ),
                        },
                        "required_ram": {
                            "type": "integer",
                            "description": (
                                "Required memory in bytes for the model. "
                                "The system will verify availability before shifting."
                            ),
                            "minimum": 1,
                        },
                        "reason": {
                            "type": "string",
                            "description": (
                                "Optional explanation for the upshift, "
                                "used for audit logging (e.g., "
                                "'Complex multi-step reasoning task detected')"
                            ),
                        },
                    },
                    "required": ["model_name", "required_ram"],
                },
            },
        }

    async def execute(
        self, model_name: str, required_ram: int, reason: str = ""
    ) -> ToolResult:
        """Execute the upshift operation.

        Args:
            model_name: Name of the heavier model to load.
            required_ram: Required memory in bytes for the model.
            reason: Optional explanation for audit logging.

        Returns:
            ToolResult containing success status, active model, cluster health,
            and an agent-readable message.
        """
        try:
            # Log with optional reason parameter
            log_kwargs = {
                "model_name": model_name,
                "required_ram": required_ram,
            }
            if reason:
                log_kwargs["reason"] = reason
            logger.info("upshift_initiated_by_agent", **log_kwargs)

            await self.clutch.upshift(model_name, required_ram)

            status = self.clutch.status()
            message = (
                f"Successfully upshifted to {model_name}. "
                f"Cluster health: {status.cluster_health}"
            )

            return ToolResult(
                success=True,
                active_model=status.active_model,
                cluster_health=status.cluster_health,
                message=message,
            )

        except ValueError as e:
            error_msg = (
                f"Upshift failed: insufficient resources or invalid parameters. "
                f"{str(e)}"
            )
            logger.error(
                "upshift_failed_validation",
                model_name=model_name,
                required_ram=required_ram,
                error=str(e),
            )
            status = self.clutch.status()
            return ToolResult(
                success=False,
                active_model=status.active_model,
                cluster_health=status.cluster_health,
                message=error_msg,
                error=error_msg,
            )

        except Exception as e:
            error_msg = (
                f"Upshift to {model_name} failed: {str(e)}. "
                "The cluster may be in an unstable state. "
                "Consider checking cluster health before retrying."
            )
            logger.error(
                "upshift_failed",
                model_name=model_name,
                required_ram=required_ram,
                error=str(e),
                exc_info=True,
            )
            status = self.clutch.status()
            return ToolResult(
                success=False,
                active_model=status.active_model,
                cluster_health=status.cluster_health,
                message=error_msg,
                error=error_msg,
            )


class DownshiftTool:
    """Tool for downshifting to a lighter model.

    This tool allows an OpenClaw agent to conserve resources by
    downshifting to a lighter model when complex reasoning is complete.
    """

    def __init__(self, clutch: LLMClutch) -> None:
        """Initialize the downshift tool.

        Args:
            clutch: The LLMClutch instance managing model switching.
        """
        self.clutch = clutch

    @classmethod
    def tool_schema(cls) -> dict[str, Any]:
        """Return the OpenClaw-compatible tool schema.

        Returns:
            A JSON schema definition describing the tool's parameters
            and expected behavior.
        """
        return {
            "type": "function",
            "function": {
                "name": "downshift",
                "description": (
                    "Downshift to a lighter model to conserve cluster resources. "
                    "Use this when complex reasoning is complete and a simpler "
                    "model can handle the remaining work. Returns cluster health "
                    "status and the active model after the shift."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model_name": {
                            "type": "string",
                            "description": (
                                "Name of the lighter model to load "
                                "(e.g., 'llama-7b', 'claude-haiku')"
                            ),
                        },
                        "required_ram": {
                            "type": "integer",
                            "description": (
                                "Required memory in bytes for the model. "
                                "The system will verify availability before shifting."
                            ),
                            "minimum": 1,
                        },
                        "reason": {
                            "type": "string",
                            "description": (
                                "Optional explanation for the downshift, "
                                "used for audit logging (e.g., "
                                "'Complex reasoning phase complete, switching to "
                                "lightweight inference')"
                            ),
                        },
                    },
                    "required": ["model_name", "required_ram"],
                },
            },
        }

    async def execute(
        self, model_name: str, required_ram: int, reason: str = ""
    ) -> ToolResult:
        """Execute the downshift operation.

        Args:
            model_name: Name of the lighter model to load.
            required_ram: Required memory in bytes for the model.
            reason: Optional explanation for audit logging.

        Returns:
            ToolResult containing success status, active model, cluster health,
            and an agent-readable message.
        """
        try:
            # Log with optional reason parameter
            log_kwargs = {
                "model_name": model_name,
                "required_ram": required_ram,
            }
            if reason:
                log_kwargs["reason"] = reason
            logger.info("downshift_initiated_by_agent", **log_kwargs)

            await self.clutch.downshift(model_name, required_ram)

            status = self.clutch.status()
            message = (
                f"Successfully downshifted to {model_name}. "
                f"Cluster health: {status.cluster_health}"
            )

            return ToolResult(
                success=True,
                active_model=status.active_model,
                cluster_health=status.cluster_health,
                message=message,
            )

        except ValueError as e:
            error_msg = (
                f"Downshift failed: insufficient resources or invalid parameters. "
                f"{str(e)}"
            )
            logger.error(
                "downshift_failed_validation",
                model_name=model_name,
                required_ram=required_ram,
                error=str(e),
            )
            status = self.clutch.status()
            return ToolResult(
                success=False,
                active_model=status.active_model,
                cluster_health=status.cluster_health,
                message=error_msg,
                error=error_msg,
            )

        except Exception as e:
            error_msg = (
                f"Downshift to {model_name} failed: {str(e)}. "
                "The cluster may be in an unstable state. "
                "Consider checking cluster health before retrying."
            )
            logger.error(
                "downshift_failed",
                model_name=model_name,
                required_ram=required_ram,
                error=str(e),
                exc_info=True,
            )
            status = self.clutch.status()
            return ToolResult(
                success=False,
                active_model=status.active_model,
                cluster_health=status.cluster_health,
                message=error_msg,
                error=error_msg,
            )


class StatusTool:
    """Tool for inspecting cluster state before shifting.

    This tool allows an OpenClaw agent to check the current cluster
    health and active model before deciding to upshift or downshift.
    """

    def __init__(self, clutch: LLMClutch) -> None:
        """Initialize the status tool.

        Args:
            clutch: The LLMClutch instance managing model switching.
        """
        self.clutch = clutch

    @classmethod
    def tool_schema(cls) -> dict[str, Any]:
        """Return the OpenClaw-compatible tool schema.

        Returns:
            A JSON schema definition describing the tool's parameters
            and expected behavior.
        """
        return {
            "type": "function",
            "function": {
                "name": "status",
                "description": (
                    "Inspect the current cluster state: active model, "
                    "health status, and engine state. Use this before deciding "
                    "whether to upshift or downshift. Returns cluster health "
                    "and active model information."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

    def execute(self) -> ToolResult:
        """Execute the status check.

        Returns:
            ToolResult containing the current cluster state.
        """
        try:
            logger.info("status_check_initiated_by_agent")

            status = self.clutch.status()
            message = (
                f"Cluster status: engine_state={status.state.value}, "
                f"active_model={status.active_model}, "
                f"cluster_health={status.cluster_health}"
            )

            return ToolResult(
                success=True,
                active_model=status.active_model,
                cluster_health=status.cluster_health,
                message=message,
            )

        except Exception as e:
            error_msg = f"Status check failed: {str(e)}"
            logger.error(
                "status_check_failed",
                error=str(e),
                exc_info=True,
            )
            return ToolResult(
                success=False,
                active_model=None,
                cluster_health=False,
                message=error_msg,
                error=error_msg,
            )


# Tool registry mapping tool names to their classes
_TOOL_REGISTRY: dict[str, type[UpshiftTool | DownshiftTool | StatusTool]] = {
    "upshift": UpshiftTool,
    "downshift": DownshiftTool,
    "status": StatusTool,
}


def get_openclaw_tools(clutch: LLMClutch) -> list[dict[str, Any]]:
    """Get a list of all OpenClaw tool definitions ready for injection.

    This convenience function returns all tool definitions in a format
    that can be directly passed to an OpenClaw agent configuration.

    Args:
        clutch: The LLMClutch instance to use for all operations.

    Returns:
        A list of tool schema dictionaries compatible with OpenClaw.
        Each dictionary includes the function schema and metadata
        for agent-readable tool invocation.

    Example:
        clutch = LLMClutch(backend=exo_backend, infra_manager=infra_mgr)
        tools = get_openclaw_tools(clutch)
        agent = OpenClawAgent(tools=tools)
    """
    return [
        UpshiftTool.tool_schema(),
        DownshiftTool.tool_schema(),
        StatusTool.tool_schema(),
    ]


def get_tool_executor(
    clutch: LLMClutch, tool_name: str
) -> UpshiftTool | DownshiftTool | StatusTool | None:
    """Get the executor (instance) for a specific tool by name.

    This helper function returns the actual tool instance that has the
    execute() method, allowing OpenClaw to dispatch tool calls.

    Args:
        clutch: The LLMClutch instance to use.
        tool_name: Name of the tool ('upshift', 'downshift', or 'status').

    Returns:
        The tool executor instance, or None if tool_name is not recognized.

    Example:
        executor = get_tool_executor(clutch, 'upshift')
        result = await executor.execute(model_name='llama-70b', required_ram=500000)
    """
    tool_class = _TOOL_REGISTRY.get(tool_name)
    if tool_class is None:
        return None

    return tool_class(clutch)
