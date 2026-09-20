# email-notify：Codex 邮件告知技能

这个技能用于在 Codex 任务完成后，把经过脱敏的结果摘要通过 SMTP 发送到指定邮箱。它只在用户明确调用或明确要求发送邮件时运行，不会自动外发任务内容。

## 目录结构

```text
email-notify/
├── SKILL.md
├── config.example.env
├── README.md
└── scripts/
    └── send_email.py
```

- `SKILL.md`：技能触发条件、摘要格式和安全边界。
- `scripts/send_email.py`：Python 3 标准库 SMTP 发送器。
- `config.example.env`：仅列出配置项名称，不保存真实值。
- `README.md`：安装、配置、调用和故障排查说明。

## 安全配置

邮件密码、应用专用密码和访问令牌必须保存在操作系统凭据管理器或由安全的进程管理器运行时注入。不要把它们写进本仓库、命令行参数、Codex 会话、摘要或日志。

脚本优先通过 Python `keyring` 读取系统密钥链，服务名默认为 `codex-email-notify`；没有可用密钥链时，才读取受保护的进程环境变量。Windows 上可以使用“凭据管理器 → 普通凭据”保存 SMTP 用户名和应用专用密码。

## 配置项

必须配置：

```text
EMAIL_NOTIFY_SMTP_HOST
EMAIL_NOTIFY_SMTP_USER
EMAIL_NOTIFY_SMTP_PASSWORD
EMAIL_NOTIFY_FROM
EMAIL_NOTIFY_TO
```

可选配置：

```text
EMAIL_NOTIFY_SMTP_PORT=587
EMAIL_NOTIFY_SMTP_TIMEOUT=20
EMAIL_NOTIFY_RETRIES=3
EMAIL_NOTIFY_RETRY_BASE_SECONDS=1
EMAIL_NOTIFY_STATE_DIR=.email-notify-state
EMAIL_NOTIFY_KEYRING_SERVICE=codex-email-notify
```

新浪邮箱通常支持 `smtp.sina.com` 的 465/SSL 或 587/STARTTLS。使用哪一种方式取决于发送器配置；本脚本默认使用 STARTTLS，端口和 TLS 行为可以通过脚本或环境配置调整。

`config.example.env` 只用于查看变量名称。真实配置应由本机安全存储提供，例如：

```powershell
python -m pip install keyring
```

随后使用系统密钥链工具保存对应值。不要把密码写入 `.env` 文件并提交到 GitHub。

## 调用方式

从摘要文件发送：

```powershell
python .\scripts\send_email.py `
  --input .\completion-summary.txt `
  --subject "Codex 任务完成"
```

从标准输入发送：

```powershell
Get-Content .\completion-summary.txt -Raw |
  python .\scripts\send_email.py --subject "Codex 任务完成"
```

先做本地检查而不连接 SMTP：

```powershell
python .\scripts\send_email.py `
  --input .\completion-summary.txt `
  --subject "Codex 任务完成" `
  --dry-run
```

脚本会限制正文长度，脱敏常见的 `password`、`token`、`secret`、`api_key` 和 Bearer 值，并通过摘要哈希避免重复发送。需要有意重发时使用 `--force`。

## 故障排查

- `missing protected setting`：检查 SMTP 主机、用户、发件人和收件人是否已注入；密码应存在于系统凭据管理器。
- `notification failed`：检查 SMTP 主机、端口、防火墙和 TLS 设置。新浪邮箱需要启用 SMTP 服务，并使用应用专用密码。
- 重复通知被跳过：脚本发现相同摘要已经成功发送。确认重复发送确有必要后再使用 `--force`。
- `keyring` 不可用：安装并配置适合当前操作系统的 `keyring` 后端，或由安全的进程管理器注入环境变量。

脚本只会报告错误类型，不会输出密码、令牌、SMTP 密码或完整邮件正文。SMTP 成功表示服务器接受了消息，不代表收件箱一定已经投递。

## 发布说明

提交到公开仓库前，请确认没有加入真实邮箱地址、密码、应用专用密码、Token、`.email-notify-state` 或 Python 缓存文件。推荐先运行：

```powershell
python .\scripts\send_email.py --input .\completion-summary.txt --subject "Codex 任务完成" --dry-run
```

本技能不会启动开发服务。
