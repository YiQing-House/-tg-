import os
from dotenv import load_dotenv

# 加载 .env 文件 (如果存在)
load_dotenv()

# ======== 安全配置 (请重命名为 config.py) ========
# 敏感信息建议从环境变量读取

# Telegram API Credentials
API_ID = int(os.getenv("TG_API_ID", "你的API_ID"))
API_HASH = os.getenv("TG_API_HASH", "你的API_HASH")

# Bot Token (From @BotFather)
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "你的BOT_TOKEN")

# Storage Configuration
STORAGE_CHANNEL_ID = int(os.getenv("TG_STORAGE_CHANNEL", "-100xxxxxxxxxx"))
BACKUP_CHANNEL_ID = int(os.getenv("TG_BACKUP_CHANNEL", "0"))

# Database Configuration
DB_NAME = os.getenv("DB_NAME", "vault.db")
DB_PASSWORD = os.getenv("DB_PASSWORD", "你的数据库密码")

# Encryption Configuration
# 必须设置，否则无法加密/解密
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# VPS Temporary Storage Path
TEMP_DOWNLOAD_DIR = os.getenv("TEMP_DIR", "./temp")

# ======== 其他配置 (默认即可) ========
STORAGE_MODE = os.getenv("STORAGE_MODE", "telegram_stealth")
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", os.path.join(os.getcwd(), "Storage"))
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "telegram-vault")
S3_PUBLIC_DOMAIN = os.getenv("S3_PUBLIC_DOMAIN", "")

# ======== Web 服务 ========
ENABLE_WEB_SERVER = True
WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
WEB_SERVER_PORT = int(os.getenv("WEB_SERVER_PORT", 8080))
WEB_PUBLIC_HOST = os.getenv("WEB_PUBLIC_HOST", "127.0.0.1:8080")

# 管理员 ID
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))
