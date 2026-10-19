---
name: email-notify
description: Send a concise, sanitized summary of a completed Codex task by email. Use only when the user explicitly asks for email notification or invokes this skill; never expose SMTP credentials in prompts, files, message bodies, or logs.
metadata:
  short-description: Securely email completed-task summaries
---

# Email notification

Use this skill at the end of a completed task when the user invokes `$email-notify` or explicitly requests an email update. First assemble a short result summary (outcome, changed files, checks, and known limitations). Remove credentials, access tokens, private keys, and sensitive configuration values before sending. Then hand the summary to the bundled email sender, `scripts/send_email.py`; this skill is the user-facing notification entry point, and the script performs delivery.

Run the bundled helper with a summary from stdin or `--input`:

```powershell
Get-Content .\completion-summary.txt -Raw |
  python .\email-notify\scripts\send_email.py --subject "Codex task completed" --to "team@example.com"
```

The configured default recipient is always included. Any address specified in the user's prompt is an additional recipient; pass it with `--to` (repeat the option or use comma-separated addresses for multiple additions). The helper sends a separate email to each recipient, so recipients do not see one another's addresses. Do not replace or omit the configured default recipient. Include no recipient override when the user did not specify one.

Use `--dry-run` to validate resolution and redaction without connecting to SMTP. The helper sends and tracks each recipient separately, retries transient SMTP failures with bounded exponential backoff, applies a timeout, and records only recipient-specific payload digests locally. A successfully delivered recipient is not sent the same summary again unless `--force` is supplied; failed recipients can be retried without resending to recipients that already succeeded.

Credentials and addresses must be provisioned outside the Codex conversation. The helper checks the OS keychain through the optional `keyring` package first (service `codex-email-notify`, keys named by the `EMAIL_NOTIFY_*` setting), then falls back to environment variables. Never put real values in this skill, a prompt, a summary, or a committed config file. See `README.md` for keychain setup and the complete setting list.

Do not claim delivery unless the helper exits successfully. If SMTP is unavailable, report the failure locally and preserve the summary for a later retry; do not print secret values.
