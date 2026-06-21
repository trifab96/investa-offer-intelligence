"""Processing pipeline package.

Each module is a pure-ish step taking/returning Pydantic models. The
orchestrator (``app.pipeline.orchestrator``) wires them together and persists
status transitions: received -> parsing -> extracting -> matching ->
enriching -> scoring -> done|failed.
"""
