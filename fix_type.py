import sqlite3
conn = sqlite3.connect('vault_bot.session')
c = conn.cursor()
c.execute("UPDATE peers SET type='supergroup' WHERE id=-1003367631991")
conn.commit()
c.execute('SELECT * FROM peers')
print('Updated:', c.fetchall())
conn.close()
