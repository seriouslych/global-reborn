import sqlite3

def connect_db(db_name='global_chat.db'):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS global_chats (
                    server_id INTEGER,
                    server_name TEXT,
                    channel_id INTEGER)''')
    conn.commit()
    return conn, c

def add_global_chat(conn, server_id, server_name, channel_id):
    c = conn.cursor()
    
    c.execute("SELECT server_id FROM global_chats WHERE server_id = ?", (server_id,))
    if c.fetchone():
        c.execute("UPDATE global_chats SET server_name = ?, channel_id = ? WHERE server_id = ?",
                  (server_name, channel_id, server_id))
    else:
        c.execute("INSERT INTO global_chats (server_id, server_name, channel_id) VALUES (?, ?, ?)",
                  (server_id, server_name, channel_id))
    conn.commit()

def remove_global_chat(conn, channel_id):
    c = conn.cursor()
    c.execute("DELETE FROM global_chats WHERE channel_id = ?", (channel_id,))
    conn.commit()

def load_global_chat_channels(conn):
    c = conn.cursor()
    c.execute("SELECT channel_id FROM global_chats")
    return [row[0] for row in c.fetchall()]
