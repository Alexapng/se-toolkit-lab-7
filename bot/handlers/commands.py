"""Command handlers without Telegram dependencies."""

from __future__ import annotations


def handle_start() -> str:
    return "Welcome! I am your LMS helper bot."


def handle_help() -> str:
    return "Available commands: /start, /help, /health, /labs, /scores"


def handle_health() -> str:
    return "Backend health check is not implemented yet."


def handle_labs() -> str:
    return "Labs list is not implemented yet."


def handle_scores() -> str:
    return "Scores lookup is not implemented yet."


def handle_unknown() -> str:
    return "Not implemented yet."
