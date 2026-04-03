"""Bot entry point with test mode and Telegram runtime."""

from __future__ import annotations

import argparse
import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import load_config
from handlers.commands import (
    handle_health,
    handle_help,
    handle_labs,
    handle_scores,
    handle_start,
    handle_unknown,
)
from services.llm_client import LlmClient
from services.lms_api import LmsApiClient, LmsApiError


# ---------------------------------------------------------------------------
# Inline keyboard for /start — lets users pick common actions without typing
# ---------------------------------------------------------------------------

START_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📚 Available labs", callback_data="cmd_labs"),
            InlineKeyboardButton(text="📊 My scores", callback_data="cmd_scores"),
        ],
        [
            InlineKeyboardButton(
                text="🏆 Top students", callback_data="cmd_top_students"
            ),
            InlineKeyboardButton(
                text="🩺 Health check", callback_data="cmd_health"
            ),
        ],
    ]
)


def _build_clients() -> tuple[LmsApiClient, LlmClient]:
    """Create API and LLM clients from loaded configuration."""
    config = load_config()
    api_client = LmsApiClient(config)
    llm_client = LlmClient(config)
    return api_client, llm_client


def handle_text(user_input: str) -> str:
    """Return a response for a user message without Telegram dependencies.

    Slash commands are handled by direct handler functions.  All other text
    is routed through the LLM intent router.
    """
    normalized = user_input.strip()
    if not normalized:
        return handle_unknown()

    command = normalized.split(maxsplit=1)[0]
    slash_commands = {"/start", "/help", "/health", "/labs", "/scores"}
    if command in slash_commands:
        if command == "/start":
            return handle_start()
        if command == "/help":
            return handle_help()
        if command == "/health":
            return handle_health()
        if command == "/labs":
            return handle_labs()
        if command == "/scores":
            return handle_scores(normalized)
        return handle_unknown()

    # Natural language — route through LLM
    api_client, llm_client = _build_clients()
    try:
        return llm_client.route(normalized, api_client=api_client)
    except LmsApiError as exc:
        return str(exc)
    except Exception as exc:
        return f"AI service error: {exc}"


async def run_telegram() -> None:
    config = load_config()
    if not config.bot_token:
        raise RuntimeError("BOT_TOKEN is required in Telegram mode.")

    bot = Bot(token=config.bot_token)
    dispatcher = Dispatcher()

    @dispatcher.message()
    async def on_message(message: Message) -> None:
        response = handle_text(message.text or "")
        await message.answer(response, reply_markup=START_KEYBOARD)

    @dispatcher.callback_query()
    async def on_callback(callback) -> None:
        """Handle inline keyboard button presses."""
        data = callback.data or ""
        if data == "cmd_labs":
            response = handle_labs()
        elif data == "cmd_health":
            response = handle_health()
        elif data == "cmd_scores":
            response = "Send me a lab slug, e.g. /scores lab-04"
        elif data == "cmd_top_students":
            api_client = LmsApiClient(config)
            try:
                from handlers.commands import handle_scores

                response = handle_scores("/scores lab-04")
            except Exception:
                response = "Specify a lab, e.g. /scores lab-04"
        else:
            response = handle_text(callback.message.text or "")

        await callback.message.edit_text(
            response, reply_markup=START_KEYBOARD
        )
        await callback.answer()

    await dispatcher.start_polling(bot)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test",
        metavar="TEXT",
        help="Run a single command in offline test mode and print the response.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.test is not None:
        print(handle_text(args.test))
        return 0

    asyncio.run(run_telegram())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
