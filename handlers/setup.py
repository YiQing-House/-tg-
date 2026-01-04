from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import config
from handlers.tools import check_auth

# ========== 管理员专用检查 ==========
def is_admin(client, user_id):
    """检查是否是管理员"""
    return user_id == client.admin_id

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    """Handle /start command"""
    # 权限检查
    if not await check_auth(client, message):
        return

    
    

    # === Terms Check (Session Based) ===
    from handlers.session import is_session_active
    from database import db
    
    # Check if user agreed in THIS session
    if not is_session_active(message.from_user.id):
        # Also check DB for record purposes? 
        # User wants "Every time bot restarts", so strictly Session based for the Disclaimer SHOWING.
        # But we can still respect the DB if we wanted, but User explicitly asked for "Every time".
        # So we IGNORE DB for the *Interactive Check*.
        
        s_text = (
            "📜 **免责声明 (Disclaimer)**\n\n"
            "1. 本机器人仅用于个人数据备份与管理，代码开源且透明。\n"
            "2. 用户需自行承担使用本工具产生的一切后果。\n"
            "3. 请勿利用本工具存储或传播任何违反当地法律法规的内容。\n\n"
            "点击下方按钮代表你已阅读并同意以上条款。"
        )
        await message.reply_text(
            s_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ 我同意以上条款", callback_data="agree_terms")]])
        )
        return

    # 显示主菜单
    await send_main_menu(client, message)

async def send_main_menu(client, message):
    from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
    
    # Check Admin
    is_adm = message.from_user.id == client.admin_id
    
    buttons = [
        [KeyboardButton("📥 批量下载"), KeyboardButton("☁️ 存储/上传")]
    ]
    if is_adm:
        buttons.append([KeyboardButton("👮 管理员")])
        
    await message.reply_text(
        "👋 **欢迎回到私人文件保险箱！**\n\n"
        "我是你的个人数据管家，提供最高级别的数据加密存储与管理服务。\n"
        "请通过下方菜单选择功能：\n\n"
        "🔐 **数据安全**: 本地加密，云端存储\n"
        "⚡️ **极速体验**: 自动分流，满速上传\n"
        "🎥 **流媒体**: 支持原画质在线播放",
        "⚡️ **极速体验**: 自动分流，满速上传\n"
        "🎥 **流媒体**: 支持原画质在线播放",
        reply_markup=get_main_menu_keyboard(is_adm)
    )

def get_main_menu_keyboard(is_admin_user=False):
    from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
    buttons = [
        [KeyboardButton("📥 批量下载"), KeyboardButton("☁️ 存储/上传")]
    ]
    if is_admin_user:
        buttons.append([KeyboardButton("👮 管理员")])
    
    return ReplyKeyboardMarkup(
        buttons, 
        resize_keyboard=True, 
        one_time_keyboard=False,
        is_persistent=True,
        placeholder="请选择功能..."
    )

@Client.on_callback_query(filters.regex("agree_terms"))
async def terms_btn_callback(client: Client, callback):
    from database import db
    db.accept_terms(callback.from_user.id)
    
    await callback.answer("✅ 已同意条款")
    try: await callback.message.delete()
    except: pass
    
    # 这里的 message 可能是旧的，我们需要用 callback.message 的 chat_id 发新消息
    # 但 callback.message 是 Bot 发的消息，没有 from_user 指向 User.
    # 所以我们构造一个 fake message context 或者直接用 client.send_message
    
    # 重新构造 Message 对象是不行的，我们直接发
    is_adm = callback.from_user.id == client.admin_id
    buttons = [
        [KeyboardButton("📥 批量下载"), KeyboardButton("☁️ 存储/上传")]
    ]
    if is_adm:
        buttons.append([KeyboardButton("👮 管理员")])
        
    await client.send_message(
        callback.message.chat.id,
        "💡 当然，你也可以随时直接发送文件给我，我会自动处理。",
        reply_markup=ReplyKeyboardMarkup(
            buttons,
            resize_keyboard=True,
            one_time_keyboard=False,
            is_persistent=True,
            placeholder="请选择功能..."
        )
    )


    pass # Old logic removed


@Client.on_message(filters.forwarded & filters.private)
async def channel_id_sniffer(client: Client, message: Message):
    """Detect forwarded messages"""
    # 权限检查
    if not await check_auth(client, message):
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
    """Handle links and collection keys"""
    # 权限检查
    if not await check_auth(client, message):
        return
    import re
    text = message.text.strip()
    
    # 首先检查是否是提取码 (16-32位字母数字)
    import re
    import os
    import asyncio
    # 清理文本，去除可能的 @username 前缀
    # 例如用户输入: "@MyBot 1234abcd..."
    clean_text = re.sub(r'^@\w+\s+', '', text).strip()
    
    # 检查是否是提取码 (16-32位字母数字)
    # 使用 clean_text 进行匹配
    if re.match(r'^[a-zA-Z0-9]{16,32}$', clean_text):
        key = clean_text # 使用清理后的 key
        from database import db
        file_info = db.get_file_by_key(key)
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
                        file_name=f"temp_enc_{key}.bin"
                    )
                    
                    # 解密
                    from services.crypto_utils import decrypt_file
                    import base64
                    
                    decrypted_path = f"temp_dec_{key}_{file_info['file_name']}"
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

