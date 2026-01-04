# 🤖 机器人部署与服务器迁移指南

本指南旨在帮助您将本地开发环境中的机器人完美迁移到 Linux 服务器（如腾讯云、硅谷节点等海外 VPS）上运行。

---

## 📋 部署前准备 (重要)

由于本项目的安全性设计，敏感信息不会同步到 GitHub。在迁移前，请确保您的本地文件夹中包含以下 **不可或缺** 的文件：

| 文件名 | 作用 | 迁移建议 |
| :--- | :--- | :--- |
| `config.py` | 您的所有 API 密钥和 ID | 必须手动上传 |
| `vault.db` | **核心数据库**，包含所有文件的加密密钥 | 必须手动上传，否则文件无法解密 |
| `vault_bot.session` | 机器人的登录凭证 | 推荐上传，免去二次配置 |
| `vault_user.session` | 管理员账号的登录凭证 | 推荐上传，防止异地登录风控 |
| `vault_storage.session`| 存储账号的登录凭证 | 推荐上传 |

---

## 🛠️ 第一步：服务器环境初始化

### 1. 更新系统并安装 Python
建议使用 Ubuntu 20.04+ 或 Debian 系统。

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv git -y
```

### 2. 获取代码
```bash
cd /opt
sudo git clone https://github.com/YiQing-House/-tg-.git tg_vault
sudo chown -R $USER:$USER /opt/tg_vault
cd tg_vault
```

### 3. 创建虚拟环境并安装依赖
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install tgcrypto  # 强烈建议安装，可将解密速度提升 10 倍以上
```

---

## 📦 第二步：迁移核心文件

使用 `SCP` 指令或 `WinSCP/FileZilla` 等工具，将本地的以下文件上传到服务器的 `/opt/tg_vault/` 根目录：

- `config.py`
- `vault.db`
- `*.session` (共 3 个文件)

---

## 🚀 第三步：后台保活配置 (Systemd)

为了让机器人在关掉 SSH 后依然运行，并实现开机自启：

1.  **创建服务文件**:
    ```bash
    sudo nano /etc/systemd/system/tgvault.service
    ```
2.  **写入以下配置**:
    ```ini
    [Unit]
    Description=Telegram Private Vault Service
    After=network.target

    [Service]
    User=root
    WorkingDirectory=/opt/tg_vault
    ExecStart=/opt/tg_vault/venv/bin/python bot.py
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target
    ```
3.  **启动服务**:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable tgvault
    sudo systemctl start tgvault
    ```

---

## 🖥️ 宝塔面板 (Baota) 快速部署

如果您使用宝塔面板，可以更简单地部署：

1.  使用 **Python项目管理器**。
2.  **添加项目**:
    - 路径选择解压后的文件夹（确保包含了上传的 `vault.db` 和 `session`）。
    - 启动文件选 `bot.py`。
    - 勾选 **“安装模块依赖”**。
3.  **手动安装 TgCrypto**:
    - 在项目虚拟环境中执行 `pip install tgcrypto` 以保证加解密性能。
4.  **注意**: 即使在宝塔上，也要确认存储路径是否有写入权限。

---

## ❓ 常见问题排查

- **Q: 启动提示 `Peer id invalid`？**
  - A: Session 文件失效或未上传。建议在本地删除该 session 重新登录一次，再将新生成的 session 上传到服务器。
- **Q: 磁盘空间报警？**
  - A: 本项目已有“流式分片清理”机制，但如果您单次处理的文件极大，请确保磁盘剩余空间大于单文件大小的 3 倍。
- **Q: 连接超时？**
  - A: 请确认服务器位于 **中国大陆以外**，且防火墙已放行 8080 端口（如果您开启了 Web 播放功能）。
