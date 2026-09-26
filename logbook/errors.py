"""Failures and passing notes, kept apart from everything that raises them.

`fail` raises rather than exits, so a web app or a bot can catch it and show the
message; `note` prints on the command line but is collected when a front end
wants the messages back instead.
"""

from __future__ import annotations

_captured: list | None = None


class LogbookError(Exception):
    """Something in the input makes a logbook impossible. Message is user-facing."""


def fail(message: str):
    raise LogbookError(str(message).strip().lstrip("!").strip())


def note(message: str):
    """Say something in passing - printed on the CLI, collected for web and bot."""
    if _captured is None:
        print(f"  * {message}")
    else:
        _captured.append(str(message))


class capture_notes:
    """Collect note() messages instead of printing them."""

    def __enter__(self):
        global _captured
        self.messages: list = []
        _captured = self.messages
        return self.messages

    def __exit__(self, *exc):
        global _captured
        _captured = None
        return False
