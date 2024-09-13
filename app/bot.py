import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from nltk.stem import SnowballStemmer
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define your API credentials (get from my.telegram.org)
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
config_file_path = './data/forward_chats.json'

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
    )

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Add Chat", callback_data='add_chat'),
        InlineKeyboardButton("Remove Chat", callback_data='remove_chat'),
        InlineKeyboardButton("List Chats", callback_data='list_chats'),
        InlineKeyboardButton("Add Keyword", callback_data='add_keyword'),
        InlineKeyboardButton("Remove Keyword", callback_data='remove_keyword'),
        InlineKeyboardButton("List Keywords", callback_data='list_keywords')
    )

    await message.reply(welcome_message, reply_markup=markup)

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

async def process_add_chat(message: types.Message):
    input_text = message.text
    chat_id = await get_chat_id_from_group(input_text)

    if chat_id:
        if str(chat_id) not in forward_chats:
            forward_chats.append(str(chat_id))
            save_config(forward_chats, keywords)
            await message.reply(f"Chat with ID {chat_id} has been added successfully.")
        else:
            await message.reply(f"Chat {chat_id} is already in the subscription list.")
    else:
        await message.reply("No valid chat ID, handle, or link was provided. Please try again.")
    dp.unregister_message_handler(process_add_chat)

async def process_remove_chat(message: types.Message):
    input_text = message.text
    chat_id = await get_chat_id_from_group(input_text)

    if chat_id:
        if str(chat_id) in forward_chats:
            forward_chats.remove(str(chat_id))
            save_config(forward_chats, keywords)
            await message.reply(f"Chat with ID {chat_id} has been removed successfully.")
        else:
            await message.reply(f"Chat {chat_id} is not in the subscription list.")
    else:
        await message.reply("No valid chat ID, handle, or link was provided. Please try again.")
    dp.unregister_message_handler(process_remove_chat)

async def add_keyword_step(message: types.Message):
    keyword_to_add = message.text.lower()
    if keyword_to_add not in keywords:
        keywords.append(keyword_to_add)
        save_config(forward_chats, keywords)
        await message.reply(f"Keyword '{keyword_to_add}' has been added to the list.")
    dp.unregister_message_handler(add_keyword_step)

async def remove_keyword_step(message: types.Message):
    keyword_to_remove = message.text.lower()
    if keyword_to_remove in keywords:
        keywords.remove(keyword_to_remove)
        save_config(forward_chats, keywords)
        await message.reply(f"Keyword '{keyword_to_remove}' has been removed from the list.")
    else:
        await message.reply(f"Keyword '{keyword_to_remove}' not found in the list.")
    dp.unregister_message_handler(remove_keyword_step)

if __name__ == '__main__':
    # Start the bot
    executor.start_polling(dp, skip_updates=True)
