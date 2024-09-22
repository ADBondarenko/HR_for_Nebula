import os
import json
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
import logging
import re
from pyrogram.errors import RPCError

# Logging
logging.basicConfig(filename='bot_py.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Define your API credentials
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
phone_number = os.getenv("PHONE_NUMBER")
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
config_file_path = './data/forward_chats.json'
session_string = os.getenv("SESSION_STRING")

#Load target groups
TARGET_GROUP_IDS = os.getenv("TARGET_GROUP_IDS", "").split(",")

#Stemmer functionality -- NOT YET IMPLETENTED
# stemmer_english = SnowballStemmer("english") --YET TO BE IMPLEMENTED
# stemmer_russian = SnowballStemmer("russian") --YET TO BE IMPLEMENTED

#Whitelisted IDs
whitelisted_ids = os.getenv("WHITELISTED_IDS", "")
WHITELISTED_IDS = [int(user_id) for user_id in whitelisted_ids.split(",") if user_id.isdigit()]

#Bot authentification
bot = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=telegram_token)

def log_handler_registration(handler_name):
    logger.debug(f"Handler '{handler_name}' has been registered.")

# Utils 
def load_config():
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as f:
            data = json.load(f)
            return data.get('chats', []), data.get('keywords', [])
    else:
        print(f"Config file {config_file_path} not found.")
        return [], []

def save_config(chats, keywords):
    with open(config_file_path, 'w') as f:
        json.dump({"chats": chats, "keywords": keywords}, f)
        
forward_chats, keywords = load_config()

def handle_telegram_url(url):
    url = url.strip()

    # If the input is already in @username format
    if url.startswith("@"):
        return url

    # If the input is a username without '@'
    if re.match(r"^[\w\d_]{5,}$", url):
        return f"@{url}"

    # Normalize the URL by ensuring it starts with 'https://'
    if not url.startswith("http"):
        url = "https://" + url

    # If the URL is an invite link with the '+' format (used for private groups, new format)
    if re.match(r"https://(t|telegram)\.me/\+[\w\d]+", url):
        return url

    # If the URL is an old invite link with the 'joinchat' format
    if re.match(r"https://(t|telegram)\.me/joinchat/[\w\d]+", url):
        return url

    # If the URL is a public channel/group (strip to @username)
    match = re.match(r"https://(t|telegram)\.me/([^/]+)$", url)
    if match:
        username = match.group(2)
        # Exclude 'joinchat' and '+' prefixes
        if not username.startswith("joinchat") and not username.startswith("+"):
            return f"@{username}"

    # If none of the above, return None
    return None

async def get_chat_id(username):
    try: 
        chat = await bot.get_chat(username)
        return chat.id
        
    except RPCError as e:
        await bot.send_message("me", f"Error: Could not retrieve chat ID. Details: {str(e)}")
    except Exception as e:
        # Catch any other exceptions and send an error message
        await bot.send_message("me", f"Unexpected error occurred: {str(e)}")

def is_authorized(user_id):
    return user_id in WHITELISTED_IDS

# Bot menu and commands
async def main_menu(client, message):
    menu = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Add New Chat", callback_data="add_new_chat")],
            [InlineKeyboardButton("Get All Chats", callback_data="get_chats")],
            [InlineKeyboardButton("Delete a Chat", callback_data="delete_chat")],
            [InlineKeyboardButton("Add a Keyword", callback_data="add_new_keyword")],
            [InlineKeyboardButton("Delete a Keyword", callback_data="delete_keyword")],
            [InlineKeyboardButton("Get all Keywords", callback_data="get_keywords")]
        ]
    )
    
    # Send the main menu to the user
    await message.reply("Main Menu:", reply_markup=menu)

# Function to handle the "Back to menu" action
async def back_to_menu(client, callback_query):
    await callback_query.message.edit_text("Returning to the main menu...")
    await main_menu(client, callback_query.message)

# Start command with authorization check
@bot.on_message(filters.command("start"))
async def start(client, message):
    logger.debug("Command start received")
    if not is_authorized(message.from_user.id):
        await message.reply("You are not authorized to use this bot.")
        return
    else:
        await main_menu(client, message)
        
log_handler_registration("start")

# Callback query handler for button clicks
@bot.on_callback_query()
async def button_click(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id

    if data == "add_new_chat":
        await callback_query.message.reply(
            "Please provide a new chat to add (e.g., @username or a t.me link):",
            reply_markup=ForceReply()
        )

    elif data == "get_chats":
        chats, keywords = load_config()
        if not chats:
            text = "No monitored chats found."
        else:
            chat_list = "\n".join([f"ID: {chat['id']}, Prompt: {chat['prompt']}" for chat in chats])
            text = f"Monitored Chats:\n{chat_list}"
        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Back to menu", callback_data="back_to_menu")]]
            )
        )

    elif data == "delete_chat":
        await callback_query.message.reply(
            "Please provide a chat to delete (e.g., @username or a t.me link):",
            reply_markup=ForceReply()
        )

    elif data == "add_new_keyword":
        await callback_query.message.reply(
            "Please provide a keyword to add:",
            reply_markup=ForceReply()
        )

    elif data == "delete_keyword":
        await callback_query.message.reply(
            "Please provide a keyword to delete:",
            reply_markup=ForceReply()
        )

    elif data == "get_keywords":
        chats, keywords = load_config()
        if not keywords:
            text = "No monitored keywords found."
        else:
            keyword_list = "\n".join([str(keyword) for keyword in keywords])
            text = f"Monitored Keywords:\n{keyword_list}"
        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Back to menu", callback_data="back_to_menu")]]
            )
        )

    elif data == "back_to_menu":
        await back_to_menu(client, callback_query)
        
log_handler_registration("callbacks")

# Message handler to process user input based on replies
@bot.on_message(filters.private & filters.reply)
async def handle_private_reply(client, message):
    if not is_authorized(message.from_user.id):
        await message.reply("You are not authorized to use this bot.")
        return

    if message.reply_to_message.from_user.is_bot:
        prompt = message.reply_to_message.text
        if "Please provide a new chat to add" in prompt:
            await add_new_chat(client, message)
        elif "Please provide a chat to delete" in prompt:
            await delete_chat(client, message)
        elif "Please provide a keyword to add" in prompt:
            await add_keyword(client, message)
        elif "Please provide a keyword to delete" in prompt:
            await delete_keyword(client, message)
        else:
            await message.reply("Unrecognized action.")
    else:
        await message.reply("Please select an option from the menu.")
        
log_handler_registration("handle_private_reply")

# Function to add a new chat
async def add_new_chat(client, message):
    logger.debug("Function add_new_chat called")
    chat_id_input = message.text.strip()
    chat_identifier = handle_telegram_url(chat_id_input)
    if not chat_identifier:
        await message.reply("Invalid chat ID or URL.")
        await main_menu(client, message)
        return

    chat_id = await get_chat_id(chat_identifier)
    if not chat_id:
        await message.reply("Could not retrieve chat ID.")
        await main_menu(client, message)
        return

    chats, keywords = load_config()

    # Check if the chat is already in the list
    if any(chat['id'] == chat_id for chat in chats):
        await message.reply(f"Chat ID {chat_id} is already in the list.")
    else:
        chats.append({'id': chat_id, 'prompt': chat_id_input})
        save_config(chats, keywords)
        await message.reply(f"Chat ID {chat_id} added successfully!")

    # Return to main menu
    await main_menu(client, message)
    
log_handler_registration("add_new_chat")

# Function to delete a chat
async def delete_chat(client, message):
    logger.debug("Function delete_chat called")
    chat_id_input = message.text.strip()
    chat_identifier = handle_telegram_url(chat_id_input)
    if not chat_identifier:
        await message.reply("Invalid chat ID or URL.")
        await main_menu(client, message)
        return

    chat_id = await get_chat_id(chat_identifier)
    if not chat_id:
        await message.reply("Could not retrieve chat ID.")
        await main_menu(client, message)
        return

    chats, keywords = load_config()

    # Find the chat in the list
    chat_to_remove = next((chat for chat in chats if chat['id'] == chat_id), None)

    if not chat_to_remove:
        await message.reply(f"Chat ID {chat_id} is not in the list.")
    else:
        chats.remove(chat_to_remove)
        save_config(chats, keywords)
        await message.reply(f"Chat ID {chat_id} deleted successfully!")

    # Return to main menu
    await main_menu(client, message)
    
log_handler_registration("delete_chat")

# Function to add a keyword
async def add_keyword(client, message):
    logger.debug("Function add_keyword called")
    keyword = message.text.strip()
    chats, keywords = load_config()

    if keyword in keywords:
        await message.reply(f"Keyword '{keyword}' is already in the list.")
    else:
        keywords.append(keyword)
        save_config(chats, keywords)
        await message.reply(f"Keyword '{keyword}' added successfully!")

    # Return to main menu
    await main_menu(client, message)
    
log_handler_registration("add_keyword")

# Function to delete a keyword
async def delete_keyword(client, message):
    logger.debug("Function delete_keyword called")
    keyword = message.text.strip()
    chats, keywords = load_config()

    if keyword not in keywords:
        await message.reply(f"Keyword '{keyword}' is not in the list.")
    else:
        keywords.remove(keyword)
        save_config(chats, keywords)
        await message.reply(f"Keyword '{keyword}' deleted successfully!")

    # Return to main menu
    await main_menu(client, message)
    
log_handler_registration("delete_keyword")

# Function to monitor messages and forward based on keywords
def monitored_chats_filter(_, __, message):
    chats, _ = load_config()
    chat_ids = [chat['id'] for chat in chats]
    return message.chat.id in chat_ids

@bot.on_message(filters.create(monitored_chats_filter) & filters.text)
async def keyword_listener(client, message):
    _, keywords = load_config()
    if not keywords:
        return
    for keyword in keywords:
        if keyword.lower() in message.text.lower():
            for target_chat in TARGET_GROUP_IDS:
                await message.forward(target_chat)
                
log_handler_registration("keyword_listener")

bot.run()
