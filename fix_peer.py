import sqlite3
import time

# 从 user session 获取 access_hash
user_conn = sqlite3.connect('vault_user.session')
user_cursor = user_conn.cursor()
user_cursor.execute("SELECT id, access_hash, type FROM peers WHERE id = -1003367631991")
user_peer = user_cursor.fetchone()
user_conn.close()

if user_peer:
    peer_id, access_hash, peer_type = user_peer
    print(f"从 user session 获取到: id={peer_id}, access_hash={access_hash}, type={peer_type}")
    
    # 计算正确的 channel_id
    # Pyrogram ID 格式: -100 + channel_id
    # 例如: -1003367631991 -> channel_id = 3367631991
    raw_channel_id = abs(peer_id) % 1000000000000
    print(f"Raw channel_id: {raw_channel_id}")
    
    # 写入到 bot session (使用正确的数字类型 3 = channel/supergroup)
    bot_conn = sqlite3.connect('vault_bot.session')
    bot_cursor = bot_conn.cursor()
    bot_cursor.execute(
        "INSERT OR REPLACE INTO peers (id, access_hash, type, username, phone_number, last_update_on) VALUES (?, ?, ?, ?, ?, ?)",
        (peer_id, access_hash, 3, None, None, int(time.time()))
    )
    bot_conn.commit()
    bot_conn.close()
    print(f"已写入到 bot session!")
    
    # 验证
    bot_conn = sqlite3.connect('vault_bot.session')
    bot_cursor = bot_conn.cursor()
    bot_cursor.execute("SELECT * FROM peers")
    print(f"Bot peers 表: {bot_cursor.fetchall()}")
    bot_conn.close()
else:
    print("user session 中没有找到该 peer!")
