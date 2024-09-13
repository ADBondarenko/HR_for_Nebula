import os
import json
from telethon import TelegramClient, events
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from nltk.stem import SnowballStemmer

# Define your API credentials (get from my.telegram.org)
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
phone_number = os.getenv("PHONE_NUMBER")

# Path to the JSON file that stores the list of chats and keywords (inside the Docker volume)
config_file_path = './data/forward_chats.json'

# Define the target groups (list of IDs or usernames) to which messages will be forwarded
TARGET_GROUP_IDS = os.getenv("TARGET_GROUP_IDS", "").split(",")  # Comma-separated list of target group IDs or usernames

# Initialize the Telegram client (Telethon) and bot (Aiogram)
client = TelegramClient('session_name', api_id, api_hash)
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

    # Buttons to manage chats and keywords
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

# Get the chat ID of the current group
@dp.message_handler(commands=['get_chat_id'])
async def get_chat_id(message: types.Message):
    chat_id = message.chat.id
    await message.reply(f"The chat ID is: {chat_id}")

# Get the chat ID from a https://t.me/xxxx link or @username
async def get_chat_id_from_group(group_link):
    try:
        entity = await client.get_entity(group_link)
        return entity.id
    except Exception as e:
        print(f"Error resolving link: {e}")
        return None

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
        await bot.send_message(chat_id, f"The following chats are being monitored:\n" + "\n".join(forward_chats))

    # Handle keyword management
    elif callback_query.data == 'add_keyword':
        await bot.send_message(chat_id, "Please send the keyword to add:")
        dp.register_message_handler(add_keyword_step, state=None)
    elif callback_query.data == 'remove_keyword':
        await bot.send_message(chat_id, "Please send the keyword to remove:")
        dp.register_message_handler(remove_keyword_step, state=None)
    elif callback_query.data == 'list_keywords':
        await bot.send_message(chat_id, f"The following keywords are being monitored:\n" + "\n".join(keywords))

    # Get chat ID of the current group
    elif callback_query.data == 'get_chat_id':
        await bot.send_message(chat_id, f"The current chat ID is: {chat_id}")

    # Resolve chat ID from link
    elif callback_query.data == 'get_chat_id_from_group':
        await bot.send_message(chat_id, "Please send the https://t.me/ link to resolve:")
        dp.register_message_handler(resolve_chat_id_step, state=None)

# Handle adding a chat (resolve chat ID if a link or @username is provided)
async def add_chat_step(message: types.Message):
    if not is_whitelisted(message.from_user.id):
        await message.reply("Access denied. You are not authorized to use this bot.")
        return

    chat_to_add = message.text

    # Check if the input is a https://t.me/ link or @username and resolve the chat ID
    if chat_to_add.startswith("https://t.me/") or chat_to_add.startswith("@"):
        resolved_id = await get_chat_id_from_group(chat_to_add)
        if resolved_id:
            chat_to_add = str(resolved_id)
        else:
            await message.reply("Failed to resolve chat ID from the provided link or username.")
            return

    # Add the resolved or provided chat ID
    if chat_to_add not in forward_chats:
        forward_chats.append(chat_to_add)
        save_config(forward_chats, keywords)
        await message.reply(f"Chat {chat_to_add} has been added to the subscription list.")
    else:
        await message.reply(f"Chat {chat_to_add} is already in the subscription list.")

# Handle removing a chat (support for raw chat ID, @username, or https://t.me/ link)
async def remove_chat_step(message: types.Message):
    if not is_whitelisted(message.from_user.id):
        await message.reply("Access denied. You are not authorized to use this bot.")
        return

    chat_to_remove = message.text

    # Check if the input is a https://t.me/ link or @username and resolve the chat ID
    if chat_to_remove.startswith("https://t.me/") or chat_to_remove.startswith("@"):
        resolved_id = await get_chat_id_from_group(chat_to_remove)
        if resolved_id:
            chat_to_remove = str(resolved_id)
        else:
            await message.reply("Failed to resolve chat ID from the provided link or username.")
            return

    # Remove the resolved or provided chat ID
    if chat_to_remove in forward_chats:
        forward_chats.remove(chat_to_remove)
        save_config(forward_chats, keywords)
        await message.reply(f"Chat {chat_to_remove} has been removed from the subscription list.")
    else:
        await message.reply(f"Chat {chat_to_remove} is not in the subscription list.")

# Handle adding a keyword (with optional stemming)
async def add_keyword_step(message: types.Message):
    if not is_whitelisted(message.from_user.id):
        await message.reply("Access denied. You are not authorized to use this bot.")
        return

    keyword_to_add = message.text.lower()

    # Ask whether stemming should be applied (yes/no buttons)
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("Yes", callback_data=f'stemming_yes_{keyword_to_add}'),
               InlineKeyboardButton("No", callback_data=f'stemming_no_{keyword_to_add}'))

    await message.reply(f"Do you want to apply stemming for the keyword '{keyword_to_add}'?", reply_markup=markup)

# Handle keyword stemming based on user's selection
@dp.callback_query_handler(lambda c: c.data.startswith('stemming_'))
async def process_stemming_choice(callback_query: types.CallbackQuery):
    choice, keyword_to_add = callback_query.data.split('_')[1], callback_query.data.split('_')[2]
    chat_id = callback_query.from_user.id

    if choice == 'yes':
        # Detect language of the keyword and apply stemming
        if all('а' <= c <= 'я' for c in keyword_to_add):  # If the word contains only Cyrillic characters
            stemmed_keyword = stemmer_russian.stem(keyword_to_add)
            language = 'Russian'
        else:
            stemmed_keyword = stemmer_english.stem(keyword_to_add)
            language = 'English'

        # Add the base keyword and stemmed version
        if keyword_to_add not in keywords:
            keywords.append(keyword_to_add)
        if stemmed_keyword not in keywords:
            keywords.append(stemmed_keyword)

        save_config(forward_chats, keywords)
        await bot.send_message(chat_id, f"Keyword '{keyword_to_add}' and its stemmed version '{stemmed_keyword}' "
                                        f"({language}) have been added to the list.")

    else:
        # Only add the base keyword without stemming
        if keyword_to_add not in keywords:
            keywords.append(keyword_to_add)
            save_config(forward_chats, keywords)
            await bot.send_message(chat_id, f"Keyword '{keyword_to_add}' has been added to the list without stemming.")

# Handle removing a keyword
async def remove_keyword_step(message: types.Message):
    if not is_whitelisted(message.from_user.id):
        await message.reply("Access denied. You are not authorized to use this bot.")
        return

    keyword_to_remove = message.text.lower()

    # Remove the base keyword
    if keyword_to_remove in keywords:
        keywords.remove(keyword_to_remove)
        await message.reply(f"Keyword '{keyword_to_remove}' has been removed from the list.")
    
    # Remove the stemmed version of the keyword
    stemmed_keyword_eng = stemmer_english.stem(keyword_to_remove)
    stemmed_keyword_rus = stemmer_russian.stem(keyword_to_remove)
    if stemmed_keyword_eng in keywords:
        keywords.remove(stemmed_keyword_eng)
        await message.reply(f"Stemmed English keyword '{stemmed_keyword_eng}' has been removed from the list.")
    if stemmed_keyword_rus in keywords:
        keywords.remove(stemmed_keyword_rus)
        await message.reply(f"Stemmed Russian keyword '{stemmed_keyword_rus}' has been removed from the list.")

    save_config(forward_chats, keywords)

# Handle resolving a chat ID from a https://t.me/ link or @username
async def resolve_chat_id_step(message: types.Message):
    if not is_whitelisted(message.from_user.id):
        await message.reply("Access denied. You are not authorized to use this bot.")
        return

    group_link = message.text
    resolved_id = await get_chat_id_from_group(group_link)
    if resolved_id:
        await message.reply(f"The resolved chat ID is: {resolved_id}")
    else:
        await message.reply("Failed to resolve chat ID from the provided link or username.")

# Listen for messages in subscribed chats and forward them if they contain a keyword or a Telegram link
@client.on(events.NewMessage(chats=forward_chats))
async def message_handler(event):
    message_text = event.message.text.lower()

    # Forward message if it contains a keyword
    for keyword in keywords:
        if keyword in message_text:
            sender = await event.get_sender()
            sender_name = sender.username if sender.username else sender.first_name
            print(f"Keyword '{keyword}' found in message from {sender_name}: {event.message.text}")

            # Forward the message to all target groups
            for group_id in TARGET_GROUP_IDS:
                await client.forward_messages(group_id.strip(), event.message)
                print(f"Message forwarded to {group_id}")

async def main():
    # Start the Telethon client
    await client.start(phone=phone_number)
    
    # Notify when the client has started
    print("Client started. Listening for messages and commands...")
    
    # Keep the client running to listen for events
    await client.run_until_disconnected()

if __name__ == '__main__':
    # Run the bot
    executor.start_polling(dp, skip_updates=True)

    # Start the Telethon client and listen for new messages
    with client:
        client.loop.run_until_complete(main())
