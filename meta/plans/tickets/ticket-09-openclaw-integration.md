# Ticket 09: OpenClaw Tool Integration

**Title:** `feat: [create OpenClaw agent tool wrapper for self-escalation]`

**Labels:** `enhancement`

## What do you want to build?

Create a pre-formatted tool definition in `integrations/openclaw.py`
that allows llm-clutch to be directly injected into an OpenClaw agent
as an executable tool. This enables the agent to self-escalate by
detecting a complex task and autonomously swapping to a heavier reasoning
model, then downshifting when the task is complete.

## Acceptance Criteria

- [ ] `libs/llm-clutch/src/llm_clutch/integrations/openclaw.py` contains tool definition(s) compatible with OpenClaw's tool schema
- [ ] An `upshift_tool` definition exposes `upshift()` with parameters: `model_name` (str), `required_ram` (int), and optional `reason` (str, for audit logging)
- [ ] A `downshift_tool` definition exposes `downshift()` with the same parameter shape
- [ ] A `status_tool` definition exposes `status()` so the agent can inspect cluster state before deciding to shift
- [ ] Tool definitions include clear descriptions that help the LLM agent understand when and why to use each tool
- [ ] The tool wrapper handles async execution and returns structured results (success/failure, active model, available memory)
- [ ] Error responses are formatted as agent-readable messages (not raw exceptions)
- [ ] Unit tests validate tool schema shape, successful invocation, and error handling
- [ ] `uv run ruff check .` and `uv run pytest` pass

## Implementation Notes

- The tool definitions should follow OpenClaw's expected format — likely
  a JSON schema or Python callable with specific metadata. If the exact
  OpenClaw tool specification is not finalized, design the wrapper as a
  simple Python callable with a `tool_schema()` class method that returns
  the JSON schema definition. Mark the format as provisional with a
  `# TODO: Verify against OpenClaw tool spec` comment.
- The `reason` parameter on upshift/downshift is for audit/logging
  purposes — it lets the agent explain why it chose to escalate
  (e.g., "Complex multi-step reasoning task detected").
- The wrapper should instantiate or receive an `LLMClutch` instance and
  delegate all logic to it — no business logic should live in the
  integration layer.
- Consider providing a convenience function
  `get_openclaw_tools(clutch: LLMClutch) -> list[dict]` that returns all
  tool definitions ready for injection into an OpenClaw agent config.
