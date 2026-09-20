---
name: email-notify
description: Send a concise, sanitized summary of a completed Codex task by email. Use only when the user explicitly asks for email notification or invokes this skill; never expose SMTP credentials in prompts, files, message bodies, or logs.
metadata:
  short-description: Securely email completed-task summaries
---

# Email notification

Use this skill at the end of a completed task when the user has requested an email update. First assemble a short result summary (outcome, changed files, checks, and known limitations). Remove credentials, access tokens, private keys, and sensitive configuration values before sending.

Run the bundled helper with a summary from stdin or `--input`:

```powershell
Get-Content .\completion-summary.txt -Raw |
  python .\email-notify\scripts\send_email.py --subject "Codex task completed"
```

Use `--dry-run` to validate resolution, redaction, idempotency, and message construction without connecting to SMTP. The helper retries transient SMTP failures with bounded exponential backoff, applies a timeout, and records only a payload digest and outcome in the audit directory. A successful digest is not sent again unless `--force` is supplied.

Credentials and addresses must be provisioned outside the Codex conversation. The helper checks the OS keychain through the optional `keyring` package first (service `codex-email-notify`, keys named by the `EMAIL_NOTIFY_*` setting), then falls back to environment variables. Never put real values in this skill, a prompt, a summary, or a committed config file. See `README.md` for keychain setup and the complete setting list.

Do not claim delivery unless the helper exits successfully. If SMTP is unavailable, report the failure locally and preserve the summary for a later retry; do not print secret values.
