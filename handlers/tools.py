from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import asyncio
import time
import re
import os
from pyrogram.types import Message as PyrogramMessage

print("🔁 Loading Handler: tools.py")

# 全局存储
user_dialogs_cache = {}
user_download_dest = {}
user_last_action = {}  # 频率限制：记录用户上次操作时间
user_collecting_mode = {}  # 收集模式：{user_id: {"collection_id": xxx, "collection_name": xxx, "files": []}}

# ========== 安全检查 ==========

def is_blacklisted(client, user_id):
    """检查用户是否在黑名单中"""
    return hasattr(client, 'blacklist') and user_id in client.blacklist

def check_rate_limit(user_id, limit_seconds=5):
    """检查频率限制，返回 True 表示通过，False 表示被限制"""
    now = time.time()
    last_time = user_last_action.get(user_id, 0)
    if now - last_time < limit_seconds:
        return False
    user_last_action[user_id] = now
    return True

@Client.on_message(filters.command("recent") & filters.private)
async def list_recent_chats(client: Client, message: Message):
    """
    List recent chats with pagination and category filter.
    管理员专用命令
    """
    # 管理员检查
    if message.from_user.id != client.admin_id:
        await message.reply_text("⛔ 此命令仅限管理员使用。")
        return
    
    user = client.user_client
    status_msg = await message.reply_text("🔄 正在获取对话列表（可能需要几秒钟）...")
    
    # 获取所有对话
    dialogs_list = []
    async for dialog in user.get_dialogs(limit=200):  # 增加扫描数量
        chat = dialog.chat
        
        # 处理名称，特别处理 deleted 账号
        if chat.first_name == "Deleted Account" or (hasattr(chat, 'is_deleted') and chat.is_deleted):
            title = "🚫 Deleted Account"
        else:
            title = chat.title or chat.first_name or "Unknown"
        
        # 生成链接
        if chat.username:
            link = f"https://t.me/{chat.username}"
        elif str(chat.type) in ["ChatType.CHANNEL", "ChatType.SUPERGROUP", "ChatType.GROUP"]:
            link = f"https://t.me/c/{str(chat.id).replace('-100', '')}/1"
        else:
            link = None
        
        # 分类标签
        chat_type = str(chat.type).replace("ChatType.", "")
        if chat_type == "PRIVATE" and hasattr(chat, 'is_bot') and chat.is_bot:
            chat_type = "BOT"
        
        dialogs_list.append({
            "title": title, 
            "id": chat.id, 
            "type": chat_type,
            "link": link
        })
    
    if not dialogs_list:
        await status_msg.edit_text("❌ 没有找到任何对话。")
        return
    
    # 缓存结果
    user_dialogs_cache[message.from_user.id] = dialogs_list
    
    # 显示第一页（默认全部）
    await show_dialogs_page(status_msg, dialogs_list, page=0, filter_type="ALL")

@Client.on_message(filters.command("search") & filters.private)
async def search_chats(client: Client, message: Message):
    """
    Search chats by keyword.
    Usage: /search <keyword>
    """
    from pyrogram.types import ForceReply
    
    args = message.command
    
    # 权限检查
    if message.from_user.id != client.admin_id:
        return

    if len(args) < 2:
        await message.reply_text(
            "🔍 **搜索对话**\n\n"
            "请直接输入你要搜索的关键词：\n"
            "（例如输入：福利）",
            reply_markup=ForceReply(placeholder="输入关键词...")
        )
        return
    
    keyword = " ".join(args[1:]).lower()
    await do_search(client, message, keyword)

@Client.on_message(filters.reply & filters.private & filters.text)
async def handle_reply_input(client: Client, message: Message):
    """Handle reply to search/download/newcollection prompts."""
    # 权限检查
    if message.from_user.id != client.admin_id:
        return

    if not message.reply_to_message:
        return
    
    prompt_text = message.reply_to_message.text or ""
    
    # 处理搜索回复
    if "请直接输入你要搜索的关键词" in prompt_text:
        keyword = message.text.strip()
        if keyword:
            await do_search(client, message, keyword.lower())
    
    # 处理下载回复
    elif "请按格式输入" in prompt_text and "频道ID 数量" in prompt_text:
        parts = message.text.strip().split()
        if len(parts) >= 2:
            try:
                chat_id = int(parts[0])
                limit = int(parts[1])
                dest = user_download_dest.get(message.from_user.id, "channel")
                await do_batch_download(client, message, chat_id, limit, dest)
            except ValueError:
                await message.reply_text("❌ 格式错误！请输入：`频道ID 数量`\n例如：`-1001234567890 10`")
    
    # 处理创建合集回复
    elif "请输入合集名称" in prompt_text:
        collection_name = message.text.strip()
        if collection_name:
            await do_create_collection(client, message, collection_name)

async def do_search(client, message, keyword):
    """Perform the actual search."""
    user = client.user_client
    status_msg = await message.reply_text(f"🔍 正在搜索包含 **{keyword}** 的对话...")
    
    results = []
    count = 0
    async for dialog in user.get_dialogs(limit=500):
        chat = dialog.chat
        title = chat.title or chat.first_name or "Unknown"
        if keyword in title.lower():
            count += 1
            # 生成链接
            if chat.username:
                link = f"https://t.me/{chat.username}"
            elif str(chat.type) in ["ChatType.CHANNEL", "ChatType.SUPERGROUP", "ChatType.GROUP"]:
                link = f"https://t.me/c/{str(chat.id).replace('-100', '')}/1"
            else:
                link = None
            
            link_text = f"[🔗]({link})" if link else ""
            chat_type = str(chat.type).replace("ChatType.", "")
            results.append(f"{count}. **{title}** {link_text}\n🆔 `{chat.id}` | {chat_type}\n")
    
    if results:
        output = f"🔎 **搜索结果** (找到 {len(results)} 个)\n\n"
        output += "\n".join(results[:15])  # 最多显示15个
        if len(results) > 15:
            output += f"\n(还有 {len(results)-15} 个结果未显示)"
        output += "\n\n👉 复制 ID 后发送：`/download ID 数量`"
    else:
        output = f"❌ 没有找到包含 **{keyword}** 的对话。"
    await status_msg.edit_text(output)

@Client.on_message(filters.command("deleted") & filters.private)
async def find_deleted_accounts(client: Client, message: Message):
    """Specifically scan for deleted/banned account chats. 管理员专用"""
    # 管理员检查
    if message.from_user.id != client.admin_id:
        await message.reply_text("⛔ 此命令仅限管理员使用。")
        return
    
    user = client.user_client
    status_msg = await message.reply_text("🔍 正在扫描所有对话，寻找 Deleted Account...")
    
    results = []
    count = 0
    async for dialog in user.get_dialogs(limit=500):  # 扫描更多
        chat = dialog.chat
        count += 1
        
        # 多种方式检测 deleted account
        is_deleted = False
        name = chat.first_name or chat.title or ""
        
        # 方式1: 名字就是 Deleted Account
        if "Deleted Account" in name or "deleted" in name.lower():
            is_deleted = True
        
        # 方式2: 检查 is_deleted 属性（如果存在）
        if hasattr(chat, 'is_deleted') and chat.is_deleted:
            is_deleted = True
        
        # 方式3: 私聊但没有 first_name 和 last_name
        if str(chat.type) == "ChatType.PRIVATE" and not chat.first_name and not chat.username:
            is_deleted = True
            name = "[空名字-可能是deleted]"
        
        if is_deleted:
            results.append({
                "name": name or "[无名]",
                "id": chat.id,
                "type": str(chat.type)
            })
    
    if results:
        output = f"🔎 扫描了 {count} 个对话，找到 {len(results)} 个疑似 Deleted Account：\n\n"
        for i, r in enumerate(results[:15], 1):
            output += f"{i}. **{r['name']}**\n🆔 `{r['id']}` ← 点击复制\n\n"
        output += "⚠️ 死号无法通过链接跳转，请直接复制 ID\n"
        output += "👉 然后发送：`/download ID 数量`"
        await status_msg.edit_text(output)
    else:
        output = f"❌ 扫描了 {count} 个对话，没有找到 Deleted Account。\n\n"
        output += "可能的原因：\n"
        output += "1. 你已经删除了那个对话\n"
        output += "2. 那个账号还没被封（名字没变成 Deleted Account）\n"
        output += "3. 你从未跟那个账号有过对话"
        await status_msg.edit_text(output)

async def show_dialogs_page(message, dialogs_list, page=0, filter_type="ALL"):
    """Helper to show a specific page of dialogs with optional filtering."""
    
    # 根据类型过滤
    if filter_type != "ALL":
        filtered_list = [d for d in dialogs_list if d['type'] == filter_type]
    else:
        filtered_list = dialogs_list
    
    per_page = 8
    total_pages = max(1, (len(filtered_list) + per_page - 1) // per_page)
    start = page * per_page
    end = start + per_page
    page_items = filtered_list[start:end]
    
    # 统计各类型数量
    type_counts = {}
    for d in dialogs_list:
        t = d['type']
        type_counts[t] = type_counts.get(t, 0) + 1
    
    output = f"📋 **对话列表** (第 {page+1}/{total_pages} 页)\n"
    output += f"🔍 筛选: **{filter_type}** | 共 {len(filtered_list)} 个\n\n"
    
    if not page_items:
        output += "❌ 该分类下没有对话。"
    else:
        for i, item in enumerate(page_items, start=start+1):
            link_text = f"[🔗]({item['link']})" if item.get('link') else ""
            output += f"{i}. **{item['title']}** {link_text}\n"
            output += f"🆔 `{item['id']}` | {item.get('type', '?')}\n\n"
    
    output += "👉 复制 ID：`/download ID 数量`"
    
    # 构建分类按钮
    filter_buttons = [
        InlineKeyboardButton("全部", callback_data=f"dlg_filter_ALL_{page}"),
        InlineKeyboardButton(f"频道({type_counts.get('CHANNEL', 0)})", callback_data=f"dlg_filter_CHANNEL_{page}"),
        InlineKeyboardButton(f"群组({type_counts.get('SUPERGROUP', 0) + type_counts.get('GROUP', 0)})", callback_data=f"dlg_filter_SUPERGROUP_{page}"),
        InlineKeyboardButton(f"机器人({type_counts.get('BOT', 0)})", callback_data=f"dlg_filter_BOT_{page}"),
        InlineKeyboardButton(f"私聊({type_counts.get('PRIVATE', 0)})", callback_data=f"dlg_filter_PRIVATE_{page}"),
    ]
    
    # 翻页按钮
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"dlg_page_{filter_type}_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"dlg_page_{filter_type}_{page+1}"))
    
    keyboard = InlineKeyboardMarkup([filter_buttons, nav_buttons] if nav_buttons else [filter_buttons])
    
    await message.edit_text(output, reply_markup=keyboard, disable_web_page_preview=True)

@Client.on_callback_query(filters.regex(r"^dlg_(filter|page)_"))
async def dialogs_callback(client: Client, callback: CallbackQuery):
    """Handle pagination and filter button clicks."""
    dialogs_list = user_dialogs_cache.get(callback.from_user.id, [])
    
    if not dialogs_list:
        await callback.answer("缓存已过期，请重新发送 /recent", show_alert=True)
        return
    
    data = callback.data
    if data.startswith("dlg_filter_"):
        # Filter button: dlg_filter_TYPE_page
        parts = data.replace("dlg_filter_", "").rsplit("_", 1)
        filter_type = parts[0]
        page = 0  # Reset to first page when changing filter
    else:
        # Page button: dlg_page_TYPE_page
        parts = data.replace("dlg_page_", "").rsplit("_", 1)
        filter_type = parts[0]
        page = int(parts[1])
    
    await show_dialogs_page(callback.message, dialogs_list, page, filter_type)
    await callback.answer()

@Client.on_message(filters.command("getid") & filters.private)
async def get_chat_id(client: Client, message: Message):
    """Get chat ID from a forwarded message. 管理员专用"""
    # 管理员检查
    if message.from_user.id != client.admin_id:
        await message.reply_text("⛔ 此命令仅限管理员使用。")
        return
    
    # 检查是否回复了消息
    if message.reply_to_message:
        target = message.reply_to_message
        if target.forward_from_chat:
            chat = target.forward_from_chat
            await message.reply_text(
                f"✅ **成功获取！**\n\n"
                f"📂 **名称**: {chat.title}\n"
                f"🆔 **ID**: `{chat.id}`\n"
                f"📌 **类型**: {chat.type}"
            )
            return
        elif target.sender_chat:
            chat = target.sender_chat
            await message.reply_text(
                f"✅ **成功获取！**\n\n"
                f"📂 **名称**: {chat.title}\n"
                f"🆔 **ID**: `{chat.id}`\n"
                f"📌 **类型**: {chat.type}"
            )
            return
    
    await message.reply_text(
        "ℹ️ **使用方法**\n\n"
        "1. 从评论区或无法加入的群组**转发一条消息**给我。\n"
        "2. **回复**那条转发的消息，发送 `/getid`。\n"
        "3. 我会告诉你那个群组/频道的 ID。\n\n"
        "💡 **如果连转发都不让？**\n"
        "试试用 `/linked 频道ID` 查询主频道的评论区 ID。"
    )

@Client.on_message(filters.command("linked") & filters.private)
async def get_linked_chat(client: Client, message: Message):
    """Get linked discussion group. 管理员专用"""
    # 管理员检查
    if message.from_user.id != client.admin_id:
        await message.reply_text("⛔ 此命令仅限管理员使用。")
        return
    
    user = client.user_client
    args = message.command
    
    if len(args) < 2:
        await message.reply_text(
            "ℹ️ **用法**: `/linked 频道ID`\n\n"
            "例如：`/linked -1001234567890`\n\n"
            "这会查询某个频道关联的评论区群组 ID。\n"
            "你可以先用 `/recent` 找到主频道的 ID。"
        )
        return
    
    try:
        channel_id = int(args[1])
        status_msg = await message.reply_text("🔍 正在查询...")
        
        chat = await user.get_chat(channel_id)
        
        if chat.linked_chat:
            linked = chat.linked_chat
            await status_msg.edit_text(
                f"✅ **找到关联的评论区！**\n\n"
                f"📺 **主频道**: {chat.title}\n"
                f"🆔 主频道 ID: `{chat.id}`\n\n"
                f"💬 **评论区群组**: {linked.title}\n"
                f"🆔 评论区 ID: `{linked.id}`\n\n"
                f"👉 现在可以用：`/download {linked.id} 10`"
            )
        else:
            await status_msg.edit_text(
                f"⚠️ 频道 **{chat.title}** 没有关联评论区群组。\n\n"
                f"可能是：\n"
                f"1. 这个频道没开评论功能\n"
                f"2. 评论区是受限的"
            )
    except Exception as e:
        await message.reply_text(f"❌ 查询失败: {e}")

@Client.on_message(filters.command("download") & filters.private)
async def batch_download(client: Client, message: Message):
    """
    Batch download messages from a specific channel ID.
    Usage: /download <chat_id> <limit>
    """
    try:
        args = message.command
        if len(args) < 3:
            # 显示带目的地选择的引导提示
            await message.reply_text(
                "📥 **批量下载**\n\n"
                "**第一步：选择下载目的地**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📁 存储频道", callback_data="dl_dest_channel")],
                    [InlineKeyboardButton("⭐ 收藏夹 (Saved Messages)", callback_data="dl_dest_saved")]
                ])
            )
            return

        chat_id = int(args[1])
        limit = int(args[2])
        
        # 默认发到存储频道
        dest = user_download_dest.get(message.from_user.id, "channel")
        await do_batch_download(client, message, chat_id, limit, dest)
        
    except Exception as e:
        await message.reply_text(f"❌ 发生严重错误: {e}")

@Client.on_callback_query(filters.regex(r"^dl_dest_(channel|saved)$"))
async def download_dest_callback(client: Client, callback: CallbackQuery):
    """Handle destination selection."""
    dest = callback.data.replace("dl_dest_", "")
    user_download_dest[callback.from_user.id] = dest
    
    dest_name = "📁 存储频道" if dest == "channel" else "⭐ 收藏夹"
    
    from pyrogram.types import ForceReply
    await callback.message.edit_text(
        f"📥 **批量下载**\n\n"
        f"✅ 已选择目的地：{dest_name}\n\n"
        f"**第二步：输入来源**\n"
        f"请按格式输入：`频道ID 数量`\n"
        f"例如：`-1001234567890 10`",
        reply_markup=ForceReply(placeholder="输入: 频道ID 数量")
    )
    await callback.answer(f"已选择: {dest_name}")

async def do_batch_download(client, message, chat_id, limit, dest="channel"):
    """Core download logic."""
    user = client.user_client
    
    # 确定目的地
    from handlers.transfer import progress, humanbytes, config, db, os, time, math
    
    if dest == "saved":
        # 发送到用户的 Saved Messages，用 user client
        target_chat_id = message.from_user.id
        dest_name = "⭐ 收藏夹"
        send_client = user
    else:
        target_chat_id = config.STORAGE_CHANNEL_ID
        dest_name = "📁 存储频道"
        send_client = client
    
    status_msg = await message.reply_text(f"🚀 开始扫描频道 `{chat_id}` 的最后 {limit} 条消息...\n📍 目的地: {dest_name}")
    
    # Get history with error handling
    try:
        # 先尝试解析 peer
        try:
            await user.get_chat(chat_id)
        except:
            pass
        
        messages_to_process = []
        async for msg in user.get_chat_history(chat_id, limit=limit):
            if msg.media:
                messages_to_process.append(msg)
    except Exception as e:
        error_msg = str(e)
        if "PEER_ID_INVALID" in error_msg:
            await status_msg.edit_text(
                f"❌ 无法访问该对话！\n\n"
                f"错误: `PEER_ID_INVALID`\n\n"
                f"**这个 ID ({chat_id}) 在你的账号里找不到。**\n\n"
                f"可能原因：\n"
                f"1. 你已经删除了和这个账号的聊天记录\n"
                f"2. 这个账号从未给你发过消息\n"
                f"3. 需要先在 Telegram 里打开那个聊天"
            )
        else:
            await status_msg.edit_text(f"❌ 无法访问该频道！\n\n错误: `{e}`")
        return
    
    if not messages_to_process:
        await status_msg.edit_text("❌ 未找到包含媒体文件的消息。")
        return

    await status_msg.edit_text(f"📦 发现 {len(messages_to_process)} 个文件，准备开始搬运到 {dest_name}...")
    
    success_count = 0
    total_count = len(messages_to_process)
    
    # Process from oldest to newest (reversed)
    for index, target_msg in enumerate(reversed(messages_to_process)):
        step_msg = await message.reply_text(f"⏳ [{index+1}/{total_count}] 正在处理消息 ID: {target_msg.id}...")
        
        try:
            # Determine file name
            file_name = "unknown"
            mime_type = "unknown"
            file_size = 0
            
            if target_msg.video:
                file_name = target_msg.video.file_name or f"video_{target_msg.id}.mp4"
                mime_type = target_msg.video.mime_type
                file_size = target_msg.video.file_size
            elif target_msg.document:
                file_name = target_msg.document.file_name or f"doc_{target_msg.id}"
                mime_type = target_msg.document.mime_type
                file_size = target_msg.document.file_size
            elif target_msg.photo:
                file_name = f"photo_{target_msg.id}.jpg"
                mime_type = "image/jpeg"
                file_size = target_msg.photo.file_size
            elif target_msg.audio:
                file_name = target_msg.audio.file_name or f"audio_{target_msg.id}.mp3"
                mime_type = target_msg.audio.mime_type
                file_size = target_msg.audio.file_size
            else:
                await step_msg.edit_text(f"⚠️ 跳过：非媒体消息")
                continue

            # Download
            start_time = time.time()
            temp_dir = "downloads"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
                
            download_path = await user.download_media(
                target_msg,
                block=True,
                progress=progress,
                progress_args=(step_msg, f"⬇️ [{index+1}/{total_count}] 下载中", start_time)
            )
            
            # Upload
            start_time = time.time()
            caption = target_msg.caption or target_msg.text or ""
            
            storage_msg = None
            if target_msg.video:
                storage_msg = await send_client.send_video(target_chat_id, download_path, caption=caption, supports_streaming=True, progress=progress, progress_args=(step_msg, "⬆️ 上传中", start_time))
            elif target_msg.photo:
                storage_msg = await send_client.send_photo(target_chat_id, download_path, caption=caption, progress=progress, progress_args=(step_msg, "⬆️ 上传中", start_time))
            elif target_msg.audio:
                storage_msg = await send_client.send_audio(target_chat_id, download_path, caption=caption, progress=progress, progress_args=(step_msg, "⬆️ 上传中", start_time))
            else:
                storage_msg = await send_client.send_document(target_chat_id, download_path, caption=caption, progress=progress, progress_args=(step_msg, "⬆️ 上传中", start_time))
            
            # DB
            if storage_msg:
                new_file_id = ""
                new_file_unique_id = ""
                if storage_msg.video:
                    new_file_id = storage_msg.video.file_id
                    new_file_unique_id = storage_msg.video.file_unique_id
                elif storage_msg.document:
                    new_file_id = storage_msg.document.file_id
                    new_file_unique_id = storage_msg.document.file_unique_id
                elif storage_msg.photo:
                    new_file_id = storage_msg.photo.file_id
                    new_file_unique_id = storage_msg.photo.file_unique_id
                elif storage_msg.audio:
                    new_file_id = storage_msg.audio.file_id
                    new_file_unique_id = storage_msg.audio.file_unique_id

                db.add_file(
                    message_id=storage_msg.id,
                    chat_id=config.STORAGE_CHANNEL_ID,
                    file_id=new_file_id,
                    file_unique_id=new_file_unique_id,
                    file_name=file_name,
                    caption=caption,
                    file_size=file_size,
                    mime_type=mime_type
                )
                await step_msg.edit_text(f"✅ [{index+1}/{total_count}] 完成: {file_name}")
                success_count += 1
            
            # Cleanup
            if os.path.exists(download_path):
                os.remove(download_path)
                
        except Exception as e:
            await step_msg.edit_text(f"❌ 失败: {str(e)}")
    
    await message.reply_text(f"🎉 **批量任务结束！**\n共处理: {total_count}\n成功: {success_count}")


# ========== 合集功能 ==========

@Client.on_message(filters.command("newcollection") & filters.private)
async def create_collection_cmd(client: Client, message: Message):
    """创建新合集，自动生成密钥"""
    from database import db
    from pyrogram.types import ForceReply
    import secrets
    import string
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text(
            "📁 **创建合集**\n\n"
            "请输入合集名称：\n"
            "（例如：我的电影）",
            reply_markup=ForceReply(placeholder="输入合集名称...")
        )
        return
    
    # 直接调用带参数
    await do_create_collection(client, message, args[1])

async def do_create_collection(client, message, name):
    """创建合集的实际逻辑"""
    from database import db
    import secrets
    import string
    
    owner_id = message.from_user.id
    
    # 自动生成密钥：file_store + 16-32位随机字符
    random_length = secrets.randbelow(17) + 16
    random_chars = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(random_length))
    access_key = f"file_store{random_chars}"
    
    collection_id = db.create_collection(name, access_key, owner_id)
    
    if collection_id:
        # 进入收集模式
        user_collecting_mode[owner_id] = {
            "collection_id": collection_id,
            "collection_name": name,
            "access_key": access_key,
            "files": []
        }
        
        await message.reply_text(
            f"✅ **合集 [{name}] 创建成功！**\n\n"
            f"🔑 密钥: `{access_key}`\n\n"
            f"📥 **现在进入收集模式！**\n"
            f"• 直接发文件/链接给我\n"
            f"• 我会自动添加到这个合集\n"
            f"• 发 **结束** 完成收集\n\n"
            f"开始吧！👇"
        )
    else:
        await message.reply_text("❌ 创建失败！请重试。")

@Client.on_message(filters.command("addto") & filters.private & filters.reply)
async def add_to_collection_cmd(client: Client, message: Message):
    """添加文件到合集（需回复文件消息）"""
    from database import db
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text(
            "📁 **添加到合集**\n\n"
            "用法: 回复一条文件消息，发送 `/addto 合集名`"
        )
        return
    
    collection_name = args[1]
    owner_id = message.from_user.id
    
    collection = db.get_collection_by_name(collection_name, owner_id)
    if not collection:
        await message.reply_text(f"❌ 找不到合集 **{collection_name}**\n\n用 `/mycollections` 查看你的合集。")
        return
    
    replied = message.reply_to_message
    if not replied:
        await message.reply_text("❌ 请回复一条文件消息。")
        return
    
    file_id = None
    if replied.video:
        file_id = replied.video.file_id
    elif replied.photo:
        file_id = replied.photo.file_id
    elif replied.document:
        file_id = replied.document.file_id
    elif replied.audio:
        file_id = replied.audio.file_id
    
    if not file_id:
        await message.reply_text("❌ 回复的消息不包含文件。")
        return
    
    db.cursor.execute('SELECT id FROM files WHERE file_id = ?', (file_id,))
    row = db.cursor.fetchone()
    
    if not row:
        await message.reply_text("❌ 这个文件还没有入库。请先转发文件给机器人。")
        return
    
    if db.add_file_to_collection(collection["id"], row[0]):
        await message.reply_text(f"✅ 已添加到合集 **{collection_name}**！")
    else:
        await message.reply_text("❌ 添加失败，可能文件已在合集中。")

@Client.on_message(filters.command("mycollections") & filters.private)
async def my_collections_cmd(client: Client, message: Message):
    """查看我的合集"""
    from database import db
    
    owner_id = message.from_user.id
    collections = db.get_user_collections(owner_id)
    
    if not collections:
        await message.reply_text(
            "📁 **你还没有创建任何合集**\n\n"
            "用 `/newcollection 名称` 创建一个！"
        )
        return
    
    output = "📁 **我的合集**\n\n"
    for c in collections:
        output += f"• **{c['name']}**\n"
        output += f"  🔑 密钥: `{c['access_key']}`\n"
        output += f"  📄 文件: {c['file_count']} 个\n\n"
    
    output += "💡 分享密钥给他人，他们直接发送密钥即可获取合集。"
    await message.reply_text(output)

async def handle_collection_key(client: Client, message: Message, key: str):
    """通过密钥获取合集文件"""
    from database import db
    
    collection = db.get_collection_by_key(key)
    
    # === 情景1: 是合集密钥 ===
    if collection:
        files = db.get_collection_files(collection["id"])
        if not files:
            await message.reply_text(f"📁 合集 **{collection['name']}** 还没有文件。")
            return True
        
        status_msg = await message.reply_text(
            f"📁 **{collection['name']}**\n"
            f"共 {len(files)} 个文件，正在准备下载与解密..."
        )
        
        from pyrogram.types import InputMediaPhoto, InputMediaVideo
        import os
        import asyncio
        from services.crypto_utils import decrypt_file
        import base64
        
        media_group = []
        temp_paths = []
        storage_client = getattr(client, 'storage_client', client) # Fallback to client if storage_client missing
        
        for f in files:
            try:
                local_path = None
                is_video = False
                is_image = False
                
                mime = (f.get('mime_type') or "").lower()
                fname = (f.get('file_name') or "").lower()
                if mime.startswith('image') or fname.endswith(('.jpg', '.jpeg', '.png', '.webp', '.heic')):
                    is_image = True
                elif mime.startswith('video') or fname.endswith(('.mp4', '.mov', '.avi', '.mkv')):
                    is_video = True
                
                # 如果是加密文件或需要作为媒体发送，先下载
                # 对于加密文件，必须下载解密
                # 对于非加密媒体，为了确保能作为 InputMedia 发送(特别是原文件是Document时)，建议下载
                
                if f.get('is_encrypted'):
                    enc_msg = await storage_client.get_messages(f["chat_id"], f["message_id"])
                    if not enc_msg: continue
                    
                    try:
                        dl_path = await storage_client.download_media(enc_msg, file_name=f"temp_col_enc_{f['id']}")
                        temp_paths.append(dl_path)
                    except Exception as e:
                        print(f"Download failed: {e}")
                        continue

                    if not dl_path: continue

                    dec_path = f"temp_col_dec_{f['id']}_{f['file_name']}"
                    aes_key = base64.b64decode(f["encryption_key"])
                    
                    try:
                        await asyncio.to_thread(decrypt_file, dl_path, dec_path, aes_key)
                        local_path = dec_path
                        temp_paths.append(dec_path)
                    except Exception as e:
                        print(f"Decryption failed: {e}")
                        await message.reply_text(f"❌ 解密失败: {f['file_name']}")
                        continue
                        
                else:
                    # 非加密，但也下载以确保相册体验
                    msg = await storage_client.get_messages(f["chat_id"], f["message_id"])
                    dl_path = await storage_client.download_media(msg, file_name=f"temp_col_plain_{f['id']}")
                    local_path = dl_path
                    temp_paths.append(local_path)
                
                if not local_path or not os.path.exists(local_path):
                    continue

                caption = f['caption'] or ""
                
                if is_image:
                    media_group.append(InputMediaPhoto(local_path, caption=caption))
                elif is_video:
                    media_group.append(InputMediaVideo(local_path, caption=caption))
                else:
                    # 其他文件，清空现有媒体组后单独发送
                    if media_group:
                        await client.send_media_group(message.chat.id, media_group)
                        media_group = []
                    
                    await client.send_document(message.chat.id, local_path, caption=caption, file_name=f['file_name'])

                # 满10个发送一组
                if len(media_group) >= 10:
                    await client.send_media_group(message.chat.id, media_group)
                    media_group = []
            
            except Exception as e:
                print(f"Error processing file {f.get('id')}: {e}")
                # 即使出错也继续处理下一个
        
        # 发送剩余媒体
        if media_group:
            await client.send_media_group(message.chat.id, media_group)
            
        # 清理临时文件
        for p in temp_paths:
            if os.path.exists(p):
                try: os.remove(p)
                except: pass
        
        await status_msg.edit_text(f"✅ 合集 **{collection['name']}** 发送完成！")
        return True

    # === 情景2: 是单个文件密钥 ===
    file_info = db.get_file_by_key(key)
    if file_info:
        try:
            # 检查是否加密
            if file_info.get("is_encrypted"):
                start_time = time.time()
                status_msg = await message.reply_text(
                    f"🔐 **发现加密档案**\n"
                    f"📄 文件: `{file_info['file_name']}`\n"
                    f"⏳ 正在云端解密并提取，请稍候..."
                )
                
                # 1. 下载加密文件
                dl_path = await client.download_media(
                    file_info["file_id"],
                    file_name=f"temp_enc_{key}.bin"
                )
                
                # 2. 解密
                from services.crypto_utils import decrypt_file
                import base64
                
                decrypted_path = f"temp_dec_{key}_{file_info['file_name']}"
                aes_key = base64.b64decode(file_info["encryption_key"])
                
                await asyncio.to_thread(decrypt_file, dl_path, decrypted_path, aes_key)
                
                # 3. 发送解密后的文件
                await message.reply_document(
                    document=decrypted_path,
                    caption=f"✅ 解密成功: {file_info['file_name']}",
                    file_name=file_info['file_name']
                )
                
                # 4. 清理
                if os.path.exists(dl_path): os.remove(dl_path)
                if os.path.exists(decrypted_path): os.remove(decrypted_path)
                
                await status_msg.delete()
                
            else:
                # 普通文件直接转发
                await client.send_cached_media(
                    message.chat.id,
                    file_info["file_id"],
                    caption=file_info["caption"] or ""
                )
            return True
        except Exception as e:
            await message.reply_text(f"❌ 提取失败: {e}")
            return True

    return False


# ========== 收集模式处理 ==========

@Client.on_message(filters.regex(r"^(结束|完成|done|finish|end)$", re.IGNORECASE) & filters.private)
async def end_collecting_mode(client: Client, message: Message):
    """退出收集模式"""
    import re
    user_id = message.from_user.id
    
    if user_id not in user_collecting_mode:
        return  # 不在收集模式，忽略
    
    mode = user_collecting_mode.pop(user_id)
    file_count = len(mode["files"])
    
    await message.reply_text(
        f"✅ **收集完成！**\n\n"
        f"📁 合集: **{mode['collection_name']}**\n"
        f"📊 共收集: **{file_count}** 个文件\n"
        f"🔑 密钥: `{mode['access_key']}`\n\n"
        f"分享密钥给他人即可获取整个合集！"
    )

@Client.on_message(filters.media & filters.private)
async def media_handler(client: Client, message: Message):
    """处理收到的媒体文件 (包括转发的文件) - 自动加密存储"""
    from database import db
    import config
    
    user_id = message.from_user.id
    
    # 仅管理员可用
    if user_id != config.ADMIN_ID:
        return
    
    # 获取文件信息
    file_id = None
    file_name = "未知文件"
    file_size = 0
    
    if message.video:
        file_id = message.video.file_id
        file_name = message.video.file_name or "video.mp4"
        file_size = message.video.file_size
    elif message.photo:
        file_id = message.photo.file_id
        file_name = "photo.jpg"
        file_size = message.photo.file_size
    elif message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name or "document"
        file_size = message.document.file_size
    elif message.audio:
        file_id = message.audio.file_id
        file_name = message.audio.file_name or "audio"
        file_size = message.audio.file_size
    
    if not file_id:
        return
    
    # 检查是否在收集模式
    in_collection_mode = user_id in user_collecting_mode
    mode = user_collecting_mode.get(user_id) if in_collection_mode else None
    
    # 检查文件是否已入库
    db.cursor.execute('SELECT id, access_key FROM files WHERE file_id = ?', (file_id,))
    row = db.cursor.fetchone()
    
    if row:
        # 文件已入库
        existing_file_id = row[0]
        existing_access_key = row[1]
        
        if in_collection_mode:
            # 收集模式：添加到合集
            if db.add_file_to_collection(mode["collection_id"], existing_file_id):
                mode["files"].append(file_name)
                await message.reply_text(
                    f"✅ 已添加 `{file_name}` 到合集\n"
                    f"📊 当前: {len(mode['files'])} 个文件\n"
                    f"_(发 **结束** 完成收集)_"
                )
            else:
                await message.reply_text(f"⚠️ `{file_name}` 已在合集中")
        else:
            # 非收集模式：告知已存在
            await message.reply_text(
                f"📄 文件已存在！\n\n"
                f"📁 `{file_name}`\n"
                f"🔑 提取码: `{existing_access_key}`"
            )
        return
    
    # 文件未入库 -> 自动下载、加密、上传、入库
    status_msg = await message.reply_text(f"📥 正在处理 `{file_name}`...")
    
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    temp_file_name = f"temp_{unique_id}_{file_name}"
    
    # ...
    
    try:
        # 1. 下载文件
        # 使用唯一文件名避免冲突
        download_path = await client.download_media(message, file_name=temp_file_name)
        
        # 2. AES 加密
        from services.crypto_utils import generate_key, encrypt_file
        import base64
        import secrets
        import string
        
        aes_key = generate_key()
        aes_key_b64 = base64.b64encode(aes_key).decode('utf-8')
        
        random_name = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        encrypted_filename = f"{random_name}.bin"
        # 确保下载路径存在再操作
        if not download_path:
             raise Exception("Download failed, path is empty")
             
        encrypted_path = os.path.join(os.path.dirname(download_path), encrypted_filename)
        
        await status_msg.edit_text(f"🔒 正在加密 `{file_name}`...")
        await asyncio.to_thread(encrypt_file, download_path, encrypted_path, aes_key)
        
        # 删除原文件 (添加延时避免文件锁定)
        await asyncio.sleep(0.5)
        try:
            if os.path.exists(download_path):
                os.remove(download_path)
        except:
            pass
        
        # 3. 上传到存储频道 (优先用 Bot，失败则用闲置账号)
        await status_msg.edit_text(f"⬆️ 正在上传 `{file_name}`...")
        
        storage_msg = None
        upload_method = "Bot"
        
        # 先尝试用 Bot 上传
        try:
            storage_msg = await client.send_document(
                config.STORAGE_CHANNEL_ID,
                encrypted_path,
                caption=f"📦 {file_name}\n🔒 [AES-256 Encrypted]"
            )
        except Exception as bot_err:
            # Bot 失败，使用闲置账号
            upload_method = "存储账号"
            await status_msg.edit_text(f"⬆️ Bot上传失败，切换到存储账号...")
            storage_client = client.storage_client
            storage_msg = await storage_client.send_document(
                config.STORAGE_CHANNEL_ID,
                encrypted_path,
                caption=f"📦 {file_name}\n🔒 [AES-256 Encrypted]"
            )
        
        # 获取正确的 file_id 和 file_unique_id
        doc = storage_msg.document
        file_id_str = doc.file_id if doc else ""
        file_unique_id = doc.file_unique_id if doc else ""
        msg_id = storage_msg.id
        
        # 4. 入库
        key_length = secrets.randbelow(17) + 16
        access_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(key_length))
        
        db.add_file(
            message_id=msg_id,
            chat_id=config.STORAGE_CHANNEL_ID,
            file_id=file_id_str,
            file_unique_id=file_unique_id,
            file_name=file_name,
            caption="",
            file_size=file_size,
            mime_type="application/octet-stream",
            storage_mode='telegram_stealth',
            access_key=access_key,
            is_encrypted=True,
            encryption_key=aes_key_b64
        )
        
        # 清理加密文件
        await asyncio.sleep(0.3)
        try:
            if os.path.exists(encrypted_path):
                os.remove(encrypted_path)
        except:
            pass
        
        # 5. 如果在收集模式，添加到合集
        if in_collection_mode:
            db.cursor.execute('SELECT id FROM files WHERE access_key = ?', (access_key,))
            new_row = db.cursor.fetchone()
            if new_row:
                db.add_file_to_collection(mode["collection_id"], new_row[0])
            
            mode["files"].append(file_name)
            await status_msg.edit_text(
                f"✅ `{file_name}` 已加密入库并添加到合集\n"
                f"📊 当前: {len(mode['files'])} 个文件\n"
                f"🔑 提取码: `{access_key}`\n"
                f"_(发 **结束** 完成收集)_"
            )
        else:
            # 非收集模式：返回提取码 + 可选添加到合集
            # 获取现有合集列表
            collections = db.get_user_collections(config.ADMIN_ID)
            
            # 构建按钮
            buttons = []
            for c in collections[:5]:  # 最多显示5个
                buttons.append([InlineKeyboardButton(
                    f"📁 {c['name']}", 
                    callback_data=f"addcol_{access_key}_{c['id']}"
                )])
            buttons.append([InlineKeyboardButton(
                "➕ 新建合集", 
                callback_data=f"newcol_{access_key}"
            )])
            buttons.append([InlineKeyboardButton(
                "❌ 不添加", 
                callback_data=f"skipcol_{access_key}"
            )])
            
            await status_msg.edit_text(
                f"✅ **已加密存储！**\n\n"
                f"📄 文件: `{file_name}`\n"
                f"🔑 提取码: `{access_key}`\n\n"
                f"**添加到哪个合集？**",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        await status_msg.edit_text(f"❌ 处理失败: {e}")


# ========== 合集选择回调 ==========

# 临时存储等待新合集名称的用户
user_pending_newcol = {}  # {user_id: access_key}

@Client.on_callback_query(filters.regex(r"^addcol_"))
async def add_to_collection_callback(client: Client, callback: CallbackQuery):
    """添加文件到现有合集"""
    from database import db
    
    parts = callback.data.split("_")
    access_key = parts[1]
    collection_id = int(parts[2])
    
    # 获取文件 ID
    db.cursor.execute('SELECT id FROM files WHERE access_key = ?', (access_key,))
    row = db.cursor.fetchone()
    if row:
        db.add_file_to_collection(collection_id, row[0])
        await callback.message.edit_text(
            f"✅ 已添加到合集！\n\n"
            f"🔑 提取码: `{access_key}`"
        )
    else:
        await callback.answer("❌ 文件未找到", show_alert=True)

@Client.on_callback_query(filters.regex(r"^newcol_"))
async def new_collection_callback(client: Client, callback: CallbackQuery):
    """创建新合集并添加文件"""
    access_key = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    user_pending_newcol[user_id] = access_key
    
    await callback.message.edit_text(
        f"✅ 文件已保存！\n\n"
        f"🔑 提取码: `{access_key}`\n\n"
        f"📝 **请输入新合集的名称：**"
    )
    await callback.answer()

@Client.on_callback_query(filters.regex(r"^skipcol_"))
async def skip_collection_callback(client: Client, callback: CallbackQuery):
    """跳过添加合集"""
    access_key = callback.data.split("_")[1]
    
    await callback.message.edit_text(
        f"✅ **已加密存储！**\n\n"
        f"🔑 提取码: `{access_key}`\n\n"
        f"发送提取码即可解密获取文件"
    )

@Client.on_message(filters.text & filters.private, group=-1)
async def pending_collection_name_handler(client: Client, message: Message):
    """处理等待中的新合集名称输入"""
    from database import db
    import config
    
    user_id = message.from_user.id
    
    if user_id not in user_pending_newcol:
        message.continue_propagation()  # 让其他处理器处理
    
    if user_id != config.ADMIN_ID:
        message.continue_propagation()
    
    access_key = user_pending_newcol.pop(user_id)
    collection_name = message.text.strip()
    
    # 创建合集
    import secrets
    import string
    random_chars = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    col_access_key = f"col_{random_chars}"
    
    collection_id = db.create_collection(collection_name, col_access_key, user_id)
    
    if collection_id:
        # 添加文件到合集
        db.cursor.execute('SELECT id FROM files WHERE access_key = ?', (access_key,))
        row = db.cursor.fetchone()
        if row:
            db.add_file_to_collection(collection_id, row[0])
        
        await message.reply_text(
            f"✅ **已创建合集并添加文件！**\n\n"
            f"📁 合集: **{collection_name}**\n"
            f"🔑 合集密钥: `{col_access_key}`\n"
            f"📄 文件提取码: `{access_key}`"
        )
    else:
        await message.reply_text("❌ 创建合集失败")

