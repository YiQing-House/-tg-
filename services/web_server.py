from aiohttp import web
import os
import mimetypes
from config import LOCAL_STORAGE_PATH, WEB_SERVER_PORT, WEB_SERVER_HOST

async def handle_file_request(request):
    """Serve files with Range support (for video streaming)"""
    filename = request.match_info.get('filename', '')
    if not filename:
        return web.Response(status=404, text="Filename missing")
    
    # 防止目录遍历攻击
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(LOCAL_STORAGE_PATH, safe_filename)
    
    if not os.path.exists(file_path):
        return web.Response(status=404, text="File not found")

    # 使用 Python 的 mimetypes 猜测类型
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = 'application/octet-stream'

    # aiohttp 的 FileResponse 自动支持 Range Header (断点续传/拖动进度条)
    return web.FileResponse(file_path, headers={'Content-Type': mime_type})

async def start_web_server():
    app = web.Application()
    # 路由: /file/{filename}
    app.router.add_get('/file/{filename}', handle_file_request)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)
    
    print(f"🎬 Web Stream Server running on http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
    await site.start()
