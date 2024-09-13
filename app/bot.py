import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from nltk.stem import SnowballStemmer

# Define your API credentials
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
config_file_path = './data/forward_chats.json'

# Initialize bot and dispatcher
bot = Bot(token=telegram_token)
dp = Dispatcher(bot)

# Initialize stemmers for English and Russian
stemmer_english = SnowballStemmer("english")
stemmer_russian = SnowballStemmer("russian")

# Get the whitelisted user IDs from the environment variable
whitelisted_ids = os.getenv("WHITELISTED_IDS", "")
WHITELISTED_IDS = [int(user_id) for user_id in whitelisted_ids.split(",") if user_id.isdigit()]

# Function to load chats and keywords from the JSON file
def load_config():
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as f:
            data = json.load(f)
            return data.get('chats', []), data.get('keywords', [])
    else:
        print(f"Config file {config_file_path} not found.")
        return [], []

# Function to save the chat and keyword lists to the JSON file
def save_config(chats, keywords):
    with open(config_file_path, 'w') as f:
        json.dump({"chats": chats, "keywords": keywords}, f)

# Load the chat and keyword list from the volume
forward_chats, keywords = load_config()

# Check if a user is whitelisted
def is_whitelisted(user_id):
    return user_id in WHITELISTED_IDS

# Command to display the welcome message with available commands
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

# Callback handler for inline buttons
@dp.callback_query_handler(lambda c: c.data)
async def process_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if not is_whitelisted(user_id):
        await bot.send_message(user_id, "Access denied. You are not authorized to use this bot.")
        return

    chat_id = callback_query.from_user.id

    # Handle chat management
    if callback_query.data == 'add_chat':
        await bot.send_message(chat_id, "Please send the chat ID, username, or https://t.me/ link to add:")
        dp.register_message_handler(add_chat_step, state=None)
    elif callback_query.data == 'remove_chat':
        await bot.send_message(chat_id, "Please send the chat ID, @username, or https://t.me/ link to remove:")
        dp.register_message_handler(remove_chat_step, state=None)
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

# Handle adding a chat
async def add_chat_step(message: types.Message):
    chat_to_add = message.text

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Back to Main Menu", callback_data='back_to_menu'))

    # Check if the input is a valid chat ID, link, or username
    if chat_to_add.startswith("https://t.me/") or chat_to_add.startswith("@"):
        resolved_id = await get_chat_id_from_group(chat_to_add)
        if resolved_id:
            chat_to_add = str(resolved_id)
        else:
            await message.reply("Failed to resolve chat ID from the provided link or username.", reply_markup=markup)
            return

    # Add the resolved or provided chat ID
    if chat_to_add not in forward_chats:
        forward_chats.append(chat_to_add)
        save_config(forward_chats, keywords)
        await message.reply(f"Chat {chat_to_add} has been added to the subscription list.", reply_markup=markup)
    else:
        await message.reply(f"Chat {chat_to_add} is already in the subscription list.", reply_markup=markup)

    dp.unregister_message_handler(add_chat_step)

# Handle removing a chat
async def remove_chat_step(message: types.Message):
    chat_to_remove = message.text

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Back to Main Menu", callback_data='back_to_menu'))

    # Check if the input is a valid chat ID, link, or username
    if chat_to_remove.startswith("https://t.me/") or chat_to_remove.startswith("@"):
        resolved_id = await get_chat_id_from_group(chat_to_remove)
        if resolved_id:
            chat_to_remove = str(resolved_id)
        else:
            await message.reply("Failed to resolve chat ID from the provided link or username.", reply_markup=markup)
            return

    # Remove the resolved or provided chat ID
    if chat_to_remove in forward_chats:
        forward_chats.remove(chat_to_remove)
        save_config(forward_chats, keywords)
        await message.reply(f"Chat {chat_to_remove} has been removed from the subscription list.", reply_markup=markup)
    else:
        await message.reply(f"Chat {chat_to_remove} is not in the subscription list.", reply_markup=markup)

    dp.unregister_message_handler(remove_chat_step)

# Handle adding a keyword
async def add_keyword_step(message: types.Message):
    keyword_to_add = message.text.lower()

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Back to Main Menu", callback_data='back_to_menu'))

    if keyword_to_add not in keywords:
        keywords.append(keyword_to_add)
        save_config(forward_chats, keywords)
        await message.reply(f"Keyword '{keyword_to_add}' has been added to the list.", reply_markup=markup)
    else:
        await message.reply(f"Keyword '{keyword_to_add}' is already in the list.", reply_markup=markup)

    dp.unregister_message_handler(add_keyword_step)

# Handle removing a keyword
async def remove_keyword_step(message: types.Message):
    keyword_to_remove = message.text.lower()

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Back to Main Menu", callback_data='back_to_menu'))

    if keyword_to_remove in keywords:
        keywords.remove(keyword_to_remove)
        save_config(forward_chats, keywords)
        await message.reply(f"Keyword '{keyword_to_remove}' has been removed from the list.", reply_markup=markup)
    else:
        await message.reply(f"Keyword '{keyword_to_remove}' is not found in the list.", reply_markup=markup)

    dp.unregister_message_handler(remove_keyword_step)

# Utility function to resolve chat IDs from links or usernames
async def get_chat_id_from_group(group_link):
    try:
        entity = await client.get_entity(group_link)
        return entity.id
    except Exception as e:
        print(f"Error resolving link: {e}")
        return None

if __name__ == '__main__':
    # Start the bot
    executor.start_polling(dp, skip_updates=True)
import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from nltk.stem import SnowballStemmer
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define your API credentials
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
config_file_path = './data/forward_chats.json'

# Initialize bot and dispatcher
bot = Bot(token=telegram_token)
dp = Dispatcher(bot)

# Initialize stemmers for English and Russian
stemmer_english = SnowballStemmer("english")
stemmer_russian = SnowballStemmer("russian")

# Get the whitelisted user IDs from the environment variable
whitelisted_ids = os.getenv("WHITELISTED_IDS", "")
WHITELISTED_IDS = [int(user_id) for user_id in whitelisted_ids.split(",") if user_id.isdigit()]

# Function to load chats and keywords from the JSON file
def load_config():
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as f:
            data = json.load(f)
            return data.get('chats', []), data.get('keywords', [])
    else:
        print(f"Config file {config_file_path} not found.")
        return [], []

# Function to save the chat and keyword lists to the JSON file
def save_config(chats, keywords):
    with open(config_file_path, 'w') as f:
        json.dump({"chats": chats, "keywords": keywords}, f)

# Load the chat and keyword list from the volume
forward_chats, keywords = load_config()

# Check if a user is whitelisted
def is_whitelisted(user_id):
    return user_id in WHITELISTED_IDS

# Command to display the welcome message with available commands
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

# Callback handler for inline buttons
@dp.callback_query_handler(lambda c: c.data)
async def process_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if not is_whitelisted(user_id):
        await bot.send_message(user_id, "Access denied. You are not authorized to use this bot.")
        return

    chat_id = callback_query.from_user.id

    # Handle chat management
    if callback_query.data == 'add_chat':
        await bot.send_message(chat_id, "Please send the chat ID, username, or https://t.me/ link to add:")
        dp.register_message_handler(add_chat_step, state=None)
    elif callback_query.data == 'remove_chat':
        await bot.send_message(chat_id, "Please send the chat ID, @username, or https://t.me/ link to remove:")
        dp.register_message_handler(remove_chat_step, state=None)
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

# Handle adding a chat
async def add_chat_step(message: types.Message):
    chat_to_add = message.text

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Back to Main Menu", callback_data='back_to_menu'))

    # Check if the input is a valid chat ID, link, or username
    if chat_to_add.startswith("https://t.me/") or chat_to_add.startswith("@"):
        resolved_id = await get_chat_id_from_group(chat_to_add)
        if resolved_id:
            chat_to_add = str(resolved_id)
        else:
            await message.reply("Failed to resolve chat ID from the provided link or username.", reply_markup=markup)
            return

    # Add the resolved or provided chat ID
    if chat_to_add not in forward_chats:
        forward_chats.append(chat_to_add)
        save_config(forward_chats, keywords)
        await message.reply(f"Chat {chat_to_add} has been added to the subscription list.", reply_markup=markup)
    else:
        await message.reply(f"Chat {chat_to_add} is already in the subscription list.", reply_markup=markup)

    dp.unregister_message_handler(add_chat_step)

# Handle removing a chat
async def remove_chat_step(message: types.Message):
    chat_to_remove = message.text

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Back to Main Menu", callback_data='back_to_menu'))

    # Check if the input is a valid chat ID, link, or username
    if chat_to_remove.startswith("https://t.me/") or chat_to_remove.startswith("@"):
        resolved_id = await get_chat_id_from_group(chat_to_remove)
        if resolved_id:
            chat_to_remove = str(resolved_id)
        else:
            await message.reply("Failed to resolve chat ID from the provided link or username.", reply_markup=markup)
            return

    # Remove the resolved or provided chat ID
    if chat_to_remove in forward_chats:
        forward_chats.remove(chat_to_remove)
        save_config(forward_chats, keywords)
        await message.reply(f"Chat {chat_to_remove} has been removed from the subscription list.", reply_markup=markup)
    else:
        await message.reply(f"Chat {chat_to_remove} is not in the subscription list.", reply_markup=markup)

    dp.unregister_message_handler(remove_chat_step)

# Handle adding a keyword
async def add_keyword_step(message: types.Message):
    keyword_to_add = message.text.lower()

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Back to Main Menu", callback_data='back_to_menu'))

    if keyword_to_add not in keywords:
        keywords.append(keyword_to_add)
        save_config(forward_chats, keywords)
        await message.reply(f"Keyword '{keyword_to_add}' has been added to the list.", reply_markup=markup)
    else:
        await message.reply(f"Keyword '{keyword_to_add}' is already in the list.", reply_markup=markup)

    dp.unregister_message_handler(add_keyword_step)

# Handle removing a keyword
async def remove_keyword_step(message: types.Message):
    keyword_to_remove = message.text.lower()

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Back to Main Menu", callback_data='back_to_menu'))

    if keyword_to_remove in keywords:
        keywords.remove(keyword_to_remove)
        save_config(forward_chats, keywords)
        await message.reply(f"Keyword '{keyword_to_remove}' has been removed from the list.", reply_markup=markup)
    else:
        await message.reply(f"Keyword '{keyword_to_remove}' is not found in the list.", reply_markup=markup)

    dp.unregister_message_handler(remove_keyword_step)

# Utility function to resolve chat IDs from links or usernames
async def get_chat_id_from_group(group_link):
    try:
        entity = await client.get_entity(group_link)
        return entity.id
    except Exception as e:
        print(f"Error resolving link: {e}")
        return None

if __name__ == '__main__':
    # Start the bot
    executor.start_polling(dp, skip_updates=True)
