import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client
from config import API_ID, API_HASH

async def main():
    INVITE_LINK = "https://t.me/+OxMUqJ-a3qNjOTll"
    
    print(f"Connecting to storage client to join: {INVITE_LINK}")
    storage = Client("vault_storage", api_id=API_ID, api_hash=API_HASH)
    
    async with storage:
        try:
            print("Attempting to join chat...")
            chat = await storage.join_chat(INVITE_LINK)
            print(f"SUCCESS: Joined chat '{chat.title}'")
            print(f"CHAT_ID: {chat.id}")
        except Exception as e:
            print(f"ERROR during join: {e}")
            print("Fetching recent dialogs to find backup channel...")
            async for dialog in storage.get_dialogs(limit=20):
                print(f"Dialog: {dialog.chat.title} | ID: {dialog.chat.id}")# Just print all dialogs? No too many.
                pass

if __name__ == "__main__":
    asyncio.run(main())
