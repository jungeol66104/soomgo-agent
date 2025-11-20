"""Core agent implementation."""

import json
import operator
import os
from pathlib import Path
from typing import Annotated, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from .config import AgentConfig
from src.knowledge import KnowledgeRetriever

# Load environment
load_dotenv()


@tool
def count_characters(text: str, include_spaces: bool = True) -> dict:
    """
    Count characters in a text string accurately.

    Use this tool when you need to count characters precisely. DO NOT guess or estimate.

    Args:
        text: The text to count characters in
        include_spaces: If True, count spaces. If False, exclude spaces. Default is True.

    Returns:
        Dictionary with character counts:
        - total_with_spaces: Total character count including spaces
        - total_without_spaces: Total character count excluding spaces
        - spaces: Number of space characters
        - lines: Number of lines
    """
    total_with_spaces = len(text)
    total_without_spaces = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
    spaces = text.count(" ")
    lines = text.count("\n") + 1 if text else 0

    return {
        "total_with_spaces": total_with_spaces,
        "total_without_spaces": total_without_spaces,
        "spaces": spaces,
        "lines": lines,
        "result": total_with_spaces if include_spaces else total_without_spaces
    }


class GatheredInfo(TypedDict):
    """Information to gather from customer."""
    service_type: Optional[str]      # 서비스 종류
    company_role: Optional[str]      # 회사/직무
    deadline: Optional[str]          # 마감일
    experience: Optional[str]        # 경력
    existing_resume: Optional[str]   # 기존 자소서 (optional)
    difficulties: Optional[str]      # 어려움
    budget: Optional[str]            # 예산


class ChatState(TypedDict):
    """State for the conversation."""
    messages: Annotated[list, operator.add]
    gathered_info: GatheredInfo
    conversation_state: Literal["active", "waiting", "deferred", "closed"]
    last_closure_response: Optional[str]
    retrieved_knowledge: Optional[str]  # Knowledge from retrieval system


class SoomgoAgent:
    """Soomgo provider agent."""

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize agent.

        Args:
            config: Agent configuration (defaults to AgentConfig.from_env())
        """
        self.config = config or AgentConfig.from_env()
        self.system_prompt = self._load_prompt()

        # Initialize knowledge retriever
        logger.info("Initializing knowledge retriever...")
        self.retriever = KnowledgeRetriever(data_dir=str(self.config.knowledge_dir))

        self.graph = self._build_graph()

        logger.info(f"Initialized SoomgoAgent with {self.config.model}")

    def _load_prompt(self) -> str:
        """Load system prompt from file."""
        prompt_path = self.config.prompt_path

        if not prompt_path.exists():
            logger.warning(f"Prompt file not found: {prompt_path}")
            return "당신은 숨고 전문가입니다. 고객에게 친절하게 응답하세요."

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()

        logger.info(f"Loaded prompt from {prompt_path} ({len(prompt)} chars)")
        return prompt

    def _build_graph(self) -> CompiledStateGraph:
        """Build LangGraph workflow with information extraction and knowledge retrieval."""
        graph_builder = StateGraph(ChatState)

        # Add nodes
        graph_builder.add_node("extract_info", self._extract_information)
        graph_builder.add_node("retrieve_knowledge", self._retrieve_knowledge)
        graph_builder.add_node("agent", self._run_agent)

        # Build workflow: START -> extract info -> retrieve knowledge -> generate response -> END
        graph_builder.add_edge(START, "extract_info")
        graph_builder.add_edge("extract_info", "retrieve_knowledge")
        graph_builder.add_edge("retrieve_knowledge", "agent")
        graph_builder.add_edge("agent", END)

        return graph_builder.compile()

    def _extract_information(self, state: ChatState) -> dict:
        """Extract information and conversation state from user's latest message."""
        messages = state["messages"]
        current_info = state.get("gathered_info", {})
        current_conv_state = state.get("conversation_state", "active")
        last_closure = state.get("last_closure_response")

        # Get latest user message
        user_messages = [m for m in messages if isinstance(m, HumanMessage)]
        if not user_messages:
            return {
                "gathered_info": current_info,
                "conversation_state": current_conv_state,
                "last_closure_response": last_closure
            }

        latest_message = user_messages[-1].content

        # Get last agent message to check if we already gave closure response
        agent_messages = [m for m in messages if isinstance(m, AIMessage)]
        last_agent_msg = agent_messages[-1].content if agent_messages else None

        # Extraction prompt with conversation state detection
        extraction_prompt = f"""당신은 고객 메시지에서 필요한 정보와 대화 상태를 추출하는 전문가입니다.

**고객 메시지:**
{latest_message}

**현재 대화 상태:** {current_conv_state}
**이전 에이전트 응답:** {last_agent_msg if last_agent_msg else "없음"}

**작업 1: 정보 추출**
다음 정보를 추출하세요 (명시되지 않으면 null):
- service_type: 서비스 종류 (자소서, 이력서, 면접, 포트폴리오 등)
- company_role: 회사/직무
- deadline: 마감일
- experience: 경력
- existing_resume: 기존 자소서 보유 여부
- difficulties: 어려움/고민
- budget: 예산

**현재까지 수집된 정보:**
{json.dumps(current_info, ensure_ascii=False)}

**작업 2: 대화 상태 감지**
고객의 메시지를 보고 대화 상태를 판단하세요:

- "active": 정보 수집 중, 질문에 답변 중
- "waiting": 파일/자료를 보낸다고 함 (예: "보낼게요", "파일 보내드릴게요")
- "deferred": 고민/보류한다고 함 (예: "고려해볼게요", "생각해볼게요", "다시 연락드릴게요")
- "closed": deferred 상태 후 짧은 확인만 함 (예: "네", "네!", "감사합니다")

**판단 규칙:**
1. 고객이 "고려해볼게요", "생각해볼게요", "다시 연락드릴게요" → deferred
2. 현재 상태가 deferred이고, 고객이 "네", "네!", "알겠습니다", "감사합니다"만 보냄 → closed
3. 고객이 "파일 보낼게요", "자소서 보내드릴게요" → waiting
4. 그 외 → active

**출력 형식 (JSON):**
{{
  "service_type": "...",
  "company_role": "...",
  "deadline": "...",
  "experience": "...",
  "existing_resume": "...",
  "difficulties": "...",
  "budget": "...",
  "conversation_state": "active|waiting|deferred|closed"
}}
"""

        # Call LLM with JSON mode
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            extractor = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.0,
                api_key=api_key,
            )

            response = extractor.invoke(
                [HumanMessage(content=extraction_prompt)],
                response_format={"type": "json_object"}
            )

            extracted = json.loads(response.content)

            # Extract conversation state
            new_conv_state = extracted.pop("conversation_state", current_conv_state)

            # Merge info with current info (only update non-null values)
            updated_info = current_info.copy()
            for key, value in extracted.items():
                if value is not None and value != "null" and value.strip() != "":
                    updated_info[key] = value

            logger.debug(f"Extracted info: {extracted}")
            logger.debug(f"Conversation state: {current_conv_state} -> {new_conv_state}")
            logger.debug(f"Updated info: {updated_info}")

            return {
                "gathered_info": updated_info,
                "conversation_state": new_conv_state,
                "last_closure_response": last_closure
            }

        except Exception as e:
            logger.error(f"Error extracting information: {e}")
            return {
                "gathered_info": current_info,
                "conversation_state": current_conv_state,
                "last_closure_response": last_closure
            }

    def _retrieve_knowledge(self, state: ChatState) -> dict:
        """Retrieve relevant knowledge for the user's latest message."""
        messages = state["messages"]
        gathered_info = state.get("gathered_info", {})

        # Get latest user message
        user_messages = [m for m in messages if isinstance(m, HumanMessage)]
        if not user_messages:
            return {"retrieved_knowledge": None}

        latest_message = user_messages[-1].content

        # Build context-aware query
        # If user asks generic question like "얼마인가요?", add service context
        query = latest_message
        service_type = gathered_info.get("service_type")

        # Enhance query with context if it's too generic
        if len(latest_message) < 20 and service_type:
            # Generic queries like "얼마인가요?", "가격은?"
            query = f"{service_type} {latest_message}"
            logger.debug(f"Enhanced query with context: '{latest_message}' -> '{query}'")

        try:
            # Retrieve knowledge (lower threshold for better recall)
            retrieved = self.retriever.retrieve(query, top_k=3, threshold=0.4)

            # Format knowledge
            if retrieved.get("structured") or retrieved.get("faqs"):
                formatted = self.retriever.format_knowledge(retrieved)
                logger.debug(f"Retrieved knowledge ({len(formatted)} chars)")
                return {"retrieved_knowledge": formatted}
            else:
                logger.debug("No relevant knowledge found")
                return {"retrieved_knowledge": None}

        except Exception as e:
            logger.error(f"Error retrieving knowledge: {e}")
            return {"retrieved_knowledge": None}

    def _run_agent(self, state: ChatState) -> dict:
        """Run agent node with state-aware prompting."""
        messages = state["messages"]
        gathered_info = state.get("gathered_info", {})
        conv_state = state.get("conversation_state", "active")
        last_closure = state.get("last_closure_response")
        retrieved_knowledge = state.get("retrieved_knowledge")

        # Build state-aware system prompt with conversation state
        state_summary = self._build_state_summary(gathered_info)
        conv_state_instructions = self._build_conversation_state_instructions(conv_state, last_closure)

        # Build knowledge section if available
        knowledge_section = ""
        if retrieved_knowledge:
            knowledge_section = f"""

## 📚 관련 지식 (참고용)
{retrieved_knowledge}

**지시사항:** 위 정보를 참고하되, 자연스럽게 답변하세요. 정보를 그대로 읽지 말고 대화 맥락에 맞게 사용하세요."""

        full_prompt = f"""{self.system_prompt}

{state_summary}

{conv_state_instructions}{knowledge_section}"""

        # Add system message if needed
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=full_prompt)] + messages
        else:
            # Update existing system message with state
            messages = [SystemMessage(content=full_prompt)] + [m for m in messages if not isinstance(m, SystemMessage)]

        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env")

        # Initialize model
        model = ChatOpenAI(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            api_key=api_key,
        )

        # Bind tools to model
        tools = [count_characters]
        model_with_tools = model.bind_tools(tools)

        # Generate response with tool support
        try:
            response = model_with_tools.invoke(messages)

            # Handle tool calls if any
            while response.tool_calls:
                logger.debug(f"Tool calls detected: {len(response.tool_calls)}")

                # Add AI message with tool calls to history
                messages.append(response)

                # Execute each tool call
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]

                    logger.debug(f"Executing tool: {tool_name} with args: {tool_args}")

                    # Execute the tool
                    if tool_name == "count_characters":
                        tool_result = count_characters.invoke(tool_args)
                    else:
                        tool_result = {"error": f"Unknown tool: {tool_name}"}

                    # Create tool message with result
                    tool_message = ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_id
                    )
                    messages.append(tool_message)

                # Get next response from model
                response = model_with_tools.invoke(messages)

            response_text = response.content
            logger.debug(f"Generated response: {len(response_text)} chars")

            # Track closure responses to prevent repetition
            updated_closure = last_closure
            if conv_state in ["deferred", "waiting"]:
                # Check if response contains closure phrases
                closure_phrases = ["편하실 때", "기다릴게요", "연락 주세요", "언제든지"]
                if any(phrase in response_text for phrase in closure_phrases):
                    updated_closure = response_text
                    logger.debug(f"Tracked closure response: {updated_closure[:50]}...")

            return {
                "messages": [response],
                "last_closure_response": updated_closure
            }

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            error_msg = AIMessage(
                content="죄송합니다. 응답 생성 중 오류가 발생했습니다."
            )
            return {"messages": [error_msg]}

    def _build_state_summary(self, gathered_info: dict) -> str:
        """Build state summary for system prompt."""
        # Required fields
        required_fields = {
            "service_type": "서비스 종류",
            "company_role": "회사/직무",
            "deadline": "마감일",
            "experience": "경력",
            "difficulties": "어려움",
            "budget": "예산"
        }

        # Optional field
        optional_fields = {
            "existing_resume": "기존 자소서"
        }

        # Check what we have
        collected = []
        missing = []

        for key, label in required_fields.items():
            value = gathered_info.get(key)
            if value:
                collected.append(f"- {label}: {value}")
            else:
                missing.append(f"- {label} ✗")

        # Add optional field if present
        for key, label in optional_fields.items():
            value = gathered_info.get(key)
            if value:
                collected.append(f"- {label} (선택): {value}")

        # Build summary
        if not collected and not missing:
            return """
## 현재 상태

아직 수집된 정보가 없습니다. 자연스러운 대화를 통해 다음 정보를 파악해야 합니다:
- 서비스 종류 (자소서, 이력서, 면접, 포트폴리오 등)
- 회사/직무
- 마감일
- 경력 (신입/경력)
- 어려움이나 고민
- 예산

**중요**: 한 번에 모든 것을 물어보지 마세요. 고객이 방금 말한 내용과 자연스럽게 연결되는 1-2가지만 물어보세요.
"""

        summary = "\n## 현재 진행 상황\n"

        if collected:
            summary += "\n### ✓ 파악된 정보:\n" + "\n".join(collected)

        if missing:
            summary += "\n\n### 아직 필요한 정보:\n" + "\n".join(missing)

        summary += """

**중요**: 자연스러운 대화 흐름을 유지하세요. 고객이 방금 말한 내용과 연결되는 1-2가지만 물어보세요. 필요한 모든 정보를 한 번에 물어보지 마세요.
"""

        return summary

    def _build_conversation_state_instructions(self, conv_state: str, last_closure: Optional[str]) -> str:
        """Build dynamic instructions based on conversation state."""

        if conv_state == "closed":
            return """
## 🚨 대화 종료 상태

고객이 이미 고민/보류를 확인했습니다. 대화는 끝났습니다.

**지시사항:**
- "네!" 하나만 응답하세요
- 또는 아무 응답도 하지 마세요
- 절대 "기다릴게요", "편하실 때", "언제든지" 같은 말 반복하지 마세요
- 이미 마무리 인사를 했습니다

**예시:**
고객: "네!"
나: "네!"
"""

        elif conv_state == "deferred":
            if last_closure:
                return f"""
## ⚠️ 대화 보류 중 - 이미 마무리 인사함

고객이 고민하겠다고 했고, 당신은 이미 다음과 같이 응답했습니다:
"{last_closure[:100]}..."

**지시사항:**
- 같은 내용 반복하지 마세요
- 고객이 다시 "네"라고만 하면 "네!" 하나로 응답
- 더 이상 "기다릴게요" 같은 말 하지 마세요
"""
            else:
                return """
## ⏸️ 대화 보류 상태

고객이 고민/보류하겠다고 했습니다.

**지시사항:**
- 간단히 한 번만 응답하세요: "편하실 때 연락 주세요" 또는 "네! 고민해보시고 편하실 때 연락 주세요"
- 20-30자 정도로 짧게
- 이 응답 후, 고객이 "네"라고만 하면 "네!"로만 답하세요
"""

        elif conv_state == "waiting":
            if last_closure:
                return f"""
## 📎 파일 대기 중 - 이미 확인함

고객이 파일을 보낸다고 했고, 당신은 이미 다음과 같이 응답했습니다:
"{last_closure[:100]}..."

**지시사항:**
- 같은 내용 반복하지 마세요
- 고객이 "네"라고만 하면 "네!" 또는 "기다릴게요!" 짧게만
- 더 이상 설명하지 마세요
"""
            else:
                return """
## 📎 파일 대기 상태

고객이 파일이나 자료를 보낸다고 했습니다.

**지시사항:**
- "기다릴게요!" 또는 "파일 확인하고 바로 도와드릴게요" 짧게만
- 10-20자 정도
- 이 응답 후, 고객이 "네"라고만 하면 "네!"로만 답하세요
"""

        else:  # active
            return """
## ✅ 활성 대화 상태

일반적인 정보 수집이나 대화가 진행 중입니다. 자연스럽게 대화하세요.
"""

    def chat(
        self,
        user_message: str,
        conversation_history: Optional[list[dict]] = None,
        gathered_info: Optional[dict] = None,
        conversation_state: Optional[str] = None,
        last_closure_response: Optional[str] = None
    ) -> tuple[str, dict, str, Optional[str]]:
        """
        Send a message and get response.

        Args:
            user_message: Customer's message
            conversation_history: Previous messages [{"role": "user"|"assistant", "content": "..."}]
            gathered_info: Previously gathered information
            conversation_state: Current conversation state
            last_closure_response: Last closure response given

        Returns:
            Tuple of (Agent's response, Updated gathered_info, conversation_state, last_closure_response)
        """
        # Build messages
        messages = []

        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_message))

        # Initialize gathered_info if not provided
        if gathered_info is None:
            gathered_info = {
                "service_type": None,
                "company_role": None,
                "deadline": None,
                "experience": None,
                "existing_resume": None,
                "difficulties": None,
                "budget": None
            }

        # Initialize conversation state if not provided
        if conversation_state is None:
            conversation_state = "active"

        # Invoke graph
        try:
            result = self.graph.invoke({
                "messages": messages,
                "gathered_info": gathered_info,
                "conversation_state": conversation_state,
                "last_closure_response": last_closure_response
            })
            response = result["messages"][-1].content
            updated_info = result.get("gathered_info", gathered_info)
            updated_state = result.get("conversation_state", conversation_state)
            updated_closure = result.get("last_closure_response", last_closure_response)

            return response, updated_info, updated_state, updated_closure

        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return "죄송합니다. 오류가 발생했습니다.", gathered_info, conversation_state, last_closure_response

    def reset(self):
        """Reset the agent (currently stateless, but kept for future use)."""
        logger.info("Agent reset requested (currently stateless)")
