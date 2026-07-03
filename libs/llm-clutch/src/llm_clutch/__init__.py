"""llm-clutch package."""

from llm_clutch.core.clutch import (
    EngineState,
    EngineStatus,
    LLMClutch,
    ShiftResult,
)

__version__ = "0.1.0"

__all__ = [
    "LLMClutch",
    "EngineState",
    "EngineStatus",
    "ShiftResult",
]
