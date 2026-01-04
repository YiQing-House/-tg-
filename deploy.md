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

## 8. 宝塔面板 (Baota) 傻瓜式部署指南

使用宝塔面板自带的 **Python项目管理器** 插件，无需敲一行命令即可部署。

### 准备工作
1. 登录宝塔面板。
2. 进入 **文件**，将本地的 `TelegramVault_Deploy.zip` 上传到 `/www/wwwroot/` 目录。
3. **解压 (关键步骤)**:
   - 在文件列表中找到 `TelegramVault_Deploy.zip`。
   - 鼠标右键点击该文件，选择 **解压**。
   - 点击 **确定**。
   - 解压后，你会看到一个新的文件夹。请将这个文件夹重命名为 `tg_vault`。
   - **检查**: 双击进入 `tg_vault`，确保能看到 `bot.py` 这个文件。
     *(如果 `bot.py` 在更深一层目录，请把它们全选剪切到 `tg_vault` 根目录下)*

### 第一步：安装 Python环境
1. 点击左侧 **软件商店**。
2. 搜索 `Python`。
3. 找到 **Python项目管理器 2.0** (或 2.5)，点击 **安装**。
4. 安装完成后，点击 **设置** (或打开插件)。
5. 点击 **版本管理** -> 选择 **Python 3.9** (或更高版本) -> 点击 **安装**。等待安装完成。

### 第二步：添加项目
1. 在 Python项目管理器中，点击 **项目管理** -> **添加项目**。
2. 填写配置：
   - **项目路径**: 选择 `/www/wwwroot/tg_vault`
   - **启动文件**: 选择 `bot.py`
   - **运行端口**: `8080` (如果没有开Web功能可随便填，如 8888)
   - **Python版本**: 选择刚才安装的 `Python 3.9`
   - **启动方式**: `python`
   - **依赖包**: ✅ **勾选 "安装模块依赖"** (它会自动读取 requirements.txt)
   - **开机启动**: ✅ **勾选**
3. 点击 **确定**。
4. 等待几分钟，它会自动安装依赖并启动项目。

### 第三步：验证运行
1. 在项目列表中，看到状态显示 **运行中** (绿色播放键)。
2. 点击右侧的 **日志**。
3. 如果看到日志输出：
   ```
   Telegram Private Vault is running...
   ```
   恭喜你，部署成功！机器人已经在后台运行了。

### 常见报错解决
- **日志显示 `ModuleNotFoundError`**: 说明依赖没装好。
  - 点击右侧 **模块** -> 手动输入 `pyrogram` 点击添加。
  - 再手动输入 `tgcrypto` 点击添加。
  - 重启项目。
- **日志显示 `Peer id invalid`**: 说明 session 文件有问题。
  - 请在 **文件** 管理器中，检查 `vault_bot.session` 是否存在且有文件大小。
  - 如果文件是 0KB 或不存在，请从本地重新上传。


---

## 常见问题

Q: 报错 `Peer id invalid`？
A: 你的 `*.session` 文件可能没上传对，或者服务器环境下的 session 缓存丢失。请尝试在本地重新运行一遍同步，把新的 session 文件上传上去。

Q: 连接超时 (ConnectionTimeout)？
A: 检查你的服务器是不是**中国内地**的。内地服务器无法连接 Telegram。你需要换到香港/新加坡节点。
