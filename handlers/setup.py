from pyrogram import Client, filters
from pyrogram.types import Message
import config

# ========== 管理员专用检查 ==========
def is_admin(client, user_id):
    """检查是否是管理员"""
    return user_id == client.admin_id

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    """Handle /start command - 管理员专用"""
    # 非管理员直接拒绝，并显示用户 ID 用于调试
    if not is_admin(client, message.from_user.id):
        await message.reply_text(
            f"⛔ **此机器人为私人使用**\n\n"
            f"不对外开放。\n\n"
            f"---\n"
            f"**DEBUG**: 你的 ID 是 `{message.from_user.id}`\n"
            f"配置的 Admin ID 是 `{client.admin_id}`"
        )
        return
    
    # === Deep Linking 处理 (例如 /start file_unique_id) ===
    if len(message.command) > 1:
        param = message.command[1]
        
        # 尝试从数据库查找文件 (通过 unique_id)
        # 注意: 之前数据库设计没有直接通过 unique_id 查找的函数，我们需要去 implement 或者用 search
        # 为了高效，这里直接查库
        from database import db
        # 临时查询逻辑
        db.cursor.execute("SELECT * FROM files WHERE file_unique_id = ?", (param,))
        result = db.cursor.fetchone()
        
        if result:
            # result 结构: id, msg_id, chat_id, file_id, local_path, storage_mode, unique_id, name_enc, cap_enc ...
            # 索引: 0=id, 1=msg_id, 2=chat_id, 3=file_id, 4=local_path, 5=mode
            
            file_id = result[3]
            storage_mode = result[5]
            local_path = result[4]
            caption = db.decrypt_text(result[7]) # caption_enc is index 7
            
            # 发送文件
            try:
                if storage_mode == 's3':
                    from services.s3_client import s3
                    url = s3.generate_presigned_url(local_path)
                    await message.reply_text(f"☁️ **S3 文件下载**\n[点击下载]({url})\n{caption}")
                    
                elif storage_mode == 'local':
                    await message.reply_text(f"📂 **本地文件**\n路径: `{local_path}`\n(无法远程发送)\n{caption}")
                    
                else: 
                    # telegram / telegram_stealth 模式
                    if file_id:
                        await client.send_cached_media(
                            message.chat.id,
                            file_id,
                            caption=caption
                        )
                    else:
                         await message.reply_text("❌ 文件索引损坏：缺少 File ID")
            except Exception as e:
                 await message.reply_text(f"❌ 发送失败: {e}")
            return

    storage_mode = getattr(config, 'STORAGE_MODE', 'local').lower()
    
    if storage_mode == 's3':
        await message.reply_text(
            f"👋 **欢迎使用 Telegram 私人保险库 (S3云端版)**\n\n"
            f"☁️ **当前模式**: S3 对象存储\n"
            f"📦 **存储桶**: `{config.S3_BUCKET_NAME}`\n\n"
            f"发送给我的文件将自动上传到云端存储池 (R2/AWS)。"
        )
    elif storage_mode == 'local':
        await message.reply_text(
            f"👋 **欢迎使用 Telegram 私人保险库 (本地版)**\n\n"
            f"💻 **当前模式**: 本地硬盘存储\n"
            f"📂 **存储路径**: `{config.LOCAL_STORAGE_PATH}`\n\n"
            f"发送文件给我，我会存到本地硬盘。"
        )
    elif 'telegram' in storage_mode:
         await message.reply_text(
            f"👋 **欢迎使用 Telegram 私人保险库 (防封版)**\n\n"
            f"🛡️ **当前模式**: {storage_mode}\n"
            f"🔐 **特性**: 自动混淆 Hash + 文件名加密\n"
            f"♾️ **容量**: 无限 (Telegram 云)\n\n"
            f"发送文件给我，我会加密处理后存入私密仓库，并给你生成提取链接。"
        )
    else:
        # 原有的频道引导逻辑
        await message.reply_text(
            "👋 **欢迎使用 Telegram 私人保险库！**\n"
            "你需要配置 STORAGE_CHANNEL_ID 才能开始。"
        )

@Client.on_message(filters.forwarded & filters.private)
async def channel_id_sniffer(client: Client, message: Message):
    """Detect forwarded messages - 管理员专用"""
    if not is_admin(client, message.from_user.id):
        return
    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
        chat_title = message.forward_from_chat.title
        chat_type = message.forward_from_chat.type

        # 支持频道和群组
        if str(chat_type) in ["ChatType.CHANNEL", "ChatType.SUPERGROUP", "ChatType.GROUP"]:
            type_name = "频道" if "CHANNEL" in str(chat_type) else "群组"
            response = (
                f"✅ **成功获取{type_name}信息！**\n\n"
                f"📂 **{type_name}名称**: {chat_title}\n"
                f"🆔 **{type_name} ID**: `{chat_id}`\n\n"
                f"复制这个 ID，填到 `.env` 文件的 `TG_STORAGE_CHANNEL`：\n"
                f"```\nTG_STORAGE_CHANNEL={chat_id}\n```\n"
                f"**然后重启机器人！**"
            )
            await message.reply_text(response)
        else:
            await message.reply_text(
                f"⚠️ **不支持的类型**\n"
                f"检测到的类型: {chat_type}\n"
                f"请转发**群组或频道**的消息。"
            )
    else:
        await message.reply_text(
            "⚠️ **无法读取频道信息**\n"
            "这可能是因为该频道的隐私设置不允许转发来源。\n\n"
            "**尝试方法 B：**\n"
            "1. 在该频道里发一条消息。\n"
            "2. 复制那条消息的链接 (Copy Link)。\n"
            "3. 把链接发给我。"
        )

@Client.on_message(filters.text & filters.private & ~filters.reply & ~filters.command("start") & ~filters.command("recent") & ~filters.command("download") & ~filters.command("search") & ~filters.command("getid") & ~filters.command("linked") & ~filters.command("deleted") & ~filters.command("newcollection") & ~filters.command("addto") & ~filters.command("mycollections"))
async def link_handler(client: Client, message: Message):
    """Handle links and collection keys - 管理员专用"""
    if not is_admin(client, message.from_user.id):
        return
    import re
    text = message.text.strip()
    
    # 首先检查是否是提取码 (16-32位字母数字)
    import re
    import os
    import asyncio
    if re.match(r'^[a-zA-Z0-9]{16,32}$', text):
        from database import db
        file_info = db.get_file_by_key(text)
        if file_info:
            try:
                # 检查是否加密
                if file_info.get("is_encrypted"):
                    status_msg = await message.reply_text(
                        f"🔐 **发现加密档案**\n"
                        f"📄 文件: `{file_info['file_name']}`\n"
                        f"⏳ 正在云端解密并提取，请稍候..."
                    )
                    
                    # 使用 storage_client 下载加密文件
                    storage_client = client.storage_client
                    
                    # 从存储频道获取消息
                    enc_msg = await storage_client.get_messages(
                        file_info["chat_id"], 
                        file_info["message_id"]
                    )
                    
                    # 下载加密文件
                    dl_path = await storage_client.download_media(
                        enc_msg,
                        file_name=f"temp_enc_{text}.bin"
                    )
                    
                    # 解密
                    from services.crypto_utils import decrypt_file
                    import base64
                    
                    decrypted_path = f"temp_dec_{text}_{file_info['file_name']}"
                    aes_key = base64.b64decode(file_info["encryption_key"])
                    
                    await asyncio.to_thread(decrypt_file, dl_path, decrypted_path, aes_key)
                    
                    # 发送解密后的文件
                    await message.reply_document(
                        document=decrypted_path,
                        caption=f"✅ 解密成功: {file_info['file_name']}",
                        file_name=file_info['file_name']
                    )
                    
                    # 清理临时文件
                    if os.path.exists(dl_path): os.remove(dl_path)
                    if os.path.exists(decrypted_path): os.remove(decrypted_path)
                    
                    await status_msg.delete()
                else:
                    # 普通文件直接发送
                    await client.send_cached_media(
                        message.chat.id,
                        file_info["file_id"],
                        caption=file_info["caption"] or ""
                    )
                return
            except Exception as e:
                import traceback
                traceback.print_exc()
                await message.reply_text(f"❌ 文件发送失败: {e}")
                return
    
    # 然后检查是否是合集密钥
    from handlers.tools import handle_collection_key
    if await handle_collection_key(client, message, text):
        return  # 是有效密钥，已处理
    
    # Match pattern: https://t.me/c/123456789/10
    match = re.search(r"t\.me/c/(\d+)/", text)
    if match:
        channel_id_part = match.group(1)
        full_channel_id = int(f"-100{channel_id_part}")
        
        response = (
            f"✅ **通过链接识别到频道！**\n\n"
            f"🆔 **频道 ID**: `{full_channel_id}`\n\n"
            f"请复制这个 ID 修改 config.py，或者直接发给我让管理员修改。"
        )
        await message.reply_text(response)
        return


    # Simple check if it looks like a config update attempt or storage ID is default
    if config.STORAGE_CHANNEL_ID == -1000000000000:
        await message.reply_text(
            "⚠️ **配置未完成**\n\n"
            "如果你已经获取了频道 ID，请去修改 `config.py` 文件。\n"
            "如果你还没获取，请按 `/start` 的提示操作。"
        )

# ========== 群组消息监听 (用于 Peer 缓存) ==========
@Client.on_message(filters.group)
async def group_message_handler(client: Client, message: Message):
    """
    监听群组消息。
    当机器人在群组中收到消息时，Pyrogram 会自动缓存该群组的 peer 信息。
    这解决了机器人无法直接通过 ID 发送消息的问题 (Peer id invalid)。
    """
    # 只需要接收到消息即可，Pyrogram 内部会自动更新 session
    # 我们这里打印一条日志方便调试
    if message.chat.id == config.STORAGE_CHANNEL_ID:
        print(f"✅ Bot 收到存储频道 [{message.chat.title}] 的消息，Peer 缓存已更新。")

