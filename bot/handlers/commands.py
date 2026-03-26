"""Command handlers without Telegram dependencies."""

from __future__ import annotations

from config import load_config
from services.lms_api import LmsApiClient, LmsApiError


def handle_start() -> str:
    return "Welcome! I am your LMS helper bot."


def handle_help() -> str:
    return (
        "Available commands:\n"
        "- /start - show welcome message\n"
        "- /help - list commands\n"
        "- /health - check backend status\n"
        "- /labs - list available labs\n"
        "- /scores <lab> - show pass rates for a lab"
    )


def handle_health() -> str:
    client = LmsApiClient(load_config())
    try:
        items = client.get_items()
    except LmsApiError as exc:
        return str(exc)
    return f"Backend is healthy. {len(items)} items available."


def handle_labs() -> str:
    client = LmsApiClient(load_config())
    try:
        items = client.get_items()
    except LmsApiError as exc:
        return str(exc)

    labs = [item for item in items if item.get("type") == "lab"]
    if not labs:
        return "No labs found."

    lines = ["Available labs:"]
    for lab in labs:
        title = str(lab.get("title", "Untitled lab"))
        lines.append(f"- {title}")
    return "\n".join(lines)


def handle_scores(command_text: str) -> str:
    parts = command_text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return "Usage: /scores <lab-slug>, for example: /scores lab-04"

    lab_slug = parts[1].strip()
    if not lab_slug:
        return "Usage: /scores <lab-slug>, for example: /scores lab-04"

    client = LmsApiClient(load_config())
    try:
        pass_rates = client.get_pass_rates(lab_slug)
    except LmsApiError as exc:
        return str(exc)

    if not pass_rates:
        return f"No pass-rate data found for {lab_slug}."

    lines = [f"Pass rates for {lab_slug}:"]
    for row in pass_rates:
        task = str(row.get("task", "Unknown task"))
        rate_raw = row.get(
            "avg_score",
            row.get("avg_score_pct", row.get("pass_rate_pct", row.get("value"))),
        )
        attempts_raw = row.get("submissions", row.get("attempts", row.get("count")))

        try:
            rate_text = f"{float(rate_raw):.1f}%"
        except (TypeError, ValueError):
            rate_text = str(rate_raw)

        attempts_text = ""
        if attempts_raw is not None:
            attempts_text = f" ({attempts_raw} attempts)"

        lines.append(f"- {task}: {rate_text}{attempts_text}")

    return "\n".join(lines)


def handle_unknown() -> str:
    return "Unknown command. Use /help to see available commands."
