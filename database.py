import sqlite3

# подключение к бд
def connect_db(db_name='global_chat.db'):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    
    # создание таблиц если не существуют
    c.execute('''CREATE TABLE IF NOT EXISTS global_chats (
                    server_id INTEGER,
                    server_name TEXT,
                    channel_id INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS banned_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS banned_servers (
                    server_id INTEGER PRIMARY KEY)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS muted_users (
                    user_id INTEGER PRIMARY KEY,
                    mute_end_time TIMESTAMP)''')
    
    conn.commit()
    return conn, c

# добавление глобального чата
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

# добавление сервера в базу данных
def add_guild(conn, server_id, server_name):
    c = conn.cursor()
    
    # проверяем, существует ли уже сервер в базе данных
    c.execute("SELECT server_id FROM global_chats WHERE server_id = ?", (server_id,))
    if not c.fetchone():
        # если сервер не существует, добавляем его
        c.execute("INSERT INTO global_chats (server_id, server_name, channel_id) VALUES (?, ?, ?)",
                  (server_id, server_name, None))  # Канал по умолчанию None
        conn.commit()
        print(f"Сервер {server_name} (ID: {server_id}) добавлен в базу данных.")
    else:
        print(f"Сервер {server_name} (ID: {server_id}) уже существует в базе данных.")

# удаление глобального чата
def remove_global_chat(conn, channel_id):
    c = conn.cursor()
    c.execute("DELETE FROM global_chats WHERE channel_id = ?", (channel_id,))
    conn.commit()

# получение всех каналов
def load_global_chat_channels(conn):
    c = conn.cursor()
    c.execute("SELECT channel_id FROM global_chats")
    return [row[0] for row in c.fetchall()]

# получение всех серверов
def get_all_registered_guilds(conn):
    c = conn.cursor()
    c.execute("SELECT DISTINCT server_id FROM global_chats")
    return [row[0] for row in c.fetchall()]

# получение забанненых серверов
def get_banned_servers(conn):
    c = conn.cursor()
    c.execute("SELECT * FROM banned_servers")
    return c.fetchall()

# получение замьюченных пользователей
def get_muted_users(conn):
    c = conn.cursor()
    c.execute("SELECT user_id, mute_end_time FROM muted_users")
    return {row[0]: row[1] for row in c.fetchall()}

# добавление замьюченного пользователя
def mute_user(conn, user_id):
    c = conn.cursor()
    c.execute("INSERT INTO muted_users (user_id) VALUES (?)", (user_id,))
    conn.commit()

# добавление забаненного сервера
def ban_server(conn, server_id):
    c = conn.cursor()
    
    # проверяем, есть ли сервер уже в списке забаненных
    c.execute("SELECT server_id FROM banned_servers WHERE server_id = ?", (server_id,))
    if c.fetchone():
        print(f"Сервер {server_id} уже забанен.")
    else:
        c.execute("INSERT INTO banned_servers (server_id) VALUES (?)", (server_id,))
        conn.commit()
        print(f"Сервер {server_id} добавлен в список забаненных.")

# удаление забаненного сервера
def unban_server(conn, server_id):
    c = conn.cursor()
    c.execute("DELETE FROM banned_servers WHERE server_id = ?", (server_id,))
    conn.commit()

# удаление замьюченного пользователя
def unmute_user(conn, user_id):
    c = conn.cursor()
    c.execute("DELETE FROM muted_users WHERE user_id = ?", (user_id,))
    conn.commit()

# проверка, забанен ли сервер
def is_banned_server(conn, server_id):
    c = conn.cursor()
    c.execute("SELECT server_id FROM banned_servers WHERE server_id = ?", (server_id,))
    return c.fetchone() is not None

# проверка, замьючен ли пользователь
def is_muted_user(conn, user_id):
    c = conn.cursor()
    c.execute("SELECT mute_end_time FROM muted_users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    return result[0] if result else None
