# 腾讯云服务器部署指南

本指南将指导你如何将机器人部署到腾讯云服务器（轻量应用服务器/CVM）。

> **⚠️ 重要提示**
> 由于 Telegram 的网络封锁，**请务必选择海外地域的服务器**（如：**中国香港**、新加坡、东京、硅谷等）。
> 如果选择中国内地服务器，你是无法直接连接 Telegram API 的！

## 1. 准备工作

*   一台 **海外地域** 的腾讯云服务器 (推荐 CentOS 7.9 或 Ubuntu 20.04/22.04)。
*   本地电脑上已经运行成功，并生成了以下关键文件：
    *   `.env` (配置文件)
    *   `vault.db` (数据库，包含加密密钥)
    *   `*.session` (Bot、主号、闲置号的登录凭证)

## 2. 环境安装

登录服务器终端（SSH），根据系统执行命令：

### Ubuntu / Debian
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git -y
```

### CentOS 7.9
```bash
sudo yum install python3 python3-pip git -y
```

## 3. 获取代码

推荐使用 git 拉取代码：

```bash
cd /home/
git clone https://github.com/YiQing-House/-tg-.git TelegramVault
cd TelegramVault
```

## 4. 上传敏感文件 (关键步骤)

由于 `.env` 和 `session` 文件不在 GitHub 仓库中（为了安全），你需要从本地电脑上传它们。

**推荐使用 FTP 工具 (如 FileZilla, WinSCP) 或 SCP 命令上传以下文件到服务器的 `/home/TelegramVault/` 目录：**

1.  `.env`
2.  `vault.db`
3.  `vault_bot.session`
4.  `vault_user.session`
5.  `vault_storage.session`
6.  `vault_storage.session-journal` (如果有)

> **注意**: 如果不上传 session 文件，你在服务器上启动时需要重新输入手机号验证码，这可能因为服务器 IP 变动导致风控。直接上传本地生成的 session 文件最稳妥。

## 5. 安装依赖

```bash
# 创建虚拟环境 (推荐)
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install python-dotenv  # 确保安装了这个
```

## 6. 测试运行

先尝试前台运行，观察有无报错：

```bash
python bot.py
```

*   如果显示 `Telegram Private Vault is running...` 且无报错，说明成功。
*   按 `Ctrl + C` 停止运行。

## 7. 设置后台运行 (Systemd 保活)

为了让机器人即使关闭 SSH 也能一直运行，并且开机自启，我们创建 Systemd 服务。

**1. 创建服务文件**
```bash
sudo nano /etc/systemd/system/tgvault.service
```

**2. 粘贴以下内容** (请修改 `User` 和 `WorkingDirectory` 为实际路径)

```ini
[Unit]
Description=Telegram Private Vault Bot
After=network.target

[Service]
# 修改为你的服务器用户名 (如 root 或 ubuntu)
User=root
# 修改为你的项目路径
WorkingDirectory=/home/TelegramVault
# 修改为你的 python 路径 (如果有 venv，指向 venv 的 python)
ExecStart=/home/TelegramVault/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**3. 启动服务**

```bash
sudo systemctl daemon-reload
sudo systemctl enable tgvault
sudo systemctl start tgvault
```

**4. 查看状态与日志**

```bash
# 查看状态
sudo systemctl status tgvault

# 查看实时日志 (排查问题用)
sudo journalctl -u tgvault -f
```

## 常见问题

Q: 报错 `Peer id invalid`？
A: 你的 `*.session` 文件可能没上传对，或者服务器环境下的 session 缓存丢失。请尝试在本地重新运行一遍同步，把新的 session 文件上传上去。

Q: 连接超时 (ConnectionTimeout)？
A: 检查你的服务器是不是**中国内地**的。内地服务器无法连接 Telegram。你需要换到香港/新加坡节点。
