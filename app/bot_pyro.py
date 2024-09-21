import os
import json
from pyrogram import Client, idle, filters
from pyrogram.handlers import MessageHandler
# from nltk.stem import SnowballStemmer --YET TO BE IMPLEMENTED
# from nltk import download --YET TO BE IMPLEMENTED
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import re
import asyncio
from pyrogram.errors import RPCError, FloodWait

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

#Client authentification
app = Client("my_session", session_string=session_string, api_id=api_id, api_hash=api_hash)
bot = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=telegram_token)



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
    # If the URL is an invite link with the "+" format (used for private groups, new format)
    if re.search(r"https://t\.me/\+[\w\d]+", url):
        # Pass the new invite link format unchanged to client.get_chat
        return url
    
    # If the URL is an old invite link with the "joinchat" format
    if re.search(r"https://t\.me/joinchat/[\w\d]+", url) or re.search(r"https://telegram\.me/joinchat/[\w\d]+", url):
        # Return the old invite link format unchanged
        return url
    
    # If the URL is a public channel/group (strip to @username)
    match = re.search(r"https://t\.me/([^/]+)", url)
    if match:
        username = match.group(1)
        # Check if this is a public group or channel and return @username format
        if not username.startswith("joinchat") and not username.startswith("+"):
            return f"@{username}"
    
    # If the URL does not match any known format, return None
    return None
    
async def get_chat_id(username):
    try: 
        chat = await app.get_chat(username)
        return chat.id
        
    except RPCError as e:
        await app.send_message("me", f"Error: Could not retrieve chat ID. Details: {str(e)}")
    except Exception as e:
        # Catch any other exceptions and send an error message
        await app.send_message("me", f"Unexpected error occurred: {str(e)}")
    
def is_authorized(user_id):
    return user_id in WHITELISTED_IDS

#Bot menu and commands
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
# Callback query handler (for button clicks)
# Function to handle the "Back to menu" action
async def back_to_menu(client, callback_query):
    await callback_query.message.edit_text("Returning to the main menu...")
    await main_menu(client, callback_query.message)

# Callback query handler for button clicks
@bot.on_callback_query()
async def button_click(client, callback_query):
    data = callback_query.data

    if data == "add_new_chat":
        await callback_query.message.edit_text(
            "Please provide a new chat to add:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Back to menu", callback_data="back_to_menu")]]
            )
        )
    elif data == "get_chats":
        await callback_query.message.edit_text(
            "List of chats currently monitored:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Back to menu", callback_data="back_to_menu")]]
            )
        )
    elif data == "delete_chat":
        await callback_query.message.edit_text(
            "Please provide a chat to delete:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Back to menu", callback_data="back_to_menu")]]
            )
        )

    elif data == "add_new_keyword":
        await callback_query.message.edit_text(
            "Please provide a keyword to add:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Back to menu", callback_data="back_to_menu")]]
            )
        )
    elif data == "delete_keyword":
        await callback_query.message.edit_text(
            "Please provide a keyword to delete:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Back to menu", callback_data="back_to_menu")]]
            )
        )
    elif data == "get_keywords":
        await callback_query.message.edit_text(
            "List of currently active keywords:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Back to menu", callback_data="back_to_menu")]]
            )
        )
    elif data == "back_to_menu":
        await back_to_menu(client, callback_query)

#Start command with authorization check (credintials are managed server-side)
@bot.on_message(filters.command("start"))
async def start(client, message):
    if not is_authorized(message.from_user.id):
        await message.reply("You are not authorized to use this bot.")
        return
    else:
        await main_menu(client, message)

@bot.on_message(filters.command("add_new_chat") & filters.private)
async def add_new_chat(client, message):
    if not is_authorized(message.from_user.id):
        await message.reply("You are not authorized to use this bot.")
        return
    
    # Check if the user provided a chat ID as a command argument
    if len(message.command) < 2:
        await message.reply("Please provide a chat ID. Usage: /add_chat_id <chat_id>")
        return
        
    await message.reply('''Please provide a chat ID in form of \n:
                    https://t.me/+D3fL1dzv2WQwYTg0 join link for private groups \n
                    @user or @channels for users and/or channels \n
                    https://t.me/rbc_news or https://t.me/rbc_news/1 link for channels. \n
                    Telegram-native IDs in form of -XXXXXXXXXXXX or -100XXXXXXXXXX can also be provided.                       
                    ''')

    chat_id = message.command[1]  # Get the chat ID from the command
    chat_id = handle_telegram_url(chat_id)
    chat_id = get_chat_id(chat_id)
    
    chats, keywords = load_config()    # Load existing chat IDs from the JSON file!!!!!!!

    if chat_id in chats:
        await message.reply(f"Chat ID {chat_id} is already in the list.")
    else:
        chats.append(chat_id)   # Add the new chat ID
        save_config(chats, keywords)    # Save the updated list to the JSON file
        await message.reply(f"Chat ID {chat_id} added successfully!")


# Command to add a keyword with a yes/no follow-up for stemmed version
@app.on_message(filters.command("add_keyword") & filters.private)
async def add_keyword(client, message):
    if not is_authorized(message.from_user.id):
        await message.reply("You are not authorized to use this bot.")
        return

    # Check if the user provided a keyword as a command argument
    if len(message.command) < 2:
        await message.reply("Please provide a keyword. Usage: /add_keyword <keyword>")
        return

    keyword = message.command[1]  # Get the chat ID from the command
    chats, keywords = load_config()    # Load existing chat IDs from the JSON file!!!!!!!

    if keyword in keywords:
        await message.reply(f"Chat ID {keyword} is already in the list.")
    else:
        keywords.append(keyword)   # Add the new chat ID
        save_config(chats, keywords)    # Save the updated list to the JSON file
        await message.reply(f"Chat ID {keyword} added successfully!")

@app.on_message(filters.command("delete_keyword") & filters.private)
async def delete_keyword(client, message):
    if not is_authorized(message.from_user.id):
        await message.reply("You are not authorized to use this bot.")
        return

    # Check if the user provided a keyword as a command argument
    if len(message.command) < 2:
        await message.reply("Please provide a keyword to delete. Usage: /delete_keyword <keyword>")
        return

    keyword = message.command[1]  # Get the keyword from the command
    chats, keywords = load_config()    # Load existing chats and keywords from the JSON file

    if keyword not in keywords:
        await message.reply(f"Keyword '{keyword}' is not in the list.")
    else:
        keywords.remove(keyword)  # Remove the keyword from the list
        save_config(chats, keywords)  # Save the updated list to the JSON file
        await message.reply(f"Keyword '{keyword}' deleted successfully!")

@app.on_message(filters.command("delete_chat") & filters.private)
async def delete_chat(client, message):
    if not is_authorized(message.from_user.id):
        await message.reply("You are not authorized to use this bot.")
        return

    # Check if the user provided a keyword as a command argument
    if len(message.command) < 2:
        await message.reply("Please provide a keyword to delete. Usage: /delete_keyword <keyword>")
        return

    chat = message.command[1]  # Get the keyword from the command
    chats, keywords = load_config()    # Load existing chats and keywords from the JSON file

    if chat not in chats:
        await message.reply(f"Keyword '{chat}' is not in the list of active chats.")
    else:
        keywords.remove(keyword)  # Remove the keyword from the list
        save_config(chats, keywords)  # Save the updated list to the JSON file
        await message.reply(f"Keyword '{chat}' deleted successfully!")

@app.on_message(filters.command("get_chats") & filters.private)
async def get_chats(client, message):
    if not is_authorized(message.from_user.id):
        await message.reply("You are not authorized to use this bot.")
        return

    chats, keywords = load_config()    # Load existing chats and keywords from the JSON file

    if not chats:
        await message.reply("No monitored chats found.")
    else:
        chat_list = "\n".join([str(chat) for chat in chats])
        await message.reply(f"Monitored Chats:\n{chat_list}")
        
@app.on_message(filters.command("get_keywords") & filters.private)
async def get_keywords(client, message):
    if not is_authorized(message.from_user.id):
        await message.reply("You are not authorized to use this bot.")
        return

    chats, keywords = load_config()    # Load existing chats and keywords from the JSON file

    if not keywords:
        await message.reply("No monitored keywords found.")
    else:
        keyword_list = "\n".join([str(keyword) for keyword in keywords])
        await message.reply(f"Monitored Chats:\n{keyword_list}")



#Client-based interactions    
@app.on_message(filters.text)
async def keyword_listener(client, message):
    chats, keywords = load_config()
    if message.chat.id not in chats:
        return
    for keyword in keywords:  
        if keyword.lower() in message.text.lower():  # Check if keyword is in the message
            for target_chat in TARGET_GROUP_IDS:
                await message.forward(target_chat)


async def main():
    try:
        await bot.start()
    except FloodWait as e:
        await asyncio.sleep(e.value)
    try:
        await app.start()
    except FloodWait as e:
        await asyncio.sleep(e.value)
    
    await idle()
if __name__ == "__main__":
    asyncio.run(main())