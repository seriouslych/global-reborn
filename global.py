import os
import database

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timedelta

# global.py
# файл с функционалом глобал-чата

"""
============= GlobalReborn ==============
EN:
GlobalReborn - is a Discord bot that send messages, files and gifs all around different servers that have this bot.
Made by seriouslych (https://github.com/seriouslych)

RU:
GlobalReborn - это Discord бот который отправляет сообщения, файлы и гиф на разные серверы, у которых есть этот бот.
Сделано seriouslych (https://github.com/seriouslych)
======================================
"""

"""
TODO:
- Систему администрирования (мьюты и баны)
- Систему логирования
"""

# загрузка токена с .env файла
load_dotenv()
token = os.getenv('TOKEN')

# получение особых прав (см. https://discord.com/developers/docs/topics/gateway#privileged-intents)
intents = discord.Intents.default()
intents.message_content = True

# инициализация бота
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# мой айди в дискорд (для использовании команды без каких либо прав на сервере)
creator_id = [670627088729899008]

# массив где хранятся все ссылки хостингов гифок и изображений
gif_hostings = ["https://tenor.com/view", "https://media1.tenor.com/m/", "https://media.discordapp.net/attachments/", "https://i.imgur.com/", "https://images-ext-1.discordapp.net/external/", "https://imgur.com/", "https://cdn.discordapp.com/attachments/"]

# массив где загружается весь список серверов в память
global_chat_channels = []

# словарь где сохраняется последние 100 пересланных сообщений (для реализации функции измменения и удаления сообщения)
messages = {}
message_counter = 0 # счетчик сообщений


# переменная которая служит переключателем цвета (чтобы были цвета с флага Беларуси)
# 🔴
# 🟢
color = True

# подключение к базе данных
conn, c = database.connect_db()

# загрузка списков забаненных серверов и замьюченных пользователей
banned_servers = database.get_banned_servers(conn)
# словарь где хранится время мьюта пользователя
# пример: {user_id: unmute_time}
muted_users = database.get_muted_users(conn)

def user_check():
    def predicate(interaction):
        return interaction.user.id in creator_id or interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

def mod_user_check():
    def predicate(interaction):
        return interaction.user.id in creator_id
    return app_commands.check(predicate)

# получение списка серверов из базы данных
def load_registered_guilds():
    return database.get_all_registered_guilds(conn)

@tasks.loop(minutes=5)  # моментальная сихнронизация со всеми серверами каждые 5 минут
async def sync_commands_periodically():
    print("Начата периодическая синхронизация команд...")
    registered_guilds = load_registered_guilds()  # загружаем зарегистрированные серверы из базы данных
    
    # снхронизация команд для каждого сервера в базе данных
    for guild_id in registered_guilds:
        guild = discord.Object(id=guild_id)
        try:
            await bot.tree.sync(guild=guild)
            print(f"Команды синхронизированы для сервера {guild_id}")
        except Exception as e:
            print(f"Ошибка синхронизации для сервера {guild_id}: {e}")

    # глобальная синхронизация для всех серверов (на всякий случай)
    try:
        await bot.tree.sync()
        print("Глобальная синхронизация завершена")
    except Exception as e:
        print(f"Ошибка глобальной синхронизации: {e}")

@tasks.loop(minutes=1)
async def check_mutes():
    now = datetime.now()
    to_unmute = [user_id for user_id, unmute_time in muted_users.items() if unmute_time <= now]

    for user_id in to_unmute:
        muted_users.pop(user_id)
        database.unmute_user(conn, user_id) # размьют в бд если требуется

@bot.event
# функция которая инициализируется при загрузке бота 
# здесь происходит загрузка данных с бд, синхронизация команд с серверами и уведомление о инициализации бота
async def on_ready():
    global global_chat_channels

    print(f"Бот запущен как {bot.user.name} ({bot.user.id})")
    
    # запускаем периодическую задачу синхронизации
    sync_commands_periodically.start()
    # запускаем периодическую задачу проверки мьютов 
    check_mutes.start()

    global_chat_channels = database.load_global_chat_channels(conn)

@bot.event
async def on_guild_join(guild):
    # когда бот добавляется на новый сервер, он добавляем сервер в базу данных
    database.add_guild(conn, guild.id, guild.name)
    print(f"Сервер {guild.name} ({guild.id}) добавлен в базу данных.")
    
    # моментальная синхронизация команд для нового сервера
    await bot.tree.sync(guild=discord.Object(id=guild.id))
    print(f"Синхронизированы команды для сервера {guild.id}")

@bot.event
# самая главная функция бота
# бот берёт сообщения пользователя и рассылает его по всем серверам
async def on_message(message):
    if message.author.bot: # если автор сообщения бот - не отправлять сообщение
        return
    
    # проверка если сервер забанен
    if str(message.guild.id) in banned_servers:
        return
    
    # проверка если пользователь замьючен
    if str(message.author.id) in muted_users and muted_users[str(message.author.id)] > datetime.now():
        return

    # передача переменных
    global color
    global message_counter
    global gif_hostings

    if message.channel.id in global_chat_channels: # если канал в списке зарег. каналов:
        embed_color = discord.Color.from_str('#ce1720') if color else discord.Color.from_str('#007c30') # та самая смена цветов :)
        color = not color
        
        embed = discord.Embed(color=embed_color)
        # автор сообщения и его ID в скобках
        embed.set_author(
            name=f"{message.author.name} ({message.author.id})",
            icon_url=message.author.avatar.url
        )
        # сервер откуда это сообщение было отправлено
        embed.set_footer(
            text=f"{message.guild.name} ({message.guild.id})",
            icon_url=message.guild.icon.url if message.guild.icon else None
        )

        if message.content: # если сообщение имеет текст:
            embed.description = message.content
        
        if any(hosting in message.content for hosting in gif_hostings): # если сообщение гифка (или иное изображение)
            gif_url = message.content.strip()
            embed.description = None

            for channel_id in global_chat_channels:
                if channel_id != message.channel.id:
                    channel = bot.get_channel(channel_id)
                    if channel:
                        # тут короче один костыль который похоже не пофиксить
                        await channel.send(gif_url) # гифка отправляется отдельным сообщением
                        await channel.send(embed=embed) # и при большом потоке сообщений может получится каша, и бот просто отправит гифку и чуть позже ембед
            return

        if message.attachments: # если у сообщения есть вложения (фото, видео, файлы)
            for attachment in message.attachments:
                file = await attachment.to_file()

                for channel_id in global_chat_channels:
                    if channel_id != message.channel.id:
                        channel = bot.get_channel(channel_id)
                        if channel:
                            await channel.send(file=file)
                            await channel.send(embed=embed)
                return

        messages[message.id] = []
        for channel_id in global_chat_channels:
            if channel_id != message.channel.id:
                channel = bot.get_channel(channel_id)
                if channel:
                    sent_message = await channel.send(embed=embed)
                    # добавление сообщения в словарь
                    messages[message.id].append((channel_id, sent_message.id))
            
        message_counter += 1
        await clear_messages()

    await bot.process_commands(message)

async def clear_messages(): # очистка происходит каждые 100 сообщений, дабы не переполнять оперативную память
    global message_counter
    if message_counter >= 100:
        messages.clear()
        message_counter = 0

@bot.event
async def on_message_edit(before, after): # тут происходит изменение сообщения, если пользователь изменил сообщение на сервере
    if before.author.bot or before.content == after.content:
        return

    if before.id in messages:
        for channel_id, message_id in messages[before.id]:
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                    msg = await channel.fetch_message(message_id)
                    embed = msg.embeds[0]
                    embed.description = after.content
                    await msg.edit(embed=embed)
                except discord.NotFound:
                    pass

@bot.event
async def on_message_delete(message): # тут происходит удаление сообщения, если пользователь удалил сообщение на сервере
    if message.author.bot:
        return

    if message.id in messages:
        for channel_id, message_id in messages[message.id]:
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                    msg = await channel.fetch_message(message_id)
                    await msg.delete()
                except discord.NotFound:
                    pass 

# команда помощи/хелпа
@bot.tree.command(name='хелп', description='Показывает список команд и информацию о боте')
async def help_command(interaction: discord.Interaction):
    commands_list = """/глобал_канал `#канал` - Добавление канала для глобал чата
    /удалить_глобал_канал `#канал` - Удаление канала для глобал чата (не удаляет сам канал)
    """

    embed = discord.Embed(color=discord.Color.blue())
    
    embed.set_author(
        name=f"{bot.user.name} - Помощь",
        icon_url=bot.user.avatar.url if bot.user.avatar else None
    )

    embed.add_field(name="⚒️ Список команд:", 
                    value=commands_list,
                    inline=False)

    embed.add_field(
        name="*Примечание - эти команды доступны только администраторам сервера.",
        value="",
        inline=False
    )
    
    embed.add_field(
        name=f"🤖 О {bot.user.name}:",
        value=f"{bot.user.name} - это Discord бот, который отправляет сообщения, файлы и гифки на разные серверы, у которых есть этот бот.\n\nСделано seriouslych (https://github.com/seriouslych) - @seriously1488",
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# команда для добавления канала в глобальный чат
@bot.tree.command(name='глобал_канал', description='Добавление канала для глобал чата')
@user_check()
async def gc_command(interaction: discord.Interaction, channel: discord.TextChannel):
    global global_chat_channels
    global_chat_channels.append(channel.id)
    database.add_global_chat(conn, interaction.guild.id, interaction.guild.name, channel.id)
    await interaction.response.send_message(f"Канал {channel.mention} добавлен в глобальный чат.", ephemeral=True)

# команда для удаления канала из глобального чата
@bot.tree.command(name='удалить_глобал_канал', description='Удаление канала из глобал чата')
@user_check()
async def gcr_command(interaction: discord.Interaction, channel: discord.TextChannel):
    global global_chat_channels
    if channel.id in global_chat_channels:
        global_chat_channels.remove(channel.id)
        database.remove_global_chat(conn, channel.id)
        await interaction.response.send_message(f"Канал {channel.mention} удален из глобального чата.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Канал {channel.mention} не найден в глобальном чате.", ephemeral=True)

@bot.tree.command(name='бан_сервера', description='Банит сервер с ботом.')
@mod_user_check()
async def ban_server(interaction: discord.Interaction, server_id: str):
    if server_id in banned_servers:
        await interaction.response.send_message(f"Сервер {server_id} уже забанен.", ephemeral=True)
        return

    banned_servers.append(server_id)
    database.ban_server(conn, server_id)
    await interaction.response.send_message(f"Сервер {server_id} забанен", ephemeral=False)

@bot.tree.command(name='разбан_сервера', description='Разбанивает сервер с ботом.')
@mod_user_check()
async def unban_server(interaction: discord.Interaction, server_id: str):
    if server_id not in banned_servers:
        await interaction.response.send_message(f"Сервер {server_id} не был забанен.", ephemeral=True)
        return

    banned_servers.remove(server_id)
    database.unban_server(conn, server_id)
    await interaction.response.send_message(f"Сервер {server_id} разбанен.", ephemeral=False)

@bot.tree.command(name='мьют', description='Мьютит пользователя на определённое время.')
@mod_user_check()
async def mute_user(interaction: discord.Interaction, user_id: str, duration: int):
    if user_id in muted_users:
        await interaction.response.send_message(f"Пользователь {user_id} уже замьючен.", ephemeral=True)
        return

    unmute_time = datetime.now() + timedelta(minutes=duration)
    muted_users[user_id] = unmute_time
    database.mute_user(conn, user_id)
    await interaction.response.send_message(f"Пользователь {user_id} замьючен на {duration} минут.", ephemeral=False)

@bot.tree.command(name='размьют', description='Размьютит пользователя.')
@mod_user_check()
async def unmute_user(interaction: discord.Interaction, user_id: str):
    if user_id in muted_users:
        muted_users.pop(user_id)  # удаляем пользователя из словаря
        database.unmute_user(conn, user_id)  # удаляем из базы данных
        print(f"Пользователь {user_id} размьючен.")
    else:
        print(f"Пользователь {user_id} не найден в списке замьюченных.")

    database.unmute_user(conn, user_id)
    await interaction.response.send_message(f"Пользователь {user_id} размьючен.", ephemeral=False)

bot.run(token) # запуск бота при помощи токена
 
"""
ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐
ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 
ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐
ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 
ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐
ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 
ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐
ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 ТЫ ГЛОБАЛ ЧАТ? 🧐 
"""