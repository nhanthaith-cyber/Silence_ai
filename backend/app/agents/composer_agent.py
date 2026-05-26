import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

COMPOSER_PROMPT = """You are the RESPONSE COMPOSER AGENT for a premium fashion e-commerce brand.
ROLE: Merge outputs from all specialist agents, maintain consistent tone, and generate the final customer response.
REQUIREMENTS:
- Final response must feel: natural, human, premium, concise, emotionally stable, operationally aware.
- The customer must never feel: multiple agents exist, robotic coordination, internal system complexity.
- Use natural Vietnamese.
- Avoid robotic structure.
- Avoid excessive bullet points.
- Use short readable paragraphs.

You will receive the thoughts/analysis from the specialist agents. 
Synthesize them into one single, cohesive, premium reply to the customer.

Output strictly in JSON format as follows:
{
    "final_reply": "<The exact string to send to the customer>",
    "needs_human": <boolean>,
    "escalation_reason": "<string or null>",
    "emotion_level": "<neutral, mild_concern, annoyed, angry>"
}
"""

COMPOSER_FUNCTION = {
    "type": "function",
    "function": {
        "name": "compose_final_response",
        "description": "Generate the final response based on specialist agents' input.",
        "parameters": {
            "type": "object",
            "properties": {
                "final_reply": {"type": "string"},
                "needs_human": {"type": "boolean"},
                "escalation_reason": {"type": "string"},
                "emotion_level": {
                    "type": "string",
                    "enum": ["neutral", "mild_concern", "annoyed", "angry"]
                }
            },
            "required": ["final_reply", "needs_human", "emotion_level"]
        }
    }
}

async def execute_composer(openai_client, user_message: str, specialist_outputs: Dict[str, str], history: List[Dict[str, str]]) -> Dict[str, Any]:
    """Execute the Composer Agent."""
    
    # Format the inputs from specialists
    specialist_context = "\n\n=== SPECIALIST AGENTS ANALYSIS ===\n"
    for agent, output in specialist_outputs.items():
        specialist_context += f"[{agent}]: {output}\n\n"
        
    full_prompt = COMPOSER_PROMPT + specialist_context
    
    if not openai_client:
        return _mock_composer(user_message, specialist_outputs)

    try:
        messages = [{"role": "system", "content": full_prompt}]
        messages.extend(history[-4:])
        messages.append({"role": "user", "content": user_message})

        response = await openai_client.chat.completions.create(
            model="gpt-4o", # Use the best model for final composition
            messages=messages,
            tools=[COMPOSER_FUNCTION],
            tool_choice={"type": "function", "function": {"name": "compose_final_response"}},
            temperature=0.7
        )
        
        tool_call = response.choices[0].message.tool_calls[0]
        result = json.loads(tool_call.function.arguments)
        return result
    except Exception as e:
        logger.error(f"[Composer Agent] Error: {e}")
        return _mock_composer(user_message, specialist_outputs)


def _mock_composer(user_message: str, specialist_outputs: Dict[str, str]) -> Dict[str, Any]:
    """Fallback logic for composer."""
    
    reply = "Dạ, em đã nhận được thông tin. "
    if "Size Recommendation Agent" in specialist_outputs:
        reply += "Về size, em nghĩ mẫu này anh/chị mặc sẽ rất vừa vặn ạ. "
    if "Product Knowledge Agent" in specialist_outputs:
        reply += "Chất liệu mẫu này rất thoải mái và thoáng mát. "
    if "Logistics Agent" in specialist_outputs:
        reply += "Đơn hàng của mình đang được xử lý giao đi ạ. "
    if "Complaint Recovery Agent" in specialist_outputs:
        reply = "Em rất xin lỗi về trải nghiệm không tốt vừa qua. Em sẽ ghi nhận và xử lý ngay cho anh/chị. "
        
    return {
        "final_reply": reply.strip(),
        "needs_human": "Complaint" in reply,
        "escalation_reason": "Khách khiếu nại" if "Complaint" in reply else None,
        "emotion_level": "neutral"
    }
