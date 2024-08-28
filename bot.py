import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import database

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
- Команду help
- Определение других хостингов кроме Tenor
"""

# загрузка токена с .env файла
load_dotenv()
token = os.getenv('TOKEN')

# получение особых прав (см. https://discord.com/developers/docs/topics/gateway#privileged-intents)
intents = discord.Intents.default()
intents.message_content = True

# инициализация бота
bot = commands.Bot(command_prefix="!", intents=intents)

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

@bot.event
# функция которая инициализируется при загрузке бота 
# здесь происходит загрузка данных с бд и уведомление о инициализации бота
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")

    global global_chat_channels
    global_chat_channels = database.load_global_chat_channels(conn)

@bot.event
# самая главная функция бота
# бот берёт сообщения пользователя и рассылает его по всем серверам
async def on_message(message):
    if message.author.bot: # если автор сообщения бот - не отправлять сообщение
        return
    
    # передача переменных
    global color
    global message_counter

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
            text=f"{message.guild.name}",
            icon_url=message.guild.icon.url if message.guild.icon else None
        )

        if message.content: # если сообщение имеет текст:
            embed.description = message.content
        
        if "https://tenor.com/view/" in message.content: # если сообщение гифка (или иное изображение)
            tenor_url = message.content.strip()
            embed.description = None

            for channel_id in global_chat_channels:
                if channel_id != message.channel.id:
                    channel = bot.get_channel(channel_id)
                    if channel:
                        # тут короче один костыль который похоже не пофиксить
                        await channel.send(tenor_url) # гифка отправляется отдельным сообщением
                        await channel.send(embed=embed) # и при большом потоке сообщений может получится каша, и бот просто отправит гифку и чуть позже ембед
            return

        if message.attachments: # если у сообщения есть вложения (фото, видео, файлы)
            for attachment in message.attachments:
                file = await attachment.to_file()

                for channel_id in global_chat_channels:
                    if channel_id != message.channel.id:
                        channel = bot.get_channel(channel_id)
                        if channel:
                            await channel.send(file=file, embed=embed)
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

@bot.command()
@commands.has_permissions(administrator=True) # ПРАВА АДМИНИСТРАТОРА - ВРЕМЕННО
async def gc(ctx, channel: discord.TextChannel): # Команда - gc - добавляет в бд канал где будут отправляться сообщения (временное название)
    global global_chat_channels
    global_chat_channels.append(channel.id)
    database.add_global_chat(conn, ctx.guild.id, ctx.guild.name, channel.id)
    await ctx.send(f"Канал {channel.mention} добавлен в глобальный чат.")

@bot.command()
@commands.has_permissions(administrator=True) # ПРАВА АДМИНИСТРАТОРА - ВРЕМЕННО
async def gcr(ctx, channel: discord.TextChannel): # Команда - gcr - удаляет из бд канал (временное название)
    global global_chat_channels
    global_chat_channels.remove(channel.id)
    database.remove_global_chat(conn, channel.id)
    await ctx.send(f"Канал {channel.mention} удален из глобального чата.")

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