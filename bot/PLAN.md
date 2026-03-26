# Bot Development Plan

The bot will be built in layers so each step is testable before deployment. First, we establish a transport-independent handler architecture: command handlers return plain text and do not depend on Telegram classes. The entry point in `bot.py` runs in two modes. In `--test` mode it calls the same handlers directly and prints to stdout. In Telegram mode it receives messages, passes text to the same routing logic, and sends the response back. This gives us one source of truth for behavior.

For backend integration, we will add a small API client in `services/` that uses `LMS_API_BASE_URL` and `LMS_API_KEY` with Bearer auth. Handlers like `/health`, `/labs`, and `/scores` will call this client and return user-friendly messages with safe error handling and timeouts.

For natural language queries, we will add an intent layer driven by an LLM with tool descriptions for available actions. The LLM decides which tool to call, while tools map to handler/service functions. Fallback behavior is only for service unavailability, not regex routing.

For deployment, we will package runtime dependencies in `bot/pyproject.toml`, run with `uv`, and verify both CLI test mode and live Telegram polling on the VM. After each milestone we will validate acceptance criteria and keep the bot runnable end to end.
