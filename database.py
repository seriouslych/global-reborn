import sqlite3

# Function to connect to the database
def connect_db(db_name='global_chat.db'):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS global_chats (
                    server_id INTEGER,
                    server_name TEXT,
                    channel_id INTEGER)''')
    conn.commit()
    return conn, c

# Function to add or update a global chat channel
def add_global_chat(conn, server_id, server_name, channel_id):
    c = conn.cursor()
    
    # Check if the server ID already exists
    c.execute("SELECT server_id FROM global_chats WHERE server_id = ?", (server_id,))
    if c.fetchone():
        # Update the server name and channel ID if the server already exists
        c.execute("UPDATE global_chats SET server_name = ?, channel_id = ? WHERE server_id = ?",
                  (server_name, channel_id, server_id))
    else:
        # Insert new server data if it doesn't exist
        c.execute("INSERT INTO global_chats (server_id, server_name, channel_id) VALUES (?, ?, ?)",
                  (server_id, server_name, channel_id))
    conn.commit()

# Function to remove a global chat channel
def remove_global_chat(conn, channel_id):
    c = conn.cursor()
    c.execute("DELETE FROM global_chats WHERE channel_id = ?", (channel_id,))
    conn.commit()

# Function to load global chat channels
def load_global_chat_channels(conn):
    c = conn.cursor()
    c.execute("SELECT channel_id FROM global_chats")
    return [row[0] for row in c.fetchall()]
