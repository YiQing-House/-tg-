import sqlite3

conn = sqlite3.connect('vault_bot.session')
cursor = conn.cursor()

with open('session_info.txt', 'w') as f:
    # 列出所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    f.write(f"Tables: {tables}\n\n")

    # 查看每个表结构
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [(r[1], r[2]) for r in cursor.fetchall()]
        f.write(f"{table} columns: {columns}\n")
        
        # 查看表内容
        cursor.execute(f"SELECT * FROM {table} LIMIT 5")
        rows = cursor.fetchall()
        f.write(f"{table} data: {rows}\n\n")

conn.close()
print("Done! Check session_info.txt")
