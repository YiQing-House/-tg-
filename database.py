import sqlite3
import base64
import os
from cryptography.fernet import Fernet
from config import DB_NAME, DB_PASSWORD, ENCRYPTION_KEY

# Ensure encryption key is valid (must be 32 url-safe base64-encoded bytes)
# If the user provided a simple string, we hash it to make it valid
import hashlib
def get_fernet_key(key_string):
    digest = hashlib.sha256(key_string.encode()).digest()
    return base64.urlsafe_b64encode(digest)

cipher = Fernet(get_fernet_key(ENCRYPTION_KEY))

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()
    
    def encrypt_text(self, text):
        """使用 Fernet 加密文本"""
        if text is None:
            return None
        return cipher.encrypt(text.encode()).decode()
    
    def decrypt_text(self, encrypted_text):
        """使用 Fernet 解密文本"""
        if encrypted_text is None:
            return None
        try:
            return cipher.decrypt(encrypted_text.encode()).decode()
        except:
            return encrypted_text  # 如果解密失败，返回原文 (可能是旧数据)

    def init_db(self):
        # Create table for files
        # We encrypt 'file_name' and 'caption' to prevent keyword scanning
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER DEFAULT 0,
                chat_id INTEGER DEFAULT 0,
                file_id TEXT,
                local_path TEXT,
                storage_mode TEXT DEFAULT 'local',  -- 'local' 或 's3' 或 'telegram_stealth'
                file_unique_id TEXT NOT NULL,
                file_name_enc TEXT,
                caption_enc TEXT,
                file_size INTEGER,
                mime_type TEXT,
                access_key TEXT UNIQUE,
                is_encrypted BOOLEAN DEFAULT 0,  -- 是否已全量 AES 加密
                encryption_key TEXT,  -- AES 解密密钥 (Base64/Hex)
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                status TEXT DEFAULT 'active', -- active, banned
                ban_until TIMESTAMP,
                first_name TEXT,
                status TEXT DEFAULT 'active', -- active, banned
                accepted_terms BOOLEAN DEFAULT 0,
                ban_until TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
        
        # Schema Migration: Add missing columns to existing database
        migrations = [
            ("access_key", "TEXT UNIQUE"),
            ("is_encrypted", "BOOLEAN DEFAULT 0"),
            ("encryption_key", "TEXT"),
            ("storage_mode", "TEXT DEFAULT 'local'"),
            ("local_path", "TEXT"),
            ("backup_message_id", "INTEGER DEFAULT 0"),
            ("backup_chat_id", "INTEGER DEFAULT 0"),
        ]
        
        for col_name, col_type in migrations:
            try:
                self.cursor.execute(f"ALTER TABLE files ADD COLUMN {col_name} {col_type}")
                self.conn.commit()
            except:
                pass  # Column already exists
        
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN accepted_terms BOOLEAN DEFAULT 0")
            self.conn.commit()
        except: pass

        # Migration: Ban Reason
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN ban_reason TEXT")
            self.conn.commit()
        except: pass

    def encrypt_text(self, text):
        if text is None:
            return None
        return cipher.encrypt(text.encode()).decode()

    def decrypt_text(self, encrypted_text):
        if encrypted_text is None:
            return None
        try:
            return cipher.decrypt(encrypted_text.encode()).decode()
        except:
            return "[Decryption Failed]"

    def add_file(self, message_id, chat_id, file_id, file_unique_id, file_name, caption, file_size, mime_type, local_path=None, storage_mode='local', access_key=None, is_encrypted=False, encryption_key=None, backup_message_id=0, backup_chat_id=0):
        self.cursor.execute('''
            INSERT INTO files (message_id, chat_id, file_id, local_path, storage_mode, file_unique_id, file_name_enc, caption_enc, file_size, mime_type, access_key, is_encrypted, encryption_key, backup_message_id, backup_chat_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (message_id, chat_id, file_id, local_path, storage_mode, file_unique_id, 
              self.encrypt_text(file_name), 
              self.encrypt_text(caption), 
              file_size, mime_type, access_key, is_encrypted, encryption_key, backup_message_id, backup_chat_id))
        self.conn.commit()
    
    def get_file_by_key(self, key):
        """通过提取码获取文件"""
        self.cursor.execute("SELECT * FROM files WHERE access_key = ?", (key,))
        row = self.cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "message_id": row[1],
                "chat_id": row[2],
                "file_id": row[3],
                "local_path": row[4],
                "storage_mode": row[5],
                "file_unique_id": row[6],
                "file_name": self.decrypt_text(row[7]),
                "caption": self.decrypt_text(row[8]),
                "file_size": row[9],
                "mime_type": row[10],
                "access_key": row[11],
                "is_encrypted": row[12],
                "encryption_key": row[13]
            }
        return None

    def search_files(self, keyword):
        # Since fields are encrypted, we can't use SQL LIKE %keyword%.
        # We must fetch all and decrypt in memory (OK for personal usage < 100k files)
        # For larger datasets, we would need a blind index, but for MVP this is securest.
        self.cursor.execute('SELECT * FROM files')
        all_files = self.cursor.fetchall()
        
        results = []
        keyword = keyword.lower()
        for row in all_files:
            # row: id, msg_id, chat_id, file_id, unique_id, name_enc, cap_enc, size, mime, date
            name = self.decrypt_text(row[5]) or ""
            caption = self.decrypt_text(row[6]) or ""
            
            if keyword in name.lower() or keyword in caption.lower():
                results.append({
                    "id": row[0],
                    "message_id": row[1],
                    "chat_id": row[2],
                    "file_name": name,
                    "caption": caption,
                    "file_size": row[9] # Adjusted index for file_size
                })
        return results

    def get_all_files(self):
        self.cursor.execute('SELECT * FROM files ORDER BY upload_date DESC LIMIT 50')
        rows = self.cursor.fetchall()
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "file_name": self.decrypt_text(row[7]), # Adjusted index for file_name_enc
                "file_size": row[9] # Adjusted index for file_size
            })
        return results

    # ========== 合集功能 ==========
    
    def init_collections_table(self):
        """创建合集相关表"""
        # This method is now redundant as init_db handles collection table creation
        # Keeping it for backward compatibility if called directly, but it will do nothing
        # if tables already exist.
        pass
    
    def create_collection(self, name, access_key, owner_id):
        """创建新合集"""
        try:
            self.cursor.execute('''
                INSERT INTO collections (name, access_key, owner_id)
                VALUES (?, ?, ?)
            ''', (name, access_key, owner_id))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None  # 密钥已存在
    
    def get_collection_by_key(self, access_key):
        """通过密钥获取合集"""
        self.cursor.execute('SELECT * FROM collections WHERE access_key = ?', (access_key,))
        row = self.cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "access_key": row[2],
                "owner_id": row[3],
                "created_at": row[4]
            }
        return None
    
    def get_user_collections(self, owner_id):
        """获取用户的所有合集"""
        self.cursor.execute('SELECT * FROM collections WHERE owner_id = ?', (owner_id,))
        rows = self.cursor.fetchall()
        results = []
        for row in rows:
            # 获取合集文件数量
            self.cursor.execute('SELECT COUNT(*) FROM collection_files WHERE collection_id = ?', (row[0],))
            count = self.cursor.fetchone()[0]
            results.append({
                "id": row[0],
                "name": row[1],
                "access_key": row[2],
                "file_count": count,
                "created_at": row[4]
            })
        return results
    
    def add_file_to_collection(self, collection_id, file_id):
        """添加文件到合集"""
        try:
            self.cursor.execute('''
                INSERT INTO collection_files (collection_id, file_id)
                VALUES (?, ?)
            ''', (collection_id, file_id))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_collection_files(self, collection_id):
        """获取合集中的所有文件"""
        self.cursor.execute('''
            SELECT f.* FROM files f
            JOIN collection_files cf ON f.id = cf.file_id
            WHERE cf.collection_id = ?
            ORDER BY cf.added_at
        ''', (collection_id,))
        rows = self.cursor.fetchall()
        results = []
        for row in rows:
            # 0: id, 1: message_id, 2: chat_id, 3: file_id, 4: local_path, 5: storage_mode
            # 6: file_unique_id, 7: file_name_enc, 8: caption_enc, 9: file_size, 10: mime_type
            # 11: access_key, 12: is_encrypted, 13: encryption_key
            results.append({
                "id": row[0],
                "message_id": row[1],
                "chat_id": row[2],
                "file_id": row[3],
                "file_name": self.decrypt_text(row[7]),
                "caption": self.decrypt_text(row[8]),
                "file_size": row[9],
                "mime_type": row[10],
                "is_encrypted": row[12],
                "encryption_key": row[13],
                "backup_message_id": row[14] if len(row) > 14 else 0,
                "backup_chat_id": row[15] if len(row) > 15 else 0
            })
        return results
    
    def get_file_by_id(self, file_id):
        """通过 ID 获取文件"""
        self.cursor.execute('SELECT * FROM files WHERE id = ?', (file_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "message_id": row[1],
                "chat_id": row[2],
                "file_id": row[3],
                "file_name": self.decrypt_text(row[5]),
                "file_size": row[7]
            }
        return None
    
    def get_last_file_id(self):
        """获取最新添加的文件 ID"""
        self.cursor.execute('SELECT id FROM files ORDER BY id DESC LIMIT 1')
        row = self.cursor.fetchone()
        return row[0] if row else None
    
    def get_collection_by_name(self, name, owner_id):
        """通过名称获取用户的合集"""
        self.cursor.execute('SELECT * FROM collections WHERE name = ? AND owner_id = ?', (name, owner_id))
        row = self.cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "access_key": row[2],
                "owner_id": row[3]
            }
        return None

    def update_user(self, user_id, username, first_name):
        """更新用户信息"""
        try:
            self.cursor.execute('''
                INSERT INTO users (id, username, first_name, last_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_active = CURRENT_TIMESTAMP
            ''', (user_id, username, first_name))
            self.conn.commit()
        except: pass

    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "first_name": row[2],
                "status": row[3],
                "ban_until": row[4],
                "accepted_terms": row[5] if len(row) > 5 else 0,
                "ban_reason": row[6] if len(row) > 6 else None
            }
        return None

    def accept_terms(self, user_id):
        self.cursor.execute('UPDATE users SET accepted_terms = 1 WHERE id = ?', (user_id,))
        self.conn.commit()

    def get_all_users(self):
        self.cursor.execute('SELECT * FROM users ORDER BY last_active DESC')
        rows = self.cursor.fetchall()
        return [{"id": r[0], "username": r[1], "first_name": r[2], "status": r[3], "ban_until": r[4]} for r in rows]
    
    def set_user_ban(self, user_id, status, ban_until=None, reason=None):
        """设置用户封禁状态"""
        self.cursor.execute(
            'UPDATE users SET status = ?, ban_until = ?, ban_reason = ? WHERE id = ?',
            (status, ban_until, reason, user_id)
        )
        self.conn.commit()

    def update_user_terms(self, user_id, accepted=True):
        """更新用户条款接受状态"""
        val = 1 if accepted else 0
        self.cursor.execute('UPDATE users SET accepted_terms = ? WHERE id = ?', (val, user_id))
        self.conn.commit()


db = Database()
# 初始化合集表
db.init_collections_table()

