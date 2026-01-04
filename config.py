import os

# ======== 安全配置 ========
# 敏感信息从环境变量读取，部署时设置环境变量

# Telegram API Credentials
API_ID = int(os.getenv("TG_API_ID", "123456"))
API_HASH = os.getenv("TG_API_HASH", "cx2241....")

# Bot Token (From @BotFather)
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

# Storage Configuration
STORAGE_CHANNEL_ID = int(os.getenv("TG_STORAGE_CHANNEL", "-100xxxxxxxxxx"))

# Database Configuration
DB_NAME = os.getenv("DB_NAME", "vault.db")
DB_PASSWORD = os.getenv("DB_PASSWORD", "change_this_to_a_strong_password")

# Encryption Configuration
# 必须设置，否则无法加密/解密
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# VPS Temporary Storage Path
TEMP_DOWNLOAD_DIR = os.getenv("TEMP_DIR", "/tmp/telegram_vault_tmp")

# ======== 存储配置 ========

# 存储模式选择:
# 1. 'telegram_stealth' (⭐ 推荐): 
#    存回 Telegram 频道，但会自动混淆 Hash 和加密文件名，
#    防止被检测和封禁，无限容量，免费，0 VPS流量。
# 2. 'local' (本地): 存 VPS 硬盘或挂载盘。
# 3. 's3' (对象存储): 存 R2/AWS。

STORAGE_MODE = os.getenv("STORAGE_MODE", "telegram_stealth")

# 1. 本地存储配置
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", os.path.join(os.getcwd(), "Storage"))
if not os.path.exists(LOCAL_STORAGE_PATH):
    os.makedirs(LOCAL_STORAGE_PATH, exist_ok=True)

# 2. S3 对象存储配置 (Cloudflare R2 / AWS S3)
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "") # 例如: https://<account_id>.r2.cloudflarestorage.com
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "telegram-vault")
S3_PUBLIC_DOMAIN = os.getenv("S3_PUBLIC_DOMAIN", "") # (可选) 绑定的自定义域名

# ======== Web 播放服务配置 ========
ENABLE_WEB_SERVER = True
WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
WEB_SERVER_PORT = int(os.getenv("WEB_SERVER_PORT", 8080))
# 你的服务器公网 IP 或域名 (用于生成播放链接)
WEB_PUBLIC_HOST = os.getenv("WEB_PUBLIC_HOST", "127.0.0.1:8080")

# ======== 安全限制 ========

# 管理员 ID
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))

# 黑名单用户 ID（被封禁的用户）
BLACKLIST = set(map(int, os.getenv("BLACKLIST", "").split(","))) if os.getenv("BLACKLIST") else set()

# 频率限制（秒）
RATE_LIMIT_SECONDS = 5  # 每个用户两次操作之间最少间隔

# 下载限制
MAX_DOWNLOAD_COUNT = 50  # 单次批量下载最大数量

# 自动加入频道是否需要管理员审批
AUTO_JOIN_REQUIRE_APPROVAL = True
