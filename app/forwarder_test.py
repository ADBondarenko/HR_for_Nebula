import os
import json
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
import logging
import re
from pyrogram.errors import RPCError



# Define your API credentials
telegram_token = "7859329027:AAF4zbBLSZSbXhDeYEH9dZMDkbOK7YhgXO4"
api_id = "25873858"
api_hash = "89b04d875bbeb3c96cc7c97957bbe231"
config_file_path = './data/forward_chats.json'
session_string = ("BAGIaxsAkj7-5ujO6UFkcJXeeUEPB670VbwxBAUm_r-KOkuCNHT20_Mezbkh9-Dban-Yi4UroVPI0pEMMfDLMmjlcT8d4H4GKmTln7dZYukcptQoXPhTsWSmuxj1tcBYjbLnzi0TeutkpyYSPrPiI9CEu_j2f4jRS0ltvUUZ2bR071jlyHxcDCiyCRcVvlaZ_IRV6ksLwYl299xa7Mk7HBwcOzaDyk4AR2O2-7F9O6WraDH7RYOJj_arsETCClWPPIvHvwyOZbfDGRZcTCU0nbx6gLWKDEN3UNx4fjx3WN9NPARXHuvIeyVDLk6YaHdrVvFGPLNBzHsUn1zQM5ZX2dscRaYqKAAAAAGY3tYLAA==============================================")

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
app = Client("my_client", api_id=api_id, api_hash=api_hash, session_string=telegram_token)



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

app.run()