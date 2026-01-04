# Telegram 私人保险库 (Telegram Private Vault)

一个基于 Telegram 的无限容量、加密私人云存储解决方案。

## 简介

本项目利用 Telegram 的无限存储特性，将其转化为您的私人云盘。支持文件自动加密、指纹混淆、合集管理，完全免费且无容量限制。

**核心特性：**

*   **无限容量**: 依托 Telegram 频道，无存储上限。
*   **端到端加密**: 文件在上传前进行 AES-256 加密，确保隐私安全。Telegram 服务器也无法查看您的文件内容。
*   **双重防风控**:
    *   **Bot 优先 + 闲置账号备用**: 优先使用 Bot 上传，失败自动切换到闲置账号，降低单一账号风险。
    *   **文件混淆**: 自动混淆文件指纹，防止被 Telegram 识别为重复文件或敏感内容。
*   **便捷提取**: 发送提取码即可获取解密后的原始文件。
*   **合集管理**: 支持创建文件夹（合集），批量管理文件。
*   **Web 播放 (实验性)**: 支持通过 Web 界面在线播放视频（需配置 VPS）。

## 架构说明

系统由三个客户端协同工作：

1.  **Bot Client (`vault_bot`)**: 主交互界面，负责接收指令、文件，优先尝试上传。
2.  **User Client (`vault_user`)**: 您的主账号，用于管理和操作。
3.  **Storage Client (`vault_storage`)**: 闲置/小号，作为上传备用通道，保护主账号安全。

## 安装与配置

### 1. 环境准备

*   Python 3.8+
*   Telegram API ID 和 Hash (申请地址: https://my.telegram.org/)
*   Telegram Bot Token (向 @BotFather 申请)
*   两个 Telegram 账号（主账号 + 闲置账号）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

*(如果项目根目录没有 requirements.txt，请安装以下库)*
```bash
pip install pyrogram tgcrypto input_user_agent
```

### 3. 获取存储频道 ID

1.  创建一个新的 Telegram 频道（建议设为私有）。
2.  将 Bot 和 **两个账号** (主账号、闲置账号) 都拉入频道，并给予管理员权限（必须包含“发送消息”权限）。
3.  获取频道 ID (ID 通常以 `-100` 开头)。
    *   可以使用 Bot 的 `/getid` 指令，或者转发频道消息给 Bot 识别。

### 4. 配置文件

修改 `config.py` 或创建 `.env` 文件（推荐），填入以下信息：

```python
# config.py

API_ID = 12345678
API_HASH = "your_api_hash"
BOT_TOKEN = "your_bot_token"

STORAGE_CHANNEL_ID = -100xxxxxxxxxx  # 你的存储频道 ID
ADMIN_ID = 1234567890             # 你的主账号 ID (user_id)
```

### 5. 首次运行与登录

运行主程序：

```bash
python bot.py
```

首次运行时，程序会依次要求登录：
1.  **Bot**: 自动通过 Token 登录。
2.  **User Client**: 输入主账号手机号和验证码。
3.  **Storage Client**: 输入闲置账号手机号和验证码。

登录成功后，会在目录下生成 `.session` 文件，后续启动无需再次登录。

## 使用指南

### 基础操作

*   **上传文件**: 直接发送文件（视频、图片、文档）给 Bot。
    *   Bot 会回复“📥 正在处理...”。
    *   自动加密并上传到存储频道。
    *   上传成功后，Bot 会返回一个 **提取码** (Access Key)。
*   **下载/提取**: 发送 **提取码** 给 Bot。
    *   Bot 会查找文件，下载加密副本，自动解密，然后把原始文件发回给你。

### 合集管理

*   **创建合集**: 
    1. 发送文件后，点击回复键盘中的 "➕ 新建合集"。
    2. 输入合集名称。
*   **查看合集**: 发送 `/mycollections`。
*   **添加到合集**: 
    *   发送文件后，点击已有的合集按钮直接添加。
    *   或者回复文件消息，发送 `/addto 合集名称`。

### 常用指令

*   `/start` - 检查运行状态
*   `/mycollections` - 查看我的合集
*   `/newcollection` - 创建新合集
*   `/download` - 批量下载频道消息 (功能迁移中)
*   `/search` - 搜索对话

## 原理与安全

*   **AES-256 加密**: 每个文件上传前都会生成随机密钥进行 AES-256 加密。密钥存储在本地数据库 (`vault.db`) 中，而不随文件上传。这意味着即使有人访问了你的存储频道，下载下来的也只是无法打开的乱码文件。
*   **文件名混淆**: 上传的文件名会被随机化，防止通过文件名进行审查。

## 注意事项

*   请妥善保管 `vault.db` 和 `.session` 文件，它们包含了密钥和登录凭证。
*   建议定期备份 `vault.db`。
*   **Storage Client** 建议使用完全闲置的账号，以防万一 Telegram 进行风控（虽然本项目已做了多重防护）。

## 免责声明

## 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

## 致谢 / 参考

本项目参考或使用了以下开源项目和资源：

*   **[Pyrogram](https://github.com/pyrogram/pyrogram)**: 优雅、现代的 Telegram MTProto API 框架。
*   **Telegram Bot API**: 强大的 Telegram 机器人接口。

如果你觉得这个项目对你有帮助，欢迎点个 Star ⭐️！
