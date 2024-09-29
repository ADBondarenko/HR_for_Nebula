import os
import json
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
import logging
import re
from pyrogram.errors import RPCError, PeerIdInvalid



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
TARGET_GROUP_IDS = [int(id) for id in TARGET_GROUP_IDS]

# Logging
logging.basicConfig(filename='forwarder_py.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

#Сlient authentification
app = Client("my_client", api_id=api_id, api_hash=api_hash, phone_number = phone_number)


#Client-based interactions    
@app.on_message(filters.text)
async def keyword_listener(client, message):
    TARGET_GROUP_IDS = os.getenv("TARGET_GROUP_IDS", "").split(",")
    TARGET_GROUP_IDS = [int(id) for id in TARGET_GROUP_IDS]
    chats, keywords = load_config()
    chat_list = [i['id'] for i in chats]
    if message.chat.id not in chat_list:
        return
    for keyword in keywords:  
        if keyword.lower() in message.text.lower():  # Check if keyword is in the message
            for target_chat in TARGET_GROUP_IDS:
                try:
                    await message.forward(target_chat)
                    logger.debug(f"Message forwarded to chat ID: {target_chat}")
                except PeerIdInvalid:
                    logger.debug(f"Failed to forward message to {target_chat}: Peer ID invalid. Ensure the bot is in the target chat.")
                except RPCError as e:
                    logger.debug(f"Failed to forward message to {target_chat}: {e}")


@app.on_message(filters.text)
async def test_message(client, message):
    logger.debug(f"Message received from chat: {message.chat.id}")
    logger.debug(f"Sender: {message.from_user.first_name} ({message.from_user.id})")
    logger.debug(f"Message content: {message.text}")

app.run()