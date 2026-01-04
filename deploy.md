# 部署指南 - Telegram Private Vault

## 1. 上传文件到服务器

将以下文件/文件夹上传到服务器：

```
TelegramPrivateVault/
├── bot.py
├── config.py
├── database.py
├── requirements.txt
├── handlers/
│   ├── __init__.py
│   ├── setup.py
│   ├── tools.py
│   └── transfer.py
├── vault_bot.session        # 重要！用户登录session
├── vault_bot.session-journal # 如果有的话
└── file_vault.db            # 如果已有数据库
```

## 2. 连接服务器

```bash
ssh your-username@your-server-ip
```

## 3. 安装依赖

```bash
# 安装 Python 3.10+
sudo apt update
sudo apt install python3 python3-pip python3-venv -y

# 创建虚拟环境
cd TelegramPrivateVault
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install pyrogram tgcrypto
```

## 4. 使用 Screen 后台运行

```bash
# 安装 screen
sudo apt install screen -y

# 创建新的 screen 会话
screen -S vault_bot

# 在 screen 里运行 bot
cd TelegramPrivateVault
source venv/bin/activate
python bot.py

# 按 Ctrl+A 然后按 D 来分离 screen（bot 继续运行）
```

### Screen 常用命令

```bash
# 查看所有 screen 会话
screen -ls

# 重新连接到 screen
screen -r vault_bot

# 结束 screen 会话
screen -X -S vault_bot quit
```

## 5. 使用 systemd 服务（推荐用于生产）

创建服务文件：

```bash
sudo nano /etc/systemd/system/vault_bot.service
```

内容：

```ini
[Unit]
Description=Telegram Private Vault Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/TelegramPrivateVault
ExecStart=/home/your-username/TelegramPrivateVault/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable vault_bot
sudo systemctl start vault_bot

# 查看状态
sudo systemctl status vault_bot

# 查看日志
sudo journalctl -u vault_bot -f
```

## 6. 重要提示

1. **Session 文件**：确保上传 `vault_bot.session`，这是用户登录凭证
2. **首次运行**：如果没有 session，需要在服务器上重新登录（输入手机号和验证码）
3. **防火墙**：确保服务器能访问 Telegram API（不需要开放端口）
4. **TgCrypto**：安装 `tgcrypto` 可以大幅提升下载速度
