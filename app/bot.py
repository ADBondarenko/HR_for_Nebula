import os
import json
from telethon import TelegramClient, events
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from nltk.stem import SnowballStemmer
from dotenv import load_dotenv
import asyncio

# # Load environment variables from .env file
# load_dotenv('.env.test')

# Define your API credentials (get from my.telegram.org)
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
phone_number = os.getenv("PHONE_NUMBER")

config_file_path = './data/forward_chats.json'

TARGET_GROUP_IDS = os.getenv("TARGET_GROUP_IDS", "").split(",")

client = TelegramClient('session_name', api_id, api_hash)
bot = Bot(token=telegram_token)
dp = Dispatcher(bot)

stemmer_english = SnowballStemmer("english")
stemmer_russian = SnowballStemmer("russian")

whitelisted_ids = os.getenv("WHITELISTED_IDS", "")
WHITELISTED_IDS = [int(user_id) for user_id in whitelisted_ids.split(",") if user_id.isdigit()]

def load_config():
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as f:
            try:
                data = json.load(f)
                return data.get('chats', []), data.get('keywords', [])
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {config_file_path}")
                return [], []
    else:
        print(f"Config file {config_file_path} not found.")
        return [], []

def save_config(chats, keywords):
    try:
        with open(config_file_path, 'w') as f:
            json.dump({"chats": chats, "keywords": keywords}, f, indent=4)
    except Exception as e:
        print(f"Error writing to JSON file {config_file_path}: {e}")

forward_chats, keywords = load_config()

def is_whitelisted(user_id):
    return user_id in WHITELISTED_IDS

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    if not is_whitelisted(message.from_user.id):
        await message.reply("Access denied. You are not authorized to use this bot.")
        return

    welcome_message = (
        "Welcome to the Telegram Management Bot! Here are the available commands:\n\n"
        "/add_chat - Add a new chat (ID, username, or https://t.me/ link) to the monitoring list\n"
        "/remove_chat - Remove a chat from the monitoring list\n"
        "/list_chats - List all monitored chats\n"
        "/add_keyword - Add a keyword to monitor with optional stemming\n"
        "/remove_keyword - Remove a keyword from the list\n"
        "/list_keywords - List all monitored keywords\n"
        "/get_chat_id - Get the chat ID of the current group\n"
        "/get_chat_id_from_group - Resolve a chat ID from a https://t.me/ link\n"
    )

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Add Chat", callback_data='add_chat'),
        InlineKeyboardButton("Remove Chat", callback_data='remove_chat'),
        InlineKeyboardButton("List Chats", callback_data='list_chats'),
        InlineKeyboardButton("Add Keyword", callback_data='add_keyword'),
        InlineKeyboardButton("Remove Keyword", callback_data='remove_keyword'),
        InlineKeyboardButton("List Keywords", callback_data='list_keywords'),
        InlineKeyboardButton("Get Chat ID", callback_data='get_chat_id'),
        InlineKeyboardButton("Resolve Chat ID from Link", callback_data='get_chat_id_from_group')
    )

    await message.reply(welcome_message, reply_markup=markup)

async def get_chat_id_from_group(input_text):
    try:
        if input_text.startswith('https://t.me/'):
            input_text = input_text.split('/')[-1]

        if input_text.isdigit():
            return int(input_text)

        entity = await client.get_entity(input_text)
        return entity.id
    except (UsernameNotOccupiedError, UsernameInvalidError):
        return None
    except Exception as e:
        print(f"Error resolving entity: {e}")
        return None

@dp.callback_query_handler(lambda c: c.data)
async def process_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if not is_whitelisted(user_id):
        await bot.send_message(user_id, "Access denied. You are not authorized to use this bot.")
        return

    chat_id = callback_query.from_user.id

    if callback_query.data == 'add_chat':
        await bot.send_message(chat_id, "Please send the chat ID, username, or https://t.me/ link to add:")
        dp.register_message_handler(process_add_chat, state=None)
    elif callback_query.data == 'remove_chat':
        await bot.send_message(chat_id, "Please send the chat ID, @username, or https://t.me/ link to remove:")
        dp.register_message_handler(process_remove_chat, state=None)
    elif callback_query.data == 'list_chats':
        if forward_chats:
            chat_list = "\n".join(forward_chats)
            await bot.send_message(chat_id, f"The following chats are being monitored:\n{chat_list}")
        else:
            await bot.send_message(chat_id, "No chats are currently being monitored.")
    elif callback_query.data == 'add_keyword':
        await bot.send_message(chat_id, "Please send the keyword to add:")
        dp.register_message_handler(add_keyword_step, state=None)
    elif callback_query.data == 'remove_keyword':
        await bot.send_message(chat_id, "Please send the keyword to remove:")
        dp.register_message_handler(remove_keyword_step, state=None)
    elif callback_query.data == 'list_keywords':
        if keywords:
            keyword_list = "\n".join(keywords)
            await bot.send_message(chat_id, f"The following keywords are being monitored:\n{keyword_list}")
        else:
            await bot.send_message(chat_id, "No keywords are currently being monitored.")
    elif callback_query.data == 'get_chat_id':
        await bot.send_message(chat_id, f"The current chat ID is: {chat_id}")
    elif callback_query.data == 'get_chat_id_from_group':
        await bot.send_message(chat_id, "Please send the https://t.me/ link or @username to resolve:")
        dp.register_message_handler(resolve_chat_id_step, state=None)
    elif callback_query.data == 'back_to_menu':
        await send_welcome(callback_query.message)

async def process_add_chat(message: types.Message):
    input_text = message.text
    chat_id = await get_chat_id_from_group(input_text)

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Back to Main Menu", callback_data='back_to_menu'))

    if chat_id:
        if str(chat_id) not in forward_chats:
            forward_chats.append(str(chat_id))
            save_config(forward_chats, keywords)
            await message.reply(f"Chat with ID {chat_id} has been added successfully.", reply_markup=markup)
        else:
            await message.reply(f"Chat {chat_id} is already in the subscription list.", reply_markup=markup)
    else:
        await message.reply("No valid chat ID, handle, or link was provided. Please try again.", reply_markup=markup)

    dp.unregister_message_handler(process_add_chat)

async def process_remove_chat(message: types.Message):
    input_text = message.text
    chat_id = await get_chat_id_from_group(input_text)

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Back to Main Menu", callback_data='back_to_menu'))

    if chat_id:
        if str(chat_id) in forward_chats:
            forward_chats.remove(str(chat_id))
            save_config(forward_chats, keywords)
            await message.reply(f"Chat with ID {chat_id} has been removed successfully.", reply_markup=markup)
        else:
            await message.reply(f"Chat {chat_id} is not in the subscription list.", reply_markup=markup)
    else:
        await message.reply("No valid chat ID, handle, or link was provided. Please try again.", reply_markup=markup)

    dp.unregister_message_handler(process_remove_chat)

async def add_keyword_step(message: types.Message):
    keyword_to_add = message.text.lower()

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("Yes", callback_data=f'stemming_yes_{keyword_to_add}'),
               InlineKeyboardButton("No", callback_data=f'stemming_no_{keyword_to_add}'))

    await message.reply(f"Do you want to apply stemming for the keyword '{keyword_to_add}'?", reply_markup=markup)

    dp.unregister_message_handler(add_keyword_step)

@dp.callback_query_handler(lambda c: c.data.startswith('stemming_'))
async def process_stemming_choice(callback_query: types.CallbackQuery):
    data_parts = callback_query.data.split('_')
    choice = data_parts[1]
    keyword_to_add = '_'.join(data_parts[2:])
    chat_id = callback_query.from_user.id

    if choice == 'yes':
        if all('а' <= c <= 'я' or c == 'ё' for c in keyword_to_add.lower()):
            stemmed_keyword = stemmer_russian.stem(keyword_to_add)
            language = 'Russian'
        else:
            stemmed_keyword = stemmer_english.stem(keyword_to_add)
            language = 'English'

        if keyword_to_add not in keywords:
            keywords.append(keyword_to_add)
        if stemmed_keyword not in keywords:
            keywords.append(stemmed_keyword)

        save_config(forward_chats, keywords)
        await bot.send_message(chat_id, f"Keyword '{keyword_to_add}' and its stemmed version '{stemmed_keyword}' "
                                        f"({language}) have been added to the list.")
    else:
        if keyword_to_add not in keywords:
            keywords.append(keyword_to_add)
            save_config(forward_chats, keywords)
            await bot.send_message(chat_id, f"Keyword '{keyword_to_add}' has been added to the list without stemming.")

async def remove_keyword_step(message: types.Message):
    keyword_to_remove = message.text.lower()

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Back to Main Menu", callback_data='back_to_menu'))

    removed = False

    if keyword_to_remove in keywords:
        keywords.remove(keyword_to_remove)
        removed = True
        await message.reply(f"Keyword '{keyword_to_remove}' has been removed from the list.", reply_markup=markup)

    stemmed_keyword_eng = stemmer_english.stem(keyword_to_remove)
    stemmed_keyword_rus = stemmer_russian.stem(keyword_to_remove)
    if stemmed_keyword_eng in keywords:
        keywords.remove(stemmed_keyword_eng)
        removed = True
        await message.reply(f"Stemmed English keyword '{stemmed_keyword_eng}' has been removed from the list.", reply_markup=markup)
    if stemmed_keyword_rus in keywords:
        keywords.remove(stemmed_keyword_rus)
        removed = True
        await message.reply(f"Stemmed Russian keyword '{stemmed_keyword_rus}' has been removed from the list.", reply_markup=markup)

    if not removed:
        await message.reply(f"Keyword '{keyword_to_remove}' not found in the list.", reply_markup=markup)

    save_config(forward_chats, keywords)
    dp.unregister_message_handler(remove_keyword_step)

async def resolve_chat_id_step(message: types.Message):
    group_link = message.text
    resolved_id = await get_chat_id_from_group(group_link)
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Back to Main Menu", callback_data='back_to_menu'))
    if resolved_id:
        await message.reply(f"The resolved chat ID is: {resolved_id}", reply_markup=markup)
    else:
        await message.reply("Failed to resolve chat ID from the provided link or username.", reply_markup=markup)

    dp.unregister_message_handler(resolve_chat_id_step)

@client.on(events.NewMessage)
async def message_handler(event):
    if forward_chats:
        chat_id = str(event.chat_id)
        if chat_id in forward_chats:
            if event.message.text:
                message_text = event.message.text.lower()

                for keyword in keywords:
                    if keyword in message_text:
                        sender = await event.get_sender()
                        sender_name = sender.username if sender.username else sender.first_name
                        print(f"Keyword '{keyword}' found in message from {sender_name}: {event.message.text}")

                        for group_id in TARGET_GROUP_IDS:
                            if group_id.strip():
                                await client.forward_messages(group_id.strip(), event.message)
                                print(f"Message forwarded to {group_id}")



async def main():
    # Start the Telethon client
    await client.start(phone=phone_number)

    # Run both the Aiogram bot and Telethon client concurrently
    await asyncio.gather(
        dp.start_polling(),           # Start Aiogram bot
        client.run_until_disconnected()  # Keep Telethon running
    )
if __name__ == '__main__':
    # Ensure both Aiogram and Telethon share the same event loop
    asyncio.run(main())


if __name__ == '__main__':
    # Ensure both Aiogram and Telethon share the same event loop
    asyncio.run(main())


