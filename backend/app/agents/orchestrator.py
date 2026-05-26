import logging
import asyncio
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.models import Conversation
from app.agents.router_agent import execute_router
from app.agents.specialist_agents import execute_specialist
from app.agents.composer_agent import execute_composer

logger = logging.getLogger(__name__)

class MultiAgentOrchestrator:
    def __init__(self, openai_client, db: Session):
        self.openai_client = openai_client
        self.db = db

    async def process_message(
        self, 
        user_message: str, 
        conversation: Conversation, 
        platform: str,
        customer_memory: dict = None,
        product_context: str = None,
        history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Main orchestration flow:
        1. Router Agent
        2. Execute Specialist Agents (Parallel)
        3. Composer Agent
        """
        history = history or []

        # 1. Router Agent
        logger.info(f"[{conversation.id}] Running Router Agent...")
        router_result = await execute_router(self.openai_client, user_message, history)
        
        intents = router_result.get("detected_intents", ["general"])
        required_agents = router_result.get("required_agents", [])
        
        # Build shared context for specialists
        shared_context = f"Platform: {platform}\n"
        if customer_memory:
            from app.services.memory_service import format_memory_for_prompt
            shared_context += "\n--- CUSTOMER MEMORY ---\n" + format_memory_for_prompt(customer_memory)
        if product_context:
            shared_context += "\n--- PRODUCT KNOWLEDGE ---\n" + product_context

        # 2. Execute Specialist Agents (Parallel)
        specialist_outputs = {}
        if not required_agents:
            logger.info(f"[{conversation.id}] No specific agents required by router. Proceeding to Composer directly.")
            specialist_outputs["General"] = "No specialized intent detected. Respond naturally."
        else:
            logger.info(f"[{conversation.id}] Running Specialist Agents: {required_agents}")
            # Create async tasks for parallel execution
            tasks = []
            for agent_name in required_agents:
                tasks.append(
                    self._run_specialist_task(agent_name, user_message, shared_context, history)
                )
            
            results = await asyncio.gather(*tasks)
            for agent_name, result_text in results:
                specialist_outputs[agent_name] = result_text
        
        # 3. Composer Agent
        logger.info(f"[{conversation.id}] Running Composer Agent...")
        composer_result = await execute_composer(self.openai_client, user_message, specialist_outputs, history)

        # 4. Return formatted response for message_service compatibility
        return {
            "reply": composer_result.get("final_reply", "Xin lỗi, em chưa thể trả lời lúc này."),
            "confidence": router_result.get("confidence_score", 0.8),
            "should_handoff": composer_result.get("needs_human", False),
            "category": "general", # Simplified for now
            "intent": intents[0] if intents else "general",
            "emotion_level": composer_result.get("emotion_level", "neutral"),
            "memory_updates": None, # Will add memory agent later
            "escalation_reason": composer_result.get("escalation_reason")
        }

    async def _run_specialist_task(self, agent_name: str, user_message: str, context: str, history: List[Dict[str, str]]):
        """Helper to run specialist and return a tuple of (name, output)"""
        output = await execute_specialist(self.openai_client, agent_name, user_message, context, history)
        return (agent_name, output)
