# Project Agent Rules

## LiveKit Agents API Deprecations
When working with the `livekit-agents` Python SDK, remember the following deprecations and their modern replacements:

1. **Deprecated `JobProcess.run()`**: Do not use `JobProcess.run()` to start the agent. 
   - **Correct**: Use `cli.run_app(WorkerOptions(entrypoint_fnc=...))` from `livekit.agents import cli`.

2. **Deprecated `llm.TypeInfo`**: Do not use `llm.TypeInfo()` for type descriptions in function tools or `Annotated` hints.
   - **Correct**: Use standard string annotations directly inside `Annotated` (e.g., `content: Annotated[str, "The description"]`), or use standard docstrings inside the function definition.

## Testing & Clock Mocking
When writing unit tests for functions that implement time-of-day constraints or fatigue policies (e.g. late-night task restrictions), always mock `datetime` or the system clock to guarantee deterministic test execution regardless of the local machine execution time.

## SQL Database Dialect Compatibility
Always support both SQLite and PostgreSQL. Format parameterized queries using `dialect.format_query()`. When using pgvector (`<=>` similarity) or other Postgres-specific functions, implement a pure-Python fallback calculations path for SQLite.

## Socket IPC Cross-Platform Fallback
Ensure local inter-process socket communication handles Unix Domain Sockets with a TCP localhost socket fallback (`127.0.0.1`) for compatibility with Windows environments.

## Logger Availability in Asynchronous Node Callbacks
Verify that standalone scripts and daemon workers (like LiveKit agent nodes) import `logging` and define `logger = logging.getLogger(...)` at the module level. Avoid referencing `logger` inside callbacks if it has not been declared.
