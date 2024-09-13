import os
import json
from telethon import TelegramClient, events
import asyncio



# Define your API credentials
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
phone_number = os.getenv("PHONE_NUMBER")
config_file_path = './data/forward_chats.json'

TARGET_GROUP_IDS = os.getenv("TARGET_GROUP_IDS", "").split(",")

client = TelegramClient('session_name', api_id, api_hash)

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

forward_chats, keywords = load_config()

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
    print("Starting Telegram client...")
    await client.start(phone=phone_number)
    print("Telegram client started.")

    # Keep the Telethon client running
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
