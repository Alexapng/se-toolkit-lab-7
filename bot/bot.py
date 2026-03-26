"""Bot entry point with test mode and Telegram runtime."""

from __future__ import annotations

import argparse
import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import Message

from config import load_config
from handlers.commands import (
    handle_health,
    handle_help,
    handle_labs,
    handle_scores,
    handle_start,
    handle_unknown,
)


def handle_text(user_input: str) -> str:
    """Return a response for a user message without Telegram dependencies."""
    normalized = user_input.strip()
    if not normalized:
        return handle_unknown()

    command = normalized.split(maxsplit=1)[0]
    if command == "/start":
        return handle_start()
    if command == "/help":
        return handle_help()
    if command == "/health":
        return handle_health()
    if command == "/labs":
        return handle_labs()
    if command == "/scores":
        return handle_scores()
    return handle_unknown()


async def run_telegram() -> None:
    config = load_config()
    if not config.bot_token:
        raise RuntimeError("BOT_TOKEN is required in Telegram mode.")

    bot = Bot(token=config.bot_token)
    dispatcher = Dispatcher()

    @dispatcher.message()
    async def on_message(message: Message) -> None:
        response = handle_text(message.text or "")
        await message.answer(response)

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
