"""
Gemini Client Wrapper - dùng google-genai SDK mới nhất
"""
import json
import asyncio
from app.core.config import settings

_gemini_client = None


def get_gemini_client():
    """Khởi tạo Gemini client nếu có API key."""
    global _gemini_client
    if _gemini_client is None and settings.GEMINI_API_KEY:
        from google import genai
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client


async def gemini_chat(
    system_prompt: str,
    messages: list,
    user_message: str,
    response_schema: dict = None
) -> str:
    """
    Gọi Gemini API async.
    Trả về text response.
    """
    client = get_gemini_client()
    if not client:
        raise ValueError("Gemini client not initialized. Check GEMINI_API_KEY.")

    # Build full prompt
    full_prompt = f"{system_prompt}\n\n"

    # Add history
    for msg in messages[-6:]:
        role = "Khách hàng" if msg.get("role") == "user" else "Nhân viên AI"
        full_prompt += f"{role}: {msg.get('content', '')}\n"

    # Add JSON schema instruction if needed
    if response_schema:
        schema_str = json.dumps(response_schema, ensure_ascii=False, indent=2)
        full_prompt += (
            f"\nHãy trả lời ĐÚNG theo format JSON sau "
            f"(chỉ trả về JSON, không thêm gì khác):\n{schema_str}\n\n"
        )

    full_prompt += f"Khách hàng: {user_message}\nNhân viên AI:"

    from google import genai as _genai
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=full_prompt
        )
    )

    return response.text


async def gemini_embed(text: str) -> list:
    """Tạo embedding dùng Gemini embedding model."""
    if not settings.GEMINI_API_KEY:
        return [0.0] * 768

    client = get_gemini_client()
    if not client:
        return [0.0] * 768

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: client.models.embed_content(
            model="models/text-embedding-004",
            contents=text
        )
    )
    return result.embeddings[0].values


async def gemini_embed_query(text: str) -> list:
    """Tạo embedding cho query tìm kiếm."""
    return await gemini_embed(text)
