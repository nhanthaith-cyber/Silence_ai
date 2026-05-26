import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

ROUTER_PROMPT = """You are the ROUTER AGENT for a premium fashion e-commerce brand.
Your job is to read the customer's message and determine the INTENTS and REQUIRED AGENTS to route the request properly.

Detect any of the following intents:
- "sizing": Questions about size, fit, height, weight.
- "product": Questions about fabric, design, product details.
- "logistics": Questions about shipping, tracking, delivery delays.
- "complaint": Expressions of frustration, anger, negative feedback, or issues.
- "return": Exchange or refund requests.
- "styling": Asking for fashion advice, combinations, outfits.
- "conversion": Hesitation to buy, comparing products, asking for opinions.
- "promotion": Asking for discounts, sales, vouchers.
- "general": Greetings, generic chatter.

Based on the intents, determine the required agents from the following list:
- "Size Recommendation Agent": For "sizing".
- "Product Knowledge Agent": For "product", "styling".
- "Logistics Agent": For "logistics".
- "Complaint Recovery Agent": For "complaint", "return".
- "Sales Conversion Agent": For "conversion", "promotion".

Output strictly in JSON format as follows:
{
    "detected_intents": ["<intent1>", "<intent2>"],
    "confidence_score": <float 0.0-1.0>,
    "required_agents": ["<agent1>", "<agent2>"],
    "routing_plan": "<Brief explanation of why these agents are chosen>"
}
"""

ROUTER_FUNCTION = {
    "type": "function",
    "function": {
        "name": "route_customer_message",
        "description": "Determine the intents and route to appropriate agents.",
        "parameters": {
            "type": "object",
            "properties": {
                "detected_intents": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "confidence_score": {"type": "number"},
                "required_agents": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "routing_plan": {"type": "string"}
            },
            "required": ["detected_intents", "confidence_score", "required_agents", "routing_plan"]
        }
    }
}

async def execute_router(openai_client, user_message: str, history: List[Dict[str, str]]) -> Dict[str, Any]:
    """Execute the Router Agent."""
    if not openai_client:
        return _mock_router(user_message)

    try:
        messages = [{"role": "system", "content": ROUTER_PROMPT}]
        # Giới hạn history cho router để tập trung vào context gần nhất
        messages.extend(history[-3:])
        messages.append({"role": "user", "content": user_message})

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini", # Use faster model for routing
            messages=messages,
            tools=[ROUTER_FUNCTION],
            tool_choice={"type": "function", "function": {"name": "route_customer_message"}},
            temperature=0.0
        )
        
        tool_call = response.choices[0].message.tool_calls[0]
        result = json.loads(tool_call.function.arguments)
        return result
    except Exception as e:
        logger.error(f"[Router Agent] Error: {e}")
        return _mock_router(user_message)

def _mock_router(user_message: str) -> Dict[str, Any]:
    """Fallback router logic using keyword matching."""
    user_lower = user_message.lower()
    intents = []
    agents = []
    
    if any(w in user_lower for w in ["size", "cỡ", "mặc vừa", "m7"]):
        intents.append("sizing")
        agents.append("Size Recommendation Agent")
    if any(w in user_lower for w in ["vải", "chất liệu", "mẫu"]):
        intents.append("product")
        agents.append("Product Knowledge Agent")
    if any(w in user_lower for w in ["giao hàng", "đơn", "ship"]):
        intents.append("logistics")
        agents.append("Logistics Agent")
    if any(w in user_lower for w in ["lỗi", "tệ", "chán", "thất vọng", "rách"]):
        intents.append("complaint")
        agents.append("Complaint Recovery Agent")
    if any(w in user_lower for w in ["đổi", "trả", "hoàn"]):
        intents.append("return")
        agents.append("Complaint Recovery Agent")
    if any(w in user_lower for w in ["phối", "mix"]):
        intents.append("styling")
        agents.append("Product Knowledge Agent")
    if any(w in user_lower for w in ["nên mua", "phân vân"]):
        intents.append("conversion")
        agents.append("Sales Conversion Agent")
    if any(w in user_lower for w in ["giảm giá", "sale", "voucher"]):
        intents.append("promotion")
        agents.append("Sales Conversion Agent")
        
    if not intents:
        intents.append("general")
        
    return {
        "detected_intents": intents,
        "confidence_score": 0.8,
        "required_agents": list(set(agents)),
        "routing_plan": "Fallback mock routing based on keywords."
    }
