# 核心功能：下载、合集、文件处理
# 注意：中间件已迁移到 middleware.py

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeChat, BotCommandScopeAllPrivateChats, BotCommandScopeDefault, ReplyKeyboardMarkup, KeyboardButton
import asyncio
import time
import re
import os
from pyrogram.types import Message as PyrogramMessage
from database import db

print("🔁 Loading Handler: tools.py")

# ========== Rate Limiting ==========
RATE_LIMIT_DATA = {}  # {uid: [timestamp1, timestamp2, ...]}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_COUNT = 30   # 30 requests per 60s
RATE_LIMIT_BAN_DURATION = 180  # 3 minutes

# ========== Middleware (Global Terms Check, Priority -10) ==========
@Client.on_message(filters.private, group=-10)
async def terms_middleware(client: Client, message: Message):
    if message.from_user.is_bot:
        return

    uid = message.from_user.id
    import time
    from database import db
    from datetime import datetime
    
    # --- 1. Rate Limiting Check ---
    # (Checking before DB to allow DB-free blocking? No, check DB ban first usually?
    # User said "10 req in 60s -> Ban". If already banned, don't count?
    # Actually, check ban first. If unbanned spammer, THEN ban.)
    
    # However, existing code checks ban at step 0.
    # I will keep Ban Check first.
    
    # ... Existing Ban Check implementation needs Update to show Reason ...
    # This runs BEFORE session check. Banned users cannot interact.
    from database import db
    from datetime import datetime
    
    user_status = db.get_user(message.from_user.id)
    if user_status:
        # Check Ban
        if user_status.get('status') == 'banned':
            ban_until = user_status.get('ban_until')
            is_banned = False
            
            if ban_until:
                # Handle String format from SQLite
                if isinstance(ban_until, str):
                    try:
                        ban_until = datetime.fromisoformat(ban_until)
                    except: pass
                
                if isinstance(ban_until, datetime):
                    if ban_until > datetime.now():
                        is_banned = True
                else:
                    # Permanent or invalid? Assume banned if status is banned
                    is_banned = True
            else:
                 is_banned = True # Status is banned but no time? Permanent.

            if is_banned:
                expiry_str = ban_until.strftime('%Y-%m-%d %H:%M') if isinstance(ban_until, datetime) else "永久"
                reason_str = user_status.get('ban_reason') or "违反规则"
                
                await message.reply_text(
                    f"🚫 **您已被封禁**\n\n"
                    f"原因: {reason_str}\n"
                    f"解封: {expiry_str}", 
                    quote=True
                )
                message.stop_propagation()
                return
    
    # --- Rate Limiting Logic (For Non-Admin Active Users) ---
    # Admin is exempt from rate limiting
    from config import ADMIN_ID
    if uid == ADMIN_ID:
        # Admin bypass rate limit
        pass
    else:
        now = time.time()
        history = RATE_LIMIT_DATA.get(uid, [])
        # Filter 60s window
        history = [t for t in history if now - t < RATE_LIMIT_WINDOW]
        history.append(now)
        RATE_LIMIT_DATA[uid] = history
        
        if len(history) > RATE_LIMIT_COUNT:
             # Ban User
             from datetime import timedelta
             duration = 180 # 3 mins
             until = datetime.now() + timedelta(seconds=duration)
             until_str = until.strftime('%Y-%m-%d %H:%M:%S')
             reason = f"频次限制 ({RATE_LIMIT_COUNT}/{RATE_LIMIT_WINDOW}s)"
             
             db.set_user_ban(uid, "banned", until_str, reason)
             
             # Clear history
             RATE_LIMIT_DATA.pop(uid, None)
             
             await message.reply_text(f"🚫 **操作过快**\n\n已触发频次限制 ({RATE_LIMIT_COUNT}次/{RATE_LIMIT_WINDOW}秒)。\n封禁 3分钟。")
             message.stop_propagation()
             return

    from handlers.session import is_session_active, activate_session
    uid = message.from_user.id
    agree_text = "✅ 我已阅读并同意用户协议"
    start_btn_text = "🚀 开始使用"

    # 1. Check Agreement Click (Transition Stage 2 -> 3)
    if message.text == agree_text:
        # Activate Session
        activate_session(uid)
        db.update_user_terms(uid, True)
        
        await message.reply_text("✅ **协议已签署**\n\n身份验证通过，正在进入系统...", reply_markup=None)
        # Send Main Menu
        from handlers.setup import send_main_menu
        await send_main_menu(client, message)
        
        # Stop propagation
        message.stop_propagation()
        return

    # 2. Check Session Active (Stage 3+)
    if is_session_active(uid):
        message.continue_propagation()
        return

    # 3. Check Start Click (Transition Stage 1 -> 2)
    if message.text == start_btn_text:
        disclaimer_text = (
            "📜 **用户服务协议与免责声明**\n\n"
            "欢迎使用本个人数据管理工具。在使用本服务前，请您务必仔细阅读并理解以下条款：\n\n"
            "**1. 服务定义**\n"
            "本机器人仅为基于 Telegram 平台的第三方数据索引与加密辅助工具。我们不提供任何形式的内容托管、版权分发或互联网接入服务。所有文件实体均由用户自行存储于 Telegram 官方服务器。\n\n"
            "**2. 数据安全与隐私**\n"
            "您的数据索引采用私有化加密存储。用户需自行妥善保管提取码、访问密钥及个人账号。因用户操作不当（如泄露密钥）、设备丢失或 Telegram 平台政策调整导致的数据不可访问，开发者不承担恢复义务与赔偿责任。\n\n"
            "**3. 用户行为规范**\n"
            "用户承诺严禁利用本工具存储、传播以下内容：\n"
            "• 淫秽、色情、赌博、暴力、恐怖主义等违法信息；\n"
            "• 侵犯他人知识产权（版权、商标权）的内容；\n"
            "• 违反用户所在地法律法规或 Telegram 平台公约的其他内容。\n\n"
            "**4. 免责声明**\n"
            "• 本工具按「现状」提供，开发者不对服务的及时性、安全性、准确性作担保。\n"
            "• 对于因不可抗力、黑客攻击、系统不稳定或第三方服务（Telegram）故障导致的服务中断，开发者不承担责任。\n"
            "• 若发现违规用途，我们保留在不通知的情况下配合执法机关进行封禁账号、删除索引或上报数据的权利。\n\n"
            "🔴 **点击下方按钮即表示您已完整阅读并认可上述所有条款。**"
        )
        await message.reply_text(
            disclaimer_text,
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(agree_text)]], 
                resize_keyboard=True, 
                one_time_keyboard=False, 
                is_persistent=True,
                placeholder="请点击同意以继续..."
            ),
            quote=True
        )
        message.stop_propagation()
        return

    # 4. Default / Initial State (Stage 1)
    # User sent /start or anything else, but NO session and NO specific button click.
    # Show "Start Menu" (Highest Level)
    welcome_text = (
        "👋 **欢迎来到私人文件保险箱**\n\n"
        "您目前处于 **未登录/会话过期** 状态。\n"
        "为了保障您的数据安全与合规使用，我们需要进行简单的身份确认。\n\n"
        "👉 请点击下方按钮开始流程。"
    )
    await message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(start_btn_text)]],
            resize_keyboard=True,
            one_time_keyboard=False,
            is_persistent=True,
            placeholder="点击开始..."
        )
    )
    message.stop_propagation()


# 全局存储
user_dialogs_cache = {}
user_download_dest = {}
user_last_action = {}  # 频率限制：记录用户上次操作时间
user_collecting_mode = {}  # 收集模式：{user_id: {"collection_id": xxx, "collection_name": xxx, "files": []}}
user_last_collection = {}  # 最后一次使用的合集 {user_id: {'id': id, 'name': name}}
media_group_states = {} # {media_group_id: {'msg': Message, 'keys': [], 'bound_col_id': None, 'bound_col_name': None, 'count': 0, 'last_update': 0}}
user_interaction_state = {} # 用户交互状态: {user_id: "status_string"}
user_pending_file = {} # 用于存储待处理的文件信息，例如在创建合集时

from datetime import datetime, timedelta

# User Request History for Rate Limiting
user_request_history = {}

async def check_auth(client, message):
    """
    统一权限验证 (Auth + Rate Limit)
    1. 记录/更新用户信息
    2. 检查封禁状态
    3. 检查频率限制 (60s > 10次 -> 封禁1天)
    """
    user = message.from_user
    if not user: return False
    
    # 0. 更新用户资料
    db.update_user(user.id, user.username, user.first_name)
    
    # 1. 管理员豁免
    if user.id == client.admin_id:
        return True
    
    # 2. 检查封禁
    u_data = db.get_user(user.id)
    if u_data and u_data['status'] == 'banned':
        await message.reply_text("⛔ **你已被封禁**\n请联系管理员解封。")
        return False
        
    # 3. 频率限制 (60s 滑动窗口)
    now = time.time()
    history = user_request_history.get(user.id, [])
    # 清理过期记录
    history = [t for t in history if now - t < 60]
    
    # 判定
    if len(history) >= 10:
        # 触发自动封禁
        ban_until = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        db.set_user_ban(user.id, 'banned', ban_until)
        await message.reply_text("⛔ **请求过于频繁！**\n系统已自动封禁你 1 天。")
        return False
        
    history.append(now)
    user_request_history[user.id] = history
    return True

# Admin Commands
@Client.on_message(filters.command("users") & filters.private)
async def list_users(client, message):
    if message.from_user.id != client.admin_id: return
    users = db.get_all_users()
    text = f"👥 **用户列表 ({len(users)})**\n\n"
    for u in users:
        status_icon = "🔴" if u['status'] == 'banned' else "🟢"
        text += f"{status_icon} `{u['id']}` {u['first_name']} (@{u['username']})\n"
    await message.reply_text(text)

@Client.on_message(filters.command("ban") & filters.private)
async def ban_user_cmd(client, message):
    if message.from_user.id != client.admin_id: return
    try:
        target_id = int(message.command[1])
        db.set_user_ban(target_id, 'banned', "9999-12-31")
        await message.reply_text(f"🔴 已封禁用户 `{target_id}`")
    except:
        await message.reply_text("用法: `/ban 用户ID`")

@Client.on_message(filters.command("unban") & filters.private)
async def unban_user_cmd(client, message):
    if message.from_user.id != client.admin_id: return
    try:
        target_id = int(message.command[1])
        db.set_user_ban(target_id, 'active')
        await message.reply_text(f"🟢 已解封用户 `{target_id}`")
    except:
        await message.reply_text("用法: `/unban 用户ID`")

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
    
    # 权限检查
    if message.from_user.id != client.admin_id:
        return

    args = message.command or []
    
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
    
    # 处理下载回复 (匹配新旧两种提示格式)
    elif ("频道ID" in prompt_text and "数量" in prompt_text) or "请按格式输入" in prompt_text:
        parts = message.text.strip().split()
        if len(parts) >= 2:
            try:
                chat_id = int(parts[0])
                limit = int(parts[1])
                dest = user_download_dest.get(message.from_user.id, "channel")
                await do_batch_download(client, message, chat_id, limit, dest)
            except ValueError:
                await message.reply_text("❌ 格式错误！请输入：`频道ID 数量`\n例如：`-1001234567890 10`")
        else:
            await message.reply_text("❌ 格式错误！请输入：`频道ID 数量`\n例如：`-1001234567890 10`")
    
    # 处理创建合集回复
    elif "请输入合集名称" in prompt_text:
        collection_name = message.text.strip()
        if collection_name:
            await do_create_collection(client, message, collection_name)

async def do_search(client, message, keyword):
    """Perform the actual search."""
    # Search is still ADMIN ONLY (uses user_client) - or switch to storage?
    # User didn't ask to open search. But asked to manage users.
    # Keep user_client for Admin Search.
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
    # 权限检查 (开放给所有用户)
    if not await check_auth(client, message):
        return
    
    # 1. 检查是否有参数 (链接/用户名)
    if len(message.command) > 1:
        text = message.command[1]
        
        # A. 私有频道链接 t.me/c/12345/678
        import re
        match_private = re.search(r"t\.me/c/(\d+)", text)
        if match_private:
            id_part = match_private.group(1)
            full_id = int(f"-100{id_part}")
            await message.reply_text(
                f"✅ **通过链接解析**\n\n"
                f"🔗 **链接**: `{text}`\n"
                f"🆔 **ID**: `{full_id}`\n"
                f"📌 **类型**: 私有频道/群组 (计算推断)"
            )
            return

        # B. 公开用户名/链接 t.me/username
        username = None
        if "t.me/" in text:
            # t.me/username/123 -> username
            parts = text.split("t.me/")
            if len(parts) > 1:
                sub = parts[1].split("/")[0]
                if sub and not sub.startswith("c"):
                    username = sub
        elif text.startswith("@"):
            username = text[1:]
        elif not text.startswith("-100"): # not an ID
            username = text

        if username:
            try:
                chat = await client.get_chat(username)
                await message.reply_text(
                    f"✅ **成功获取！**\n\n"
                    f"📂 **名称**: {chat.title}\n"
                    f"🆔 **ID**: `{chat.id}`\n"
                    f"🔗 **Username**: @{chat.username}\n"
                    f"📌 **类型**: {chat.type}"
                )
                return
            except Exception as e:
                await message.reply_text(f"❌ 无法解析用户名: {e}")
                return

    # 2. 检查是否回复了消息
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
        "1. **回复**一条转发消息发送 `/getid`\n"
        "2. 发送 `/getid 链接` (支持 t.me/c/xxxxx)\n"
        "3. 发送 `/getid @用户名`\n\n"
        "💡 **如果连链接都没有？**\n"
        "试试用 `/linked 频道ID` 查询关联群组。"
    )

@Client.on_message(filters.command("linked") & filters.private)
async def get_linked_chat(client: Client, message: Message):
    """Get linked discussion group. 管理员专用"""
    # 管理员检查
    # 权限检查 (开放给所有用户)
    if not await check_auth(client, message):
        return
    
    # Use Storage Client (Idle Account) for safety
    user = client.storage_client
    args = message.command
    
    if len(args) < 2:
        await message.reply_text(
            "ℹ️ **用法**: `/linked 频道ID`\n\n"
            "例如：`/linked -1001234567890`\n\n"
            "这会查询某个频道关联的评论区群组 ID。\n"
            "你可以先用 `/recent` 找到主频道的 ID。"
        )
        return
    
    channel_id = 0
    try:
        channel_id = int(args[1])
        status_msg = await message.reply_text("🔍 正在查询...")
        
        # 1. Try with Storage Client (Protect Privacy)
        chat = None
        try:
            chat = await client.storage_client.get_chat(channel_id)
        except Exception as e:
            # 2. Fallback for Admin: Try with User Client
            if message.from_user.id == client.admin_id:
                try:
                    chat = await client.user_client.get_chat(channel_id)
                except:
                    raise e # Re-raise original or new error
            else:
                raise e

        if chat.linked_chat:
            linked = chat.linked_chat
            await status_msg.edit_text(
                f"✅ **找到关联的评论区！**\n\n"
                f"📺 **主频道**: {chat.title}\n"
                f"🆔 主频道 ID: `{chat.id}`\n\n"
                f"💬 **评论区群组**: {linked.title}\n"
                f"🆔 评论区 ID: `{linked.id}`\n\n"
                f"👉 复制评论区 ID，然后：`/download {linked.id} 10`\n"
                f"💡 **提示**: 此操作无需加入群组，不会触发进群封禁。"
            )
        else:
            await status_msg.edit_text(
                f"⚠️ 频道 **{chat.title}** 没有关联评论区群组。\n\n"
                f"可能是：\n"
                f"1. 这个频道没开评论功能\n"
                f"2. 评论区是受限的 (Bot 看不到)"
            )
    except Exception as e:
        await message.reply_text(f"❌ 查询失败: {e}\n\n若是私密频道，请确保 '闲置账号' 在频道内。")

@Client.on_message(filters.command("download") & filters.private)
async def batch_download(client: Client, message: Message):
    """
    Batch download messages from a specific channel ID.
    Usage: /download <chat_id> <limit>
    """
    # 权限检查
    if not await check_auth(client, message):
        return

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
    # Use User Client (Admin's account) for downloading
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
        scan_count = 0
        # Scan up to 500 messages or 10x the limit to find media
        max_scan = max(500, limit * 10)
        
        async for msg in user.get_chat_history(chat_id):
            scan_count += 1
            if msg.media:
                messages_to_process.append(msg)
            
            if len(messages_to_process) >= limit:
                break
            
            if scan_count >= max_scan:
                break
                
    except Exception as e:
        error_msg = str(e)
        from handlers.setup import get_main_menu_keyboard
        is_adm = message.from_user.id == client.admin_id
        
        # Try to delete status message to clean up
        try: await status_msg.delete()
        except: pass
        
        if "PEER_ID_INVALID" in error_msg:
            await message.reply_text(
                f"❌ 无法访问该对话！\n\n"
                f"错误: `PEER_ID_INVALID`\n\n"
                f"**这个 ID ({chat_id}) 在你的账号里找不到。**\n\n"
                f"可能原因：\n"
                f"1. 你已经删除了和这个账号的聊天记录\n"
                f"2. 这个账号从未给你发过消息\n"
                f"3. 需要先在 Telegram 里打开那个聊天",
                reply_markup=get_main_menu_keyboard(is_adm)
            )
        else:
            await message.reply_text(f"❌ 无法访问该频道！\n\n错误: `{e}`", reply_markup=get_main_menu_keyboard(is_adm))
        return
    
    if not messages_to_process:
        from handlers.setup import get_main_menu_keyboard
        is_adm = message.from_user.id == client.admin_id
        try: await status_msg.delete()
        except: pass
        await message.reply_text(f"❌ 未找到包含媒体文件的消息 (已扫描 {scan_count} 条)。", reply_markup=get_main_menu_keyboard(is_adm))
        return

    # Initialize Dashboard
    dashboard_msg = await status_msg.edit_text(
        f"🚀 **批量下载任务启动**\n"
        f"📦 目标: `{dest_name}`\n"
        f"📊 进度: 0/{len(messages_to_process)}\n"
        f"⏳ 正在初始化..."
    )
    
    import secrets
    import string
    import base64
    from services.crypto_utils import generate_key, encrypt_file
    
    success_count = 0
    fail_count = 0
    total_count = len(messages_to_process)
    
    # Process from oldest to newest
    for index, target_msg in enumerate(reversed(messages_to_process)):
        current_idx = index + 1
        
        try:
            # Determine file name & Update Dashboard
            file_name = "unknown"
            file_size = 0
            
            if target_msg.video:
                file_name = target_msg.video.file_name or f"video_{target_msg.id}.mp4"
                file_size = target_msg.video.file_size
            elif target_msg.document:
                file_name = target_msg.document.file_name or f"doc_{target_msg.id}"
                file_size = target_msg.document.file_size
            elif target_msg.photo:
                file_name = f"photo_{target_msg.id}.jpg"
                file_size = target_msg.photo.file_size
            elif target_msg.audio:
                file_name = target_msg.audio.file_name or f"audio_{target_msg.id}.mp3"
                file_size = target_msg.audio.file_size
            else:
                continue

            try:
                await dashboard_msg.edit_text(
                    f"🚀 **批量下载任务**\n"
                    f"📦 目标: `{dest_name}`\n"
                    f"🔄 正在处理: `{file_name}`\n"
                    f"📊 进度: {current_idx}/{total_count} | ✅ {success_count} | ❌ {fail_count}"
                )
            except: pass

            # 1. Download
            temp_dir = config.TEMP_DOWNLOAD_DIR
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)
                
            dl_path = await user.download_media(target_msg, file_name=os.path.join(temp_dir, file_name))
            
            if not dl_path:
                fail_count += 1
                continue

            # 2. Encrypt
            aes_key = generate_key()
            aes_key_b64 = base64.b64encode(aes_key).decode('utf-8')
            
            random_name = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
            enc_path = os.path.join(os.path.dirname(dl_path), f"{random_name}.bin")
            
            await asyncio.to_thread(encrypt_file, dl_path, enc_path, aes_key)
            
            # Clean raw file
            try: os.remove(dl_path)
            except: pass
            
            # 3. Upload (Dual)
            caption = f"📦 {file_name}\n🔒 [AES-256 Encrypted]"
            
            # Primary Upload
            primary_msg = await send_client.send_document(
                config.STORAGE_CHANNEL_ID,
                enc_path,
                caption=caption
            )
            
            # Backup Upload
            backup_msg_id = 0
            backup_chat_id = 0
            if config.BACKUP_CHANNEL_ID and config.BACKUP_CHANNEL_ID != 0:
                try:
                    # Prefer using storage_client for backup if possible, or same client
                    backup_uploader = client.storage_client if hasattr(client, 'storage_client') else send_client
                    b_msg = await backup_uploader.send_document(
                        config.BACKUP_CHANNEL_ID,
                        enc_path, 
                        caption=caption + " [Backup]"
                    )
                    backup_msg_id = b_msg.id
                    backup_chat_id = config.BACKUP_CHANNEL_ID
                except Exception as e:
                    print(f"Backup upload failed: {e}")
            
            # 4. DB Record
            key_length = secrets.randbelow(17) + 16
            access_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(key_length))
            
            if primary_msg and primary_msg.document:
                db.add_file(
                    message_id=primary_msg.id,
                    chat_id=config.STORAGE_CHANNEL_ID,
                    file_id=primary_msg.document.file_id,
                    file_unique_id=primary_msg.document.file_unique_id,
                    file_name=file_name,
                    caption="",
                    file_size=file_size,
                    mime_type="application/octet-stream",
                    storage_mode='telegram_stealth',
                    access_key=access_key,
                    is_encrypted=True,
                    encryption_key=aes_key_b64,
                    backup_message_id=backup_msg_id,
                    backup_chat_id=backup_chat_id
                )
                success_count += 1
            else:
                fail_count += 1
            
            # Clean enc file
            try: os.remove(enc_path)
            except: pass
            
        except Exception as e:
            fail_count += 1
            print(f"Batch file error: {e}")
            
    await dashboard_msg.edit_text(
        f"✅ **批量任务结束**\n"
        f"📊 总数: {total_count}\n"
        f"✅ 成功: {success_count}\n"
        f"❌ 失败: {fail_count}\n"
        f"📂 所有文件已加密存入保险箱。"
    )
    
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
    
    # Handle Button Trigger
    if message.text == "🆕 新建合集" or len(args) < 2:
        await message.reply_text(
            "📁 **创建合集**\n\n"
            "请输入合集名称：\n"
            "（例如：我的电影）\n\n"
            "💡 发送 /cancel 可取消",
            reply_markup=ForceReply(placeholder="输入合集名称...")
        )
        return
    
    # Check if args[0] is command (ignore /newcollection)
    # If standard command: /newcollection Name -> args[1] = Name
    # If triggered by text button? "🆕 新建合集" handled above.
    
    collection_name = args[1]
    
    # Do Create
    await do_create_collection(client, message, collection_name)

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
        # 进入收集模式
        sent_msg = await message.reply_text(
            f"✅ **合集 [{name}] 创建成功！**\n\n"
            f"🔑 密钥: `{access_key}`\n\n"
            f"📥 **现在进入收集模式！**\n"
            f"• 直接批量转发文件给我\n"
            f"• 我会静默添加到此合集\n"
            f"• 状态将实时更新在此消息中\n"
            f"• 发 **结束** 完成收集\n\n"
            f"⏳ 等待文件..."
        )
        
        user_collecting_mode[owner_id] = {
            "collection_id": collection_id,
            "collection_name": name,
            "access_key": access_key,
            "files": [],
            "status_msg_id": sent_msg.id,
            "status_chat_id": sent_msg.chat.id,
            "success": 0,
            "total": 0,
            "last_update": 0
        }
    else:
        await message.reply_text("❌ 创建失败！请重试。")

@Client.on_message(filters.regex(r"^(结束|finish|完成)$", re.IGNORECASE) & filters.private)
async def finish_collection_cmd(client: Client, message: Message):
    """结束收集模式"""
    user_id = message.from_user.id
    if user_id in user_collecting_mode:
        mode = user_collecting_mode.pop(user_id)
        
        # 最终汇总
        try:
            # 尝试更新 Dashboard 为最终状态
            await client.edit_message_text(
                chat_id=mode['status_chat_id'],
                message_id=mode['status_msg_id'],
                text=(
                    f"✅ **合集 [{mode['collection_name']}] 收集完成！**\n\n"
                    f"📊 总共: {mode['total']} | ✅ 成功: {mode['success']} | ❌ {mode['fail']}\n"
                    f"🔑 密钥: `{mode['access_key']}`"
                )
            )
        except: pass
        
        await message.reply_text(
            f"🎉 **任务结束！**\n"
            f"已退出收集模式。"
        )

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
    # === Terms Check ===
    from database import db
    user = db.get_user(message.from_user.id)
    # 强制显示免责声明 (如果未接受 OR 用户读取失败)
    if not user or not user.get('accepted_terms'):
        s_text = (
            "📜 **免责声明 (Disclaimer)**\n\n"
            "1. 本机器人仅用于个人数据备份与管理，代码开源且透明。\n"
            "2. 用户需自行承担使用本工具产生的一切后果。\n"
            "3. 请勿利用本工具存储或传播任何违反当地法律法规的内容。\n\n"
            "点击下方按钮代表你已阅读并同意以上条款。"
        )
        # Assuming InlineKeyboardMarkup and InlineKeyboardButton are imported or available
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await message.reply_text(
            s_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ 我已阅读并同意", callback_data="accept_terms")]
            ])
        )
        return
    
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

async def send_collection_files(client: Client, message: Message, files: list, collection_name: str, edit_msg=None):
    """
    发送合集文件（核心逻辑抽离）
    优化：使用临时目录，每发送一批就立即清理，防止磁盘爆满
    """
    import config
    
    if edit_msg:
        status_msg = edit_msg
        await status_msg.edit_text(f"📁 **{collection_name}**\n准备发送 {len(files)} 个文件...")
    else:
        status_msg = await message.reply_text(
            f"📁 **{collection_name}**\n"
            f"共 {len(files)} 个文件，正在准备下载与解密..."
        )
    
    from pyrogram.types import InputMediaPhoto, InputMediaVideo
    import os
    import asyncio
    from services.crypto_utils import decrypt_file
    import base64
    
    # 使用临时目录
    temp_dir = getattr(config, 'TEMP_DOWNLOAD_DIR', './temp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir, exist_ok=True)
    
    media_group = []
    batch_temp_paths = []  # 当前批次的临时文件
    storage_client = getattr(client, 'storage_client', client)
    sent_count = 0
    
    async def cleanup_batch(paths):
        """清理一批临时文件"""
        for p in paths:
            if p and os.path.exists(p):
                try: os.remove(p)
                except: pass
    
    async def send_and_cleanup_batch():
        """发送当前媒体组并清理临时文件"""
        nonlocal media_group, batch_temp_paths, sent_count
        if media_group:
            await client.send_media_group(message.chat.id, media_group)
            sent_count += len(media_group)
            media_group = []
        # 立即清理本批次临时文件
        await cleanup_batch(batch_temp_paths)
        batch_temp_paths = []
    
    for idx, f in enumerate(files):
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
            
            if f.get('is_encrypted'):
                enc_msg = await storage_client.get_messages(f["chat_id"], f["message_id"])
                
                is_valid = enc_msg and not enc_msg.empty and enc_msg.document
                
                if not is_valid:
                    b_cid = f.get('backup_chat_id', 0)
                    b_mid = f.get('backup_message_id', 0)
                    if b_cid and b_mid:
                         try:
                             enc_msg = await storage_client.get_messages(b_cid, b_mid)
                         except: pass

                if not enc_msg or enc_msg.empty: continue
                
                try:
                    dl_path = await storage_client.download_media(enc_msg, file_name=os.path.join(temp_dir, f"enc_{f['id']}"))
                    batch_temp_paths.append(dl_path)
                except: continue

                if not dl_path: continue

                dec_path = os.path.join(temp_dir, f"dec_{f['id']}_{f['file_name']}")
                aes_key = base64.b64decode(f["encryption_key"])
                
                try:
                    await asyncio.to_thread(decrypt_file, dl_path, dec_path, aes_key)
                    local_path = dec_path
                    batch_temp_paths.append(dec_path)
                except: continue
                    
            else:
                msg = await storage_client.get_messages(f["chat_id"], f["message_id"])
                dl_path = await storage_client.download_media(msg, file_name=os.path.join(temp_dir, f"plain_{f['id']}"))
                local_path = dl_path
                batch_temp_paths.append(local_path)
            
            if not local_path or not os.path.exists(local_path):
                continue

            caption = f['caption'] or ""
            
            if is_image:
                media_group.append(InputMediaPhoto(local_path, caption=caption))
            elif is_video:
                media_group.append(InputMediaVideo(local_path, caption=caption))
            else:
                # 文档：先发送当前媒体组，再单独发送文档
                await send_and_cleanup_batch()
                await client.send_document(message.chat.id, local_path, caption=caption, file_name=f['file_name'])
                sent_count += 1
                # 单独清理这个文档的临时文件
                await cleanup_batch([local_path])

            # 每10个媒体项发送一批并立即清理
            if len(media_group) >= 10:
                await send_and_cleanup_batch()
        
        except Exception as e:
            print(f"Error processing file {f.get('id')}: {e}")
    
    # 发送剩余的媒体组
    await send_and_cleanup_batch()
        
    await status_msg.edit_text(f"✅ 合集 **{collection_name}** 发送完成！共 {sent_count} 个文件。")
    return status_msg

def make_pagination_keyboard(total_pages, current_page, callback_prefix, extra_buttons=None):
    """
    生成分页键盘 (10页一组)
    callback_prefix: 例如 "col_pg_KEY_" (后面接页码)
    """
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = []
    
    # 1. 功能按钮 (放在最上面)
    if extra_buttons:
        for btn_row in extra_buttons:
            buttons.append(btn_row)

    # 2. 翻页导航 (Prev/Next)
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"{callback_prefix}{current_page-1}"))
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"{callback_prefix}{current_page+1}"))
    if nav_row:
        buttons.append(nav_row)
        
    # 3. 页码网格 (10页)
    # 计算当前显示的10页范围 (例如 Page 1 -> 1-10)
    start_num = ((current_page - 1) // 10) * 10 + 1
    end_num = min(start_num + 9, total_pages)
    
    page_buttons = []
    row = []
    for p in range(start_num, end_num + 1):
        # 高亮当前页
        text = f"· {p} ·" if p == current_page else str(p)
        row.append(InlineKeyboardButton(text, callback_data=f"{callback_prefix}{p}"))
        if len(row) == 5:
            page_buttons.append(row)
            row = []
    if row:
        page_buttons.append(row)
            
    buttons.extend(page_buttons)
            
    return InlineKeyboardMarkup(buttons)

async def show_collection_page(client, message, collection, files, page=1, is_callback=False, send_new=False):
    """显示合集的分页内容 (Smart Pagination)
    :param send_new: 如果为 True，强制发送新消息（用于 Floating Menu 效果）
    """
    from pyrogram.types import InlineKeyboardButton
    
    per_page = 10
    total_files = len(files)
    total_pages = max(1, (total_files + per_page - 1) // per_page)
    
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_files = files[start_idx:end_idx]
    
    # 1. 构建文本内容 (精简版)
    text = f"📁 **{collection['name']}**\n"
    text += f"📊 共 {total_files} 个文件 (第 {page}/{total_pages} 页)\n"
    text += f"-------------------------\n"
    text += f"🔑 提取码: `{collection['access_key']}`"

    # 2. 构建按钮 (使用 Smart Pagination)
    extra_btns = []
    # 发送本页
    extra_btns.append([InlineKeyboardButton(f"⬇️ 发送本页 ({len(page_files)}个)", callback_data=f"col_dl_{collection['access_key']}_{page}")])
    # 发送全部 (智能: 发送剩余)
    remaining_count = max(0, total_files - 10)
    if remaining_count > 0:
        extra_btns.append([InlineKeyboardButton(f"🚀 发送剩余 ({remaining_count}个 - 慎点)", callback_data=f"col_all_{collection['access_key']}")])
    
    keyboard = make_pagination_keyboard(
        total_pages, 
        page, 
        f"col_pg_{collection['access_key']}_",
        extra_buttons=extra_btns
    )
    
    try:
        if send_new:
            # Floating Menu: 发送新消息
            await client.send_message(message.chat.id, text, reply_markup=keyboard, disable_web_page_preview=True)
        elif is_callback:
            await message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)
        else:
            await message.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)
    except: pass
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
        
        # 超过10个，显示分页菜单
        # 超过10个，显示分页菜单
        if len(files) > 10:
            # 自动发送第一页 (Direct Send)
            first_page_files = files[:10]
            status_msg = await send_collection_files(client, message, first_page_files, f"{collection['name']} (第1页)")
            
            # 删除完成提示，减少干扰
            try: await status_msg.delete()
            except: pass
            
            # 显示浮动菜单
            await show_collection_page(client, message, collection, files, 1, send_new=True)
        else:
            # <= 10个，直接发送
            await send_collection_files(client, message, files, collection['name'])
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

async def get_collection_picker_keyboard(user_id, file_access_key, page=1):
    """生成合集选择键盘(支持分页和快速添加) - Smart Pagination"""
    from database import db
    from pyrogram.types import InlineKeyboardButton
    
    collections = db.get_user_collections(user_id)
    # 按ID倒序（最新的在前）
    collections.sort(key=lambda x: x['id'], reverse=True)
    
    per_page = 10 # 升级为10个每页
    total_pages = max(1, (len(collections) + per_page - 1) // per_page)
    
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    
    start = (page - 1) * per_page
    end = start + per_page
    page_items = collections[start:end]
    
    extra_btns = []
    
    # 快速添加 (Last Used) - 仅当 page=1 时显示
    if page == 1:
        last_col = user_last_collection.get(user_id)
        if last_col:
            exists = any(c['id'] == last_col['id'] for c in collections)
            if exists:
                extra_btns.append([InlineKeyboardButton(
                    f"⚡ 快速添加: {last_col['name']}",
                    callback_data=f"addcol_{file_access_key}_{last_col['id']}"
                )])
        
    # 构建当前页集合列表按钮
    for c in page_items:
        extra_btns.append([InlineKeyboardButton(
            f"📁 {c['name']} ({c['file_count']})", 
            callback_data=f"addcol_{file_access_key}_{c['id']}"
        )])
        
    extra_btns.append([InlineKeyboardButton("➕ 新建合集", callback_data=f"newcol_{file_access_key}")])
    extra_btns.append([InlineKeyboardButton("❌ 不添加", callback_data=f"skipcol_{file_access_key}")])
    
    # 使用 Smart Pagination Helper
    # 如果只有1页，隐藏页码显示? Helper 内部逻辑?
    # 我们这里控制 Picker 的 Title 文本，Page Info 在 make_pagination_keyboard 处理
    return make_pagination_keyboard(
        total_pages,
    # ... Wait, make_pagination_keyboard logic:
    # return InlineKeyboardMarkup(...)
    # I should verify make_pagination_keyboard logic later. 
    # For now, I update the CALLER to hide text.
        page,
        f"pick_pg_{file_access_key}_",
        extra_buttons=extra_btns
    )

@Client.on_message(filters.private & (filters.document | filters.video | filters.photo | filters.audio | filters.forwarded))
async def media_handler(client: Client, message: Message):
    """
    Handle media files and forwards.
    """
    # 权限检查
    if not await check_auth(client, message):
        return
    """处理收到的媒体文件 (包括转发的文件) - 自动加密存储"""
    from database import db
    import config
    
    user_id = message.from_user.id
    
    # 仅管理员可用 -> 已移除，改为 check_auth
    # if user_id != config.ADMIN_ID:
    #     return
    
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
            mode['total'] += 1
            if db.add_file_to_collection(mode["collection_id"], existing_file_id):
                mode["files"].append(file_name)
                mode['success'] += 1
            else:
                mode['success'] += 1 # 重复添加也算成功
            
            # Dashboard
            now = time.time()
            if now - mode.get('last_update', 0) > 2.0:
                mode['last_update'] = now
                try:
                    await client.edit_message_text(
                        chat_id=mode['status_chat_id'],
                        message_id=mode['status_msg_id'],
                        text=(
                            f"📁 接收合集: **{mode['collection_name']}**\n"
                            f"🔄 秒传成功: `{file_name}`\n"
                            f"📊 进度: {mode['total']} | ✅ {mode['success']} | ❌ {mode['fail']}\n"
                            f"⏳ 发 **结束** 完成"
                        )
                    )
                except: pass
        else:
            # 非收集模式：告知已存在
            await message.reply_text(
                f"📄 文件已存在！\n\n"
                f"📁 `{file_name}`\n"
                f"🔑 提取码: `{existing_access_key}`"
            )
        return
    
    # 文件未入库 -> 自动下载、加密、上传、入库
    status_msg = None
    if in_collection_mode:
        mode['total'] += 1
        now = time.time()
        if now - mode.get('last_update', 0) > 2.0:
            mode['last_update'] = now
            try:
                await client.edit_message_text(
                    chat_id=mode['status_chat_id'],
                    message_id=mode['status_msg_id'],
                    text=(
                        f"📁 接收合集: **{mode['collection_name']}**\n"
                        f"🔄 正在处理: `{file_name}`\n"
                        f"📊 进度: {mode['total']} | ✅ {mode['success']} | ❌ {mode['fail']}\n"
                        f"⏳ 发 **结束** 完成"
                    )
                )
            except: pass
    else:
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
        
        if status_msg: await status_msg.edit_text(f"🔒 正在加密 `{file_name}`...")
        await asyncio.to_thread(encrypt_file, download_path, encrypted_path, aes_key)
        
        # 删除原文件 (添加延时避免文件锁定)
        await asyncio.sleep(0.5)
        try:
            if os.path.exists(download_path):
                os.remove(download_path)
        except:
            pass
        
        # 3. 上传到存储频道 (优先用 Bot，失败则用闲置账号)
        if status_msg: await status_msg.edit_text(f"⬆️ 正在上传 `{file_name}`...")
        
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
        
        # 3.b 备份上传 (Dual Upload)
        backup_msg_id = 0
        backup_chat_id = 0
        
        if config.BACKUP_CHANNEL_ID and config.BACKUP_CHANNEL_ID != 0:
            try:
                if status_msg: await status_msg.edit_text(f"↻ 正在备份 `{file_name}`...")
                # 使用相同的上传方式 (Bot or User) 或 强制使用 User (更安全?) -> 这里跟随 primary logic
                uploader = client if upload_method == "Bot" else client.storage_client
                
                backup_msg = await uploader.send_document(
                    config.BACKUP_CHANNEL_ID,
                    encrypted_path,
                    caption=f"📦 {file_name}\n🔒 [AES-256 Encrypted Backup]"
                )
                backup_msg_id = backup_msg.id
                backup_chat_id = config.BACKUP_CHANNEL_ID
            except Exception as e:
                print(f"Backup failed: {e}")
                # 备份失败不阻断主流程

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
            encryption_key=aes_key_b64,
            backup_message_id=backup_msg_id,
            backup_chat_id=backup_chat_id
        )
        
        # 清理加密文件
        await asyncio.sleep(0.3)
        try:
            if os.path.exists(encrypted_path):
                os.remove(encrypted_path)
        except:
            pass
        
        # 5. 如果在收集模式，添加到合集
        # 5. 如果在收集模式，添加到合集
        if in_collection_mode:
            # ... (Existing Logic)
            db.cursor.execute('SELECT id FROM files WHERE access_key = ?', (access_key,))
            new_row = db.cursor.fetchone()
            if new_row:
                db.add_file_to_collection(mode["collection_id"], new_row[0])
            
            mode["files"].append(file_name)
            mode['success'] += 1
            
            now = time.time()
            if now - mode.get('last_update', 0) > 2.0:
                mode['last_update'] = now
                try:
                    await client.edit_message_text(
                        chat_id=mode['status_chat_id'],
                        message_id=mode['status_msg_id'],
                        text=(
                            f"📁 接收合集: **{mode['collection_name']}**\n"
                            f"✅ 刚刚完成: `{file_name}`\n"
                            f"📊 进度: {mode['total']} | ✅ {mode['success']} | ❌ {mode['fail']}\n"
                            f"⏳ 发 **结束** 完成"
                        )
                    )
                except: pass
        
        # === NEW: Media Group Logic ===
        elif message.media_group_id:
            mg_id = message.media_group_id
            
            # Init state if needed
            if mg_id not in media_group_states:
                # 发送初始消息 (带 Picker)
                # 使用 Group ID 作为 Picker Key 的一部分 -> pick_mg_GROUPID_
                # 但 Picker 需要 File Access Key? 
                # 我们这里 Picker 用于 Bind Group.
                # Callback: bind_mg_GROUPID_COLID
                
                start_text = f"📦 **收到相册/多文件组**\n⏳ 正在处理第 1 个文件..."
                
                # 获取 Picker (Page 1) - 使用 mg_ 前缀
                # helper definition: get_collection_picker_keyboard(user_id, key, page)
                # key used for callback: addcol_KEY_ID
                # We need addcol_mg_MGID_ID
                
                # Hack: Pass "mg_" + mg_id as the 'access_key' to the helper?
                # Helper uses key string in callback.
                # If key starts with "mg_", we handle it in `add_to_collection_callback`.
                
                fake_key = f"mg_{mg_id}"
                keyboard = await get_collection_picker_keyboard(user_id, fake_key, page=1)
                
                status_msg = await message.reply_text(start_text, reply_markup=keyboard)
                
                media_group_states[mg_id] = {
                    'msg': status_msg,
                    'keys': [],
                    'bound_col_id': None,
                    'bound_col_name': None,
                    'count': 0,
                    'last_update': time.time()
                }
            
            state = media_group_states[mg_id]
            state['count'] += 1
            state['keys'].append(access_key)
            
            # Check Binding
            if state['bound_col_id']:
                # Auto add
                db.cursor.execute('SELECT id FROM files WHERE access_key = ?', (access_key,))
                frow = db.cursor.fetchone()
                if frow:
                    db.add_file_to_collection(state['bound_col_id'], frow[0])
            
            # Debounced Update
            now = time.time()
            if now - state['last_update'] > 2.0 or state['count'] == 1:
                state['last_update'] = now
                try:
                    col_status = f"📂 存入: **{state['bound_col_name']}**" if state['bound_col_name'] else "Wait 选择合集..."
                    await state['msg'].edit_text(
                        f"📦 **收到相册/多文件组**\n"
                        f"📊 已处理: {state['count']} 个文件\n"
                        f"{col_status}\n\n"
                        f"📄 最新: `{file_name}`\n"
                        f"🔑 最新Key: `{access_key}`",
                        reply_markup=state['msg'].reply_markup
                    )
                except: pass

        else:
            # 非收集模式 & 单文件：返回提取码 + 可选添加到合集 (使用分页键盘)
            keyboard = await get_collection_picker_keyboard(user_id, access_key, page=1)
            
            await status_msg.edit_text(
                f"✅ **已加密存储！**\n\n"
                f"📄 文件: `{file_name}`\n"
                f"🔑 提取码: `{access_key}`\n\n"
                f"**添加到哪个合集？**",
                reply_markup=keyboard
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
    
    # Handle Normal File or Media Group
    is_mg = False
    mg_id = None
    
    parts = callback.data.split("_")
    # check prefix used
    # callback data: addcol_KEY_COLID
    # if KEY startswith "mg", then it is Media Group
    
    collection_id = int(parts[-1])
    access_key = "_".join(parts[1:-1])
    
    if access_key.startswith("mg_"):
        is_mg = True
        mg_id = access_key[3:]
    
    # 获取文件 ID (Only for non-MG)
    if not is_mg:
        db.cursor.execute('SELECT id FROM files WHERE access_key = ?', (access_key,))
        row = db.cursor.fetchone()
        if row:
            db.add_file_to_collection(collection_id, row[0])
            
            # 获取合集名称用于缓存
            db.cursor.execute("SELECT name FROM collections WHERE id=?", (collection_id,))
            col_res = db.cursor.fetchone()
            col_name = col_res[0] if col_res else "合集"
            
            if col_res:
                user_last_collection[callback.from_user.id] = {'id': collection_id, 'name': col_name}
            
            await callback.message.edit_text(
                f"✅ 已添加到合集 **{col_name}**！\n\n"
                f"🔑 提取码: `{access_key}`"
            )
        else:
            await callback.answer("❌ 文件未找到", show_alert=True)
            
    else:
        # === Handle Media Group Binding ===
        if mg_id not in media_group_states:
             await callback.answer("❌ 任务已过期", show_alert=True)
             return

        state = media_group_states[mg_id]
        
        # Get Collection Name
        db.cursor.execute("SELECT name FROM collections WHERE id=?", (collection_id,))
        col_res = db.cursor.fetchone()
        col_name = col_res[0] if col_res else "合集"
        
        # 1. Bind
        state['bound_col_id'] = collection_id
        state['bound_col_name'] = col_name
        user_last_collection[callback.from_user.id] = {'id': collection_id, 'name': col_name}
        
        # 2. Add Existing Keys
        added_count = 0
        for key in state['keys']:
             db.cursor.execute('SELECT id FROM files WHERE access_key = ?', (key,))
             frow = db.cursor.fetchone()
             if frow:
                 db.add_file_to_collection(collection_id, frow[0])
                 added_count += 1
        
        # 3. Update Msg
        await state['msg'].edit_text(
            f"✅ **已绑定合集: {col_name}**\n"
            f"📊 当前处理: {state['count']} 个文件\n"
            f"📥 后续文件将自动存入此合集..."
        )
        await callback.answer(f"已存入 {added_count} 个文件")

@Client.on_callback_query(filters.regex(r"^pick_pg_"))
async def picker_pagination_callback(client: Client, callback: CallbackQuery):
    from database import db
    import config
    
    parts = callback.data.split("_")
    page = int(parts[-1])
    access_key = "_".join(parts[2:-1])
    
    # 1. 获取文件名称以重建文本
    db.cursor.execute('SELECT file_name FROM files WHERE access_key = ?', (access_key,))
    row = db.cursor.fetchone()
    file_name = row[0] if row else "未知文件"
    
    # 2. 获取总页数 (用于文本显示) 
    # 这里有点低效，但为了显示 "Page X/Y" 必须算一次
    collections = db.get_user_collections(callback.from_user.id)
    per_page = 10
    total_pages = max(1, (len(collections) + per_page - 1) // per_page)
    
    # 3. 构建文本
    page_info = f" (第 {page}/{total_pages} 页)" if total_pages > 1 else ""
    
    text = (
        f"✅ **已加密存储！**\n\n"
        f"📄 文件: `{file_name}`\n"
        f"🔑 提取码: `{access_key}`\n\n"
        f"**添加到哪个合集？**{page_info}"
    )
    
    keyboard = await get_collection_picker_keyboard(callback.from_user.id, access_key, page)
    
    # Floating Menu: Delete Old -> Send New
    try: await callback.message.delete()
    except: pass
    
    await client.send_message(callback.message.chat.id, text, reply_markup=keyboard, disable_web_page_preview=True)
    await callback.answer(f"第 {page} 页")


@Client.on_callback_query(filters.regex(r"^newcol_"))
async def new_collection_callback(client: Client, callback: CallbackQuery):
    """创建新合集并添加文件"""
    parts = callback.data.split("_")
    access_key = "_".join(parts[1:])
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
    parts = callback.data.split("_")
    access_key = "_".join(parts[1:])
    
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
    
    # 移除 Admin 检查，允许所有用户创建合集
    # if user_id != config.ADMIN_ID:
    #     message.continue_propagation()
    
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

# ========== 分页回调 ==========

@Client.on_callback_query(filters.regex(r"^col_(pg|dl|all)_"))
async def collection_pagination_callback(client: Client, callback: CallbackQuery):
    from database import db
    parts = callback.data.split("_")
    action = parts[1]
    
    if action == "all":
        access_key = "_".join(parts[2:])
        page = 1
    else:
        # pg or dl
        try:
            page = int(parts[-1])
            access_key = "_".join(parts[2:-1])
        except ValueError:
            # Fallback for unexpected formats
            page = 1
            access_key = "_".join(parts[2:])

    collection = db.get_collection_by_key(access_key)
    if not collection:
        await callback.answer(f"合集不存在或密钥已失效\n(Key: {access_key})", show_alert=True)
        return
        
    files = db.get_collection_files(collection["id"])
    
    if action == "pg":
        # Direct Send + Floating Menu
        per_page = 10
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_files = files[start_idx:end_idx]
        
        await callback.answer(f"正在发送第 {page} 页...", show_alert=False)
        
        # 1. Update Menu -> Sending
        await send_collection_files(client, callback.message, page_files, f"{collection['name']} (第{page}页)", edit_msg=callback.message)
        
        # 2. Delete Old Menu
        try: await callback.message.delete()
        except: pass
        
        # 3. New Menu at Bottom
        await show_collection_page(client, callback.message, collection, files, page, send_new=True)
        
    elif action == "dl":
        per_page = 10
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_files = files[start_idx:end_idx]
        
        await callback.answer("开始发送...", show_alert=False)
        # 1. 使用当前菜单消息显示 "正在下载..." (edit_msg)
        await send_collection_files(client, callback.message, page_files, f"{collection['name']} (第{page}页)", edit_msg=callback.message)
        
        # 2. 发送完成后，删除旧菜单 (Floating Menu 效果)
        try:
            await callback.message.delete()
        except: pass
        
        # 3. 发送新菜单到最底部
        await show_collection_page(client, callback.message, collection, files, page, send_new=True)
        
    elif action == "all":
        # Smart Send All: 发送剩余 (跳过第一页)
        remaining_files = files[10:]
        if not remaining_files:
             await callback.answer("没有更多文件了 (第一页已发)", show_alert=True)
             return
             
        await callback.answer(f"开始发送剩余 {len(remaining_files)} 个文件...", show_alert=True)
        # 这里的 "发送剩余" 会自动处理 float menu 吗？
        # Send All 通常是终结操作，发送完后应该显示 "发送完成"
        # 或者 我们可以 Float 到最后一页？
        # 这里维持原样，只是把文件列表改成剩余的。
        await send_collection_files(client, callback.message, remaining_files, collection['name'], edit_msg=callback.message)


# ========== Interactive Menu Handlers (Priority -3: Always First) ==========
@Client.on_message(filters.regex("📥 批量下载") & filters.private, group=-3)
async def menu_download_handler(client, message):
    from handlers.setup import is_admin
    if not is_admin(client, message.from_user.id):
        await message.reply_text(
            "🚫 **权限不足**\n\n"
            "批量下载功能仅限管理员使用。\n"
            "如需下载禁止转发的受限资源，请联系机器人客服 (管理员)。"
        )
        return

    # Show sub-menu with old functions
    from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
    buttons = [
        [KeyboardButton("📋 最近对话"), KeyboardButton("🔍 搜索对话")],
        [KeyboardButton("👻 删除账户"), KeyboardButton("📥 开始下载")],
        [KeyboardButton("🔙 返回主菜单")]
    ]
    await message.reply_text(
        "📥 **批量下载工具箱 (管理员)**\n\n"
        "请选择操作：\n"
        "🔹 **最近对话**: 查看用户账号的最近对话列表\n"
        "🔹 **搜索对话**: 按关键词搜索对话\n"
        "🔹 **删除账户**: 查找已删除/封禁的账号\n"
        "🔹 **开始下载**: 输入链接或ID批量下载\n",
        reply_markup=ReplyKeyboardMarkup(
            buttons,
            resize_keyboard=True,
            one_time_keyboard=False,
            is_persistent=True
        )
    )

# Sub-handlers for batch download sub-menu
@Client.on_message(filters.regex("📋 最近对话") & filters.private, group=-3)
async def sub_recent_handler(client, message):
    await list_recent_chats(client, message)
    message.stop_propagation()

@Client.on_message(filters.regex("🔍 搜索对话") & filters.private, group=-3)
async def sub_search_handler(client, message):
    await search_chats(client, message)
    message.stop_propagation()

@Client.on_message(filters.regex("👻 删除账户") & filters.private, group=-3)
async def sub_deleted_handler(client, message):
    await find_deleted_accounts(client, message)
    message.stop_propagation()

@Client.on_message(filters.regex("📥 开始下载") & filters.private, group=-3)
async def sub_start_download_handler(client, message):
    from pyrogram.types import ForceReply
    user_interaction_state[message.from_user.id] = "waiting_dl_id_limit"
    await message.reply_text(
        "📥 **批量下载**\n\n"
        "请输入 **频道ID** 和 **下载数量**。\n\n"
        "格式: `频道ID 数量`\n"
        "例如: `-1001234567890 50`\n\n"
        "💡 使用 \"📋 最近对话\" 可以查看频道ID",
        reply_markup=ForceReply(placeholder="例如: -1001234567890 50")
    )
    message.stop_propagation()

@Client.on_message(filters.regex("☁️ 存储/上传") & filters.private, group=-3)
async def menu_storage_handler(client, message):
    from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
    buttons = [
        [KeyboardButton("📂 我的合集"), KeyboardButton("🆕 新建合集")],
        [KeyboardButton("� 查找文件"), KeyboardButton("📊 统计信息")],
        [KeyboardButton("�🔙 返回主菜单")]
    ]
    await message.reply_text(
        "☁️ **存储中心**\n\n"
        "请选择操作：\n"
        "🔹 **我的合集**: 管理和浏览现有合集\n"
        "🔹 **新建合集**: 创建新的加密保险箱\n"
        "🔹 **查找文件**: 全局搜索已存储文件\n\n"
        "💡 当然，你也可以随时直接发送文件给我，我会自动处理。",
        reply_markup=ReplyKeyboardMarkup(
            buttons,
            resize_keyboard=True,
            one_time_keyboard=False,
            is_persistent=True
        )
    )
    message.stop_propagation()

# Sub-menu handlers for Storage
@Client.on_message(filters.regex("📂 我的合集") & filters.private, group=-3)
async def sub_my_collections(client, message):
    # Trigger existing /mycollections logic
    # We can reuse my_collections_cmd (which is command-based) by creating a mock or extracting logic
    # Ideally, just call the function if it accepts (client, message)
    # my_collections_cmd is at ~line 942
    await my_collections_cmd(client, message)
    message.stop_propagation()

@Client.on_message(filters.regex("🆕 新建合集") & filters.private, group=-3)
async def sub_new_collection(client, message):
    await create_collection_cmd(client, message)
    message.stop_propagation()

@Client.on_message(filters.regex("🔍 查找文件") & filters.private, group=-3)
async def sub_find_file(client, message):
    from handlers.tools import find_cmd
    # find_cmd logic might assume args?
    # Let's check find_cmd later.
    # It probably needs logic like create_collection_cmd to Prompt "What to find?"
    # For now, just call it.
    await find_cmd(client, message)
    message.stop_propagation()

@Client.on_message(filters.regex("📊 统计信息") & filters.private, group=-3)
async def sub_stats_info(client, message):
    from handlers.tools import stats_cmd
    await stats_cmd(client, message)
    message.stop_propagation()


@Client.on_message(filters.regex("👮 管理员") & filters.private, group=-3)
async def menu_admin_handler(client, message):
    # Check Admin
    from handlers.setup import is_admin
    if not is_admin(client, message.from_user.id):
        return
        
    from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
    buttons = [
        [KeyboardButton("👥 用户管理"), KeyboardButton("📉 系统统计")],
        # [KeyboardButton("🔍 搜索文件"), KeyboardButton("🗑 近期删除")],
        [KeyboardButton("🔙 返回主菜单")]
    ]
    await message.reply_text(
        "👮 **管理员控制台**\n请选择管理功能：",
        reply_markup=ReplyKeyboardMarkup(
            buttons,
            resize_keyboard=True,
            one_time_keyboard=False,
            is_persistent=True
        )
    )
    message.stop_propagation()

# Sub-menu handlers for Admin
@Client.on_message(filters.regex("👥 用户管理") & filters.private, group=-3)
async def sub_admin_users(client, message):
    # Trigger list_users_handler
    await list_users_handler(client, message)
    message.stop_propagation()

@Client.on_message(filters.regex("📉 系统统计") & filters.private, group=-3)
async def sub_admin_stats(client, message):
    await admin_stats_cmd(client, message)
    message.stop_propagation()


@Client.on_message(filters.regex("🔙 返回主菜单") & filters.private, group=-3)
async def back_to_main(client, message):
    from handlers.setup import send_main_menu
    await send_main_menu(client, message)
    message.stop_propagation()

@Client.on_callback_query(filters.regex("cancel_action"))
async def cancel_action_callback(client, callback):
    uid = callback.from_user.id
    if uid in user_interaction_state:
        del user_interaction_state[uid]
    await callback.message.edit_text("✅ 已取消操作")

# Enhanced Link Handler for Download State
# We hook into existing link_handler logic or pre-empt it?
# link_handler matches text. We can add a check at top of old link_handler OR add a new priority handler.
# New priority handler is better.

@Client.on_message(filters.text & filters.private, group=-2)
async def download_state_handler(client, message):

    uid = message.from_user.id
    state = user_interaction_state.get(uid)
    
    # Handle original format: channel_id limit
    if state == "waiting_dl_id_limit":
        
        parts = message.text.strip().split()
        if len(parts) < 2:
            from handlers.setup import get_main_menu_keyboard
            is_adm = message.from_user.id == client.admin_id
            await message.reply_text("❌ 格式错误！请输入：`频道ID 数量`\n例如：`-1001234567890 50`", reply_markup=get_main_menu_keyboard(is_adm))
            return
        
        try:
            chat_id = int(parts[0])
            limit = int(parts[1])
        except ValueError:
            from handlers.setup import get_main_menu_keyboard
            is_adm = message.from_user.id == client.admin_id
            await message.reply_text("❌ ID 或数量必须是数字！请重试。\n或者点击下方按钮返回。", reply_markup=get_main_menu_keyboard(is_adm))
            return
        
        # Success! Consume state now
        del user_interaction_state[uid]
        
        # Use default destination (channel)
        dest = user_download_dest.get(uid, "channel")
        await do_batch_download(client, message, chat_id, limit, dest)
        message.stop_propagation()
        return
    
    # Handle link-based format (for backwards compatibility if ever needed)
    if state != "waiting_dl_link":
        message.continue_propagation()
        return
    # Check if text exists
    if not message.text:
        await message.reply_text("⚠️ 请发送 **链接** (Link)，不要发送文件或图片。", quote=True)
        message.stop_propagation()
        return

    del user_interaction_state[uid] # Consume state
    
    text = message.text.strip()
    chat_id = None
    chat_title = "未知"
    
    status_msg = await message.reply_text("🔍 正在解析链接...")
    
    import re
    # 1. Private Link t.me/c/123/456
    match_c = re.search(r"t\.me/c/(\d+)", text)
    if match_c:
        chat_id = int(f"-100{match_c.group(1)}")
        chat_title = "私有频道/群组 (需闲置号在群内)"
    
    # 2. Public Username/Link
    elif "t.me/" in text or text.startswith("@"):
        # Extract username
        username = text.split("t.me/")[-1].split("/")[0] if "t.me/" in text else text.replace("@", "")
        # Remove + for invite links handled below
        if not username.startswith("+") and not "joinchat" in text:
             try:
                 chat = await client.user_client.get_chat(username)
                 chat_id = chat.id
                 chat_title = chat.title
             except Exception as e:
                 await status_msg.edit_text(f"❌ 无法解析: {e}\n闲置号可能不在该群组，或者链接无效。")
                 return

    # 3. Invite Link
    if not chat_id:
        # Try Join
        try:
            # We use storage_client to join
            chat = await client.user_client.join_chat(text)
            chat_id = chat.id
            chat_title = chat.title
            await message.reply_text(f"✅ 已成功加入群组: {chat_title}")
        except Exception as e:
            # If already member (USER_ALREADY_PARTICIPANT)
            if "USER_ALREADY_PARTICIPANT" in str(e):
                 # Can't easily get ID from join_chat error, but we can try get_chat if we have a username/ID?
                 # If invite link, we assume we joined. But we don't know ID if error.
                 # Actually join_chat returns Chat object normally.
                 # If error, we might be stuck.
                 pass
            
            # If standard private link failed earlier, we are here.
            await status_msg.edit_text(f"⚠️ 解析失败或无法加入: {e}\n如果这是私有群组且闲置号已在其中，请使用 `/getid` 获取 ID 后直接使用 /download ID。")
            return

    if chat_id:
        # Check Linked Chat - REMOVED FOR SAFETY
        # logic removed to prevent joining trap groups
        
        # Check Linked Chat (Safe Mode: Info Only)
        linked_text = ""
        try:
             full_chat = await client.user_client.get_chat(chat_id)
             if full_chat.linked_chat:
                  lc = full_chat.linked_chat
                  linked_text = (
                      f"\n🔗 **关联群组 (评论区)**:\n"
                      f"名: `{lc.title}`\n"
                      f"ID: `{lc.id}`\n"
                      f"(如需下载评论，请确保闲置号在群内，然后直接发送该ID或邀请链接)"
                  )
        except: pass

        response_text = (
            f"✅ **目标锁定**\n\n"
            f"📂 名称: **{chat_title}**\n"
            f"🆔 ID: `{chat_id}`"
            f"{linked_text}\n\n"
            f"请选择操作:"
        )
        
        # Build Main Buttons
        main_btns = [
             InlineKeyboardButton("🚀 下载 (50)", callback_data=f"startdl_{chat_id}_50"),
             InlineKeyboardButton("🚀 下载 (200)", callback_data=f"startdl_{chat_id}_200")
        ]
        leave_btns = [
             InlineKeyboardButton("🚀 下载并退出 (50)", callback_data=f"startdl_{chat_id}_50_1"),
             InlineKeyboardButton("🚀 下载并退出 (200)", callback_data=f"startdl_{chat_id}_200_1") 
        ]
        
        keyboard = []
        keyboard.append(main_btns)
        keyboard.append(leave_btns)
        keyboard.append([InlineKeyboardButton("🚪 闲置号退出群组", callback_data=f"leavedl_{chat_id}")])
        
        await status_msg.edit_text(response_text, reply_markup=InlineKeyboardMarkup(keyboard))


@Client.on_callback_query(filters.regex(r"^startdl_"))
async def start_download_btn(client, callback):
    parts = callback.data.split("_")
    chat_id = int(parts[1])
    count = int(parts[2])
    auto_leave = False
    if len(parts) > 3:
        auto_leave = bool(int(parts[3]))
    
    leave_text = " (完成后自动退出)" if auto_leave else ""
    await callback.message.edit_text(f"🚀 **开始下载任务**\n目标: `{chat_id}`\n数量: {count}{leave_text}\n\n请留意后续通知。")
    
    # Trigger batch download logic
    # We can reuse do_batch_download logic but it expects a Message object with command args.
    # Cleaner to refactor do_batch_download or call a shared function.
    # For now, I will invoke a helper or copy logic.
    # Reusing `handlers.tools.do_batch_download` is hard because of `message` arg.
    # I'll create `execute_batch_download(client, user_id, target_chat_id, limit, status_message)`
    
    # ... Wait, I can't easily extract logic in this chunk.
    # Quick Check: Can I construct a Fake Message?
    # Yes, but hacky.
    
    # Better: Update do_batch_download to be split.
    # BUT, for now, I will just call the command via client? No.
    # I'll implement a simple loop here or call existing logic?
    # `do_batch_download` is complex.
    # I will Refactor `do_batch_download` separately?
    # Or just spawn a task.
    
    # Quick fix: Send a command message from the user? 
    # `await client.send_message(user_id, f"/download {chat_id} {count}")`
    # This works perfectly and reuses all logic!
    
    await callback.answer("任务已提交")
    # Simulate command
    msg = await client.send_message(callback.from_user.id, f"/download {chat_id} {count}")
    # We need to trigger the handler manually? 
    # No, sending message to self (as bot) doesn't trigger bot handlers usually (bot seeing own message).
    # Sending AS USER? Bot can't send as user.
    
    # We must REUSE Logic. 
    # I will Execute the function manually.
    
    from handlers.tools import do_batch_download
    from types import SimpleNamespace
    
    # Mock Message
    class MockMessage:
        def __init__(self, client, chat_id, text, user_id):
            self.chat = SimpleNamespace(id=user_id, type="private", title="User")
            self.from_user = SimpleNamespace(id=user_id, is_bot=False, username="User")
            self.command = text.split()
            self._client = client
            self.text = text
            
        async def reply_text(self, text, **kwargs):
            return await self._client.send_message(self.chat.id, text, **kwargs)
            
    mock_msg = MockMessage(client, chat_id, f"/download {chat_id} {count}", callback.from_user.id)
    await do_batch_download(client, mock_msg)
    
    if auto_leave:
        try:
            await client.storage_client.leave_chat(chat_id)
            await client.send_message(callback.from_user.id, f"✅ 任务完成，闲置号已自动退出群组 `{chat_id}`")
        except Exception as e:
            await client.send_message(callback.from_user.id, f"⚠️ 自动退出失败: {e}")


@Client.on_callback_query(filters.regex(r"^leavedl_"))
async def leave_download_btn(client, callback):
    chat_id = int(callback.data.split("_")[1])
    try:
        await client.storage_client.leave_chat(chat_id)
        await callback.message.edit_text(f"✅ 闲置号已退出群组 `{chat_id}`")
    except Exception as e:
        await callback.answer(f"退出失败: {e}", show_alert=True)

# ========== User Management (Admin) ==========

@Client.on_message(filters.command("users") & filters.private)
async def list_users_handler(client, message):
    from handlers.setup import is_admin
    if not is_admin(client, message.from_user.id):
        return

    await show_user_list(client, message, page=1)

async def show_user_list(client, message, page=1):
    from database import db
    users = db.get_all_users()
    total_users = len(users)
    per_page = 10
    total_pages = max(1, (total_users + per_page - 1) // per_page)
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_users = users[start_idx:end_idx]
    
    text = f"👥 **用户列表** (共 {total_users} 人)\n页码: {page}/{total_pages}\n\n"
    
    keyboard = []
    
    for u in page_users:
        status_icon = "🟢" if u['status'] == 'active' else "🔴"
        name = u['first_name'] or "未知"
        uid = u['id']
        username = f"@{u['username']}" if u['username'] else "No Username"
        
        # Add Manage Button for each user
        # Limit row width? 1 per row clearly
        btn_text = f"{status_icon} {name} ({uid})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"mng_u_{uid}")])
        
        text += f"{status_icon} **{name}** `{uid}`\nStatus: {u['status']}\n\n"
        
    # Pagination
    nav_btns = []
    if page > 1:
        nav_btns.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"users_pg_{page-1}"))
    if page < total_pages:
        nav_btns.append(InlineKeyboardButton("➡️ 下一页", callback_data=f"users_pg_{page+1}"))
        
    if nav_btns:
        keyboard.append(nav_btns)
        
    # Add Refresh
    keyboard.append([InlineKeyboardButton("🔄 刷新", callback_data=f"users_pg_{page}")])
    
    try:
        if isinstance(message, Message):
            await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except: pass

@Client.on_callback_query(filters.regex(r"^users_pg_"))
async def users_page_callback(client, callback):
    page = int(callback.data.split("_")[-1])
    await show_user_list(client, callback.message, page)
    await callback.answer()

@Client.on_callback_query(filters.regex(r"^mng_u_"))
async def manage_user_callback(client, callback):
    uid = int(callback.data.split("_")[-1])
    from database import db
    user = db.get_user(uid)
    
    if not user:
        await callback.answer("用户不存在", show_alert=True)
        return
        
    info = (
        f"👤 **用户管理**\n\n"
        f"名字: {user['first_name']}\n"
        f"ID: `{user['id']}`\n"
        f"用户名: @{user['username']}\n"
        f"状态: {user['status']}\n"
        f"封禁至: {user['ban_until'] or '无'}\n"
        f"同意条款: {'✅' if user['accepted_terms'] else '❌'}\n"
    )
    
    btns = [
        [
            InlineKeyboardButton("🚫 封禁 1天", callback_data=f"ban_u_{uid}_1d"),
            InlineKeyboardButton("🚫 封禁 3天", callback_data=f"ban_u_{uid}_3d")
        ],
        [
            InlineKeyboardButton("🚫 永久封禁", callback_data=f"ban_u_{uid}_forever"),
            InlineKeyboardButton("✅ 解封", callback_data=f"ban_u_{uid}_unban")
        ],
        [InlineKeyboardButton("🔙 返回列表", callback_data="users_pg_1")]
    ]
    
    await callback.message.edit_text(info, reply_markup=InlineKeyboardMarkup(btns))
    await callback.answer()

@Client.on_callback_query(filters.regex(r"^ban_u_"))
async def execute_ban_callback(client, callback):
    parts = callback.data.split("_")
    uid = int(parts[2])
    action = parts[3]
    
    from database import db
    from datetime import datetime, timedelta
    
    status = "active"
    until = None
    msg = "已解封"
    

    if action == "unban":
        status = "active"
        until = None
        msg = "✅ 用户已解封"
    elif action == "forever":
        status = "banned"
        until = datetime.now() + timedelta(days=36500) # 100 years
        msg = "🚫 用户已永久封禁"
    elif action.endswith("d"):
        days = int(action[:-1])
        status = "banned"
        until = datetime.now() + timedelta(days=days)
        msg = f"🚫 用户封禁 {days} 天"
        
    db.set_user_ban(uid, status, until)
    
    await callback.answer(msg, show_alert=True)
    
    # Refresh View
    # Call manage_user_callback logic again
    # Reuse via fake callback data?
    # Or just copy logic
    user = db.get_user(uid)
    info = (
        f"👤 **用户管理**\n\n"
        f"名字: {user['first_name']}\n"
        f"ID: `{user['id']}`\n"
        f"用户名: @{user['username']}\n"
        f"状态: {user['status']}\n"
        f"封禁至: {user['ban_until'] or '无'}\n"
        f"同意条款: {'✅' if user['accepted_terms'] else '❌'}\n"
    )
    
    btns = [
        [
            InlineKeyboardButton("🚫 封禁 1天", callback_data=f"ban_u_{uid}_1d"),
            InlineKeyboardButton("🚫 封禁 3天", callback_data=f"ban_u_{uid}_3d")
        ],
        [
            InlineKeyboardButton("🚫 永久封禁", callback_data=f"ban_u_{uid}_forever"),
            InlineKeyboardButton("✅ 解封", callback_data=f"ban_u_{uid}_unban")
        ],
        [InlineKeyboardButton("🔙 返回列表", callback_data="users_pg_1")]
    ]
    await callback.message.edit_text(info, reply_markup=InlineKeyboardMarkup(btns))


# ========== Terms Agreement Handler ==========
@Client.on_callback_query(filters.regex("agree_terms"))
async def agree_terms_callback(client, callback):
    from database import db
    from handlers.session import activate_session
    uid = callback.from_user.id
    
    # Security Check: Re-verify Ban Status before activating session
    # (Prevents restart-bypass)
    from datetime import datetime
    u_data = db.get_user(uid)
    if u_data and u_data.get('status') == 'banned':
        ban_until = u_data.get('ban_until')
        blocked = False
        if ban_until:
             if isinstance(ban_until, str):
                 try: ban_until = datetime.fromisoformat(ban_until)
                 except: pass
             if isinstance(ban_until, datetime) and ban_until > datetime.now():
                 blocked = True
        else:
             blocked = True
             
        if blocked:
            await callback.answer("🚫 无法操作: 您已被封禁。", show_alert=True)
            return

    # Update Session (Vital for "Restart" logic)
    activate_session(uid)
    
    # Update DB (Just for records)
    db.update_user_terms(uid, True)
    
    await callback.answer("✅ 你已同意条款，欢迎使用！")
    try:
        await callback.message.delete()
    except: pass
    
    # Send Main Menu
    from handlers.setup import send_main_menu
    await send_main_menu(client, callback.message)


# ========== 补充功能: 查找与统计 ==========

@Client.on_message(filters.command("find") & filters.private)
async def find_cmd(client: Client, message: Message):
    """查找文件"""
    from database import db
    from pyrogram.types import ForceReply
    
    args = message.text.split(maxsplit=1)
    
    # Handle Button Trigger
    if message.text == "🔍 查找文件" or len(args) < 2:
        await message.reply_text(
            "🔍 **查找文件**\n\n"
            "请输入关键词：",
            reply_markup=ForceReply(placeholder="输入关键词...")
        )
        return
        
    keyword = args[1]
    owner_id = message.from_user.id
    
    # Simple Search (Exclude deleted/banned? Not handled yet for files)
    # Search User's Collections first? Or All Files?
    # User owns collections, files are global but encrypted? 
    # Usually "My Files" -> Files in My Collections.
    # But current DB structure: Files don't have owner_id directly, Collections do.
    # Files are linked to Collections via collection_files.
    # So finding USER'S files means: 
    # JOIN collections ON collection_files.collection_id = collections.id WHERE collections.owner_id = ? AND files.file_name LIKE ?
    
    query = """
        SELECT f.file_name, f.access_key, c.name 
        FROM files f
        JOIN collection_files cf ON f.id = cf.file_id
        JOIN collections c ON cf.collection_id = c.id
        WHERE c.owner_id = ? AND f.file_name LIKE ?
        LIMIT 20
    """
    db.cursor.execute(query, (owner_id, f"%{keyword}%"))
    rows = db.cursor.fetchall()
    
    if not rows:
        await message.reply_text(f"❌ 未找到包含 **{keyword}** 的文件。")
        return
        
    text = f"🔍 **搜索结果: {keyword}**\n\n"
    for r in rows:
        fname, key, cname = r
        text += f"📄 `{fname}`\n   └ 📁 {cname} | 🔑 `{key}`\n"
        
    await message.reply_text(text)

@Client.on_message(filters.command("stats") & filters.private)
async def stats_cmd(client: Client, message: Message):
    """统计信息"""
    from database import db
    owner_id = message.from_user.id
    
    # Count User's Collections
    db.cursor.execute("SELECT COUNT(*) FROM collections WHERE owner_id=?", (owner_id,))
    c_count = db.cursor.fetchone()[0]
    
    # Count User's Files (Distinct)
    db.cursor.execute("""
        SELECT COUNT(DISTINCT f.id) 
        FROM files f
        JOIN collection_files cf ON f.id = cf.file_id
        JOIN collections c ON cf.collection_id = c.id
        WHERE c.owner_id = ?
    """, (owner_id,))
    f_count = db.cursor.fetchone()[0]
    
    await message.reply_text(
        f"📊 **统计信息**\n\n"
        f"👤 用户: {message.from_user.first_name}\n"
        f"📂 合集总数: {c_count}\n"
        f"📄 文件总数: {f_count}\n"
    )

@Client.on_message(filters.reply & filters.private)
async def search_reply_handler(client: Client, message: Message):
    """Handle Reply to Search Prompt"""
    reply = message.reply_to_message
    if not reply or not reply.text: return
    
    if "🔍 **查找文件**" in reply.text and "请输入关键词" in reply.text:
         # Execute Search
         keyword = message.text.strip()
         from database import db
         owner_id = message.from_user.id
         
         query = """
            SELECT f.file_name, f.access_key, c.name 
            FROM files f
            JOIN collection_files cf ON f.id = cf.file_id
            JOIN collections c ON cf.collection_id = c.id
            WHERE c.owner_id = ? AND f.file_name LIKE ?
            LIMIT 20
         """
         db.cursor.execute(query, (owner_id, f"%{keyword}%"))
         rows = db.cursor.fetchall()
        
         if not rows:
            await message.reply_text(f"❌ 未找到包含 **{keyword}** 的文件。")
            return
            
         text = f"🔍 **搜索结果: {keyword}**\n\n"
         for r in rows:
            fname, key, cname = r
            text += f"📄 `{fname}`\n   └ 📁 {cname} | 🔑 `{key}`\n"
            
         await message.reply_text(text)


async def admin_stats_cmd(client: Client, message: Message):
    """管理员查看系统级统计"""
    from handlers.setup import is_admin
    if not is_admin(client, message.from_user.id):
        await message.reply_text("🚫 权限不足")
        return
        
    from database import db
    
    # 1. User Count
    db.cursor.execute("SELECT COUNT(*) FROM users")
    user_count = db.cursor.fetchone()[0]
    
    # 2. Collection Count
    db.cursor.execute("SELECT COUNT(*) FROM collections")
    col_count = db.cursor.fetchone()[0]
    
    # 3. File Count
    db.cursor.execute("SELECT COUNT(*) FROM files")
    file_count = db.cursor.fetchone()[0]
    
    await message.reply_text(
        f"📉 **系统全局统计 (管理员)**\n\n"
        f"👥 **注册用户**: `{user_count}` 人\n"
        f"📂 **合集总数**: `{col_count}` 个\n"
        f"📄 **文件总存量**: `{file_count}` 个\n\n"
        f"✅ 系统运行正常。"
    )


@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_cmd(client: Client, message: Message):
    """取消当前操作，返回主菜单"""
    await message.reply_text(
        "🚫 操作已取消。",
        reply_markup=None # Remove ForceReply ifany
    )
    from handlers.setup import send_main_menu
    await send_main_menu(client, message)


