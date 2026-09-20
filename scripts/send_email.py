#!/usr/bin/env python3
"""Send a redacted Codex completion summary without persisting credentials."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import smtplib
import sys
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

MAX_BODY = 20_000
SECRET_PATTERNS = (
    re.compile(r"(?is)(password|passwd|pwd|token|secret|api[_-]?key|private[_-]?key)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?is)bearer\s+[A-Za-z0-9._~+/=-]+"),
)


def _keyring_value(name: str) -> Optional[str]:
    try:
        import keyring  # type: ignore

        service = os.getenv("EMAIL_NOTIFY_KEYRING_SERVICE", "codex-email-notify")
        value = keyring.get_password(service, name)
        return value.strip() if value else None
    except Exception:
        # A missing/broken backend is a normal reason to use the protected env fallback.
        return None


def setting(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = _keyring_value(name) or os.getenv(name) or default
    if required and not value:
        raise ValueError(f"missing protected setting: {name}")
    return value or ""


def redact(text: str) -> str:
    clean = text[:MAX_BODY]
    for pattern in SECRET_PATTERNS:
        clean = pattern.sub(lambda m: m.group(0).split(":", 1)[0].split("=", 1)[0] + "=[REDACTED]", clean)
    # Avoid accidentally echoing local secret values supplied through the environment.
    for name in ("EMAIL_NOTIFY_SMTP_PASSWORD", "EMAIL_NOTIFY_SMTP_USER"):
        secret = os.getenv(name)
        if secret:
            clean = clean.replace(secret, "[REDACTED]")
    return clean


def digest(subject: str, body: str) -> str:
    return hashlib.sha256((subject.strip() + "\n" + body).encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, help="UTF-8 summary file; otherwise read stdin")
    source.add_argument("--text", help=argparse.SUPPRESS)
    parser.add_argument("--subject", default="Codex task completed")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="ignore an existing sent digest")
    parser.add_argument("--retries", type=int, default=None)
    return parser.parse_args()


def load_body(args: argparse.Namespace) -> str:
    if args.text is not None:
        raw = args.text
    elif args.input:
        raw = args.input.read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()
    return redact(raw).strip()


def main() -> int:
    args = parse_args()
    try:
        body = load_body(args)
        if not body:
            raise ValueError("summary is empty")
        subject = redact(args.subject).strip()[:200] or "Codex task completed"
        payload_digest = digest(subject, body)
        state_dir = Path(setting("EMAIL_NOTIFY_STATE_DIR", ".email-notify-state"))
        marker = state_dir / f"{payload_digest}.sent"
        if marker.exists() and not args.force:
            print("notification already sent (idempotency digest matched)")
            return 0
        host = setting("EMAIL_NOTIFY_SMTP_HOST", required=True)
        port = int(setting("EMAIL_NOTIFY_SMTP_PORT", "587"))
        user = setting("EMAIL_NOTIFY_SMTP_USER")
        password = setting("EMAIL_NOTIFY_SMTP_PASSWORD")
        sender = setting("EMAIL_NOTIFY_FROM", user, required=True)
        recipients = [item.strip() for item in setting("EMAIL_NOTIFY_TO", required=True).split(",") if item.strip()]
        if not recipients:
            raise ValueError("missing protected setting: EMAIL_NOTIFY_TO")
        timeout = float(setting("EMAIL_NOTIFY_SMTP_TIMEOUT", "20"))
        retries = max(0, args.retries if args.retries is not None else int(setting("EMAIL_NOTIFY_RETRIES", "3")))
        retry_base = max(0.1, float(setting("EMAIL_NOTIFY_RETRY_BASE_SECONDS", "1")))
        if args.dry_run:
            print(f"dry-run ok: body_chars={len(body)} digest={payload_digest} retries={retries}")
            return 0

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = ", ".join(recipients)
        message.set_content(body)
        last_error: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
                    if user:
                        smtp.login(user, password)
                    smtp.send_message(message)
                state_dir.mkdir(parents=True, exist_ok=True)
                marker.write_text("sent\n", encoding="ascii")
                print(f"notification sent: digest={payload_digest}")
                return 0
            except (OSError, smtplib.SMTPException) as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(retry_base * (2 ** attempt))
        print(f"notification failed after {retries + 1} attempts: {type(last_error).__name__}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"notification configuration/input error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
