import socketio

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
    logger=False,
    engineio_logger=False
)

@sio.event
async def connect(sid, environ):
    print(f"[Socket.IO] Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"[Socket.IO] Client disconnected: {sid}")

@sio.event
async def join_conversation(sid, data):
    conversation_id = data.get("conversation_id")
    if conversation_id:
        await sio.enter_room(sid, f"conv_{conversation_id}")

async def emit_new_message(conversation_id: str, message_data: dict):
    """Gửi tin nhắn mới đến tất cả clients đang xem conversation này"""
    await sio.emit("new_message", message_data, room=f"conv_{conversation_id}")

async def emit_conversation_update(conversation_data: dict):
    """Cập nhật danh sách conversation cho tất cả clients"""
    await sio.emit("conversation_updated", conversation_data)

async def emit_ai_typing(conversation_id: str, is_typing: bool):
    """Hiển thị trạng thái AI đang gõ"""
    await sio.emit("ai_typing", {"typing": is_typing}, room=f"conv_{conversation_id}")
