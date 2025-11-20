# VF-Data CLI Agent - Quick Reference

## System Overview

```
User Input (CLI)
    ↓
SoomgoAgent.chat() method
    ↓
LangGraph Workflow Execution:
    ├─ Node 1: extract_info (Parse intent, gather data)
    ├─ Node 2: retrieve_knowledge (Fetch FAQs, pricing)
    └─ Node 3: agent (Generate response with LLM)
    ↓
Agent Response
```

---

## Key Files

| What | Where | Why |
|------|-------|-----|
| Main agent class | `/src/agent/core.py` | All agent logic here |
| CLI interface | `/cli/chat.py` | User interaction |
| Knowledge base | `/data/knowledge/` | Pricing, FAQs, policies |
| Configuration | `/src/agent/config.py` | Model settings |
| Retriever | `/src/knowledge/retriever.py` | Knowledge lookup |

---

## Current State Structure

```python
ChatState = {
    "messages": [...],                    # Conversation history
    "gathered_info": {                    # Customer data
        "service_type": str,              # 자소서, 이력서, etc.
        "company_role": str,              # Job type
        "deadline": str,                  # Due date
        "experience": str,                # Experience level
        "existing_resume": str,           # Has existing data?
        "difficulties": str,              # Pain points
        "budget": str                     # Budget
    },
    "conversation_state": str,            # active|waiting|deferred|closed
    "last_closure_response": str,         # Last farewell message
    "retrieved_knowledge": str            # Knowledge from retrieval
}
```

---

## Adding a Tool: 3 Steps

### Step 1: Write the Function
```python
def _my_tool(self, state: ChatState) -> dict:
    """Do something useful."""
    # Access state data
    gathered_info = state.get("gathered_info")
    messages = state["messages"]
    
    # Do work
    result = some_operation()
    
    # Return updates to state
    return {"field_name": result}
```

### Step 2: Update State (If Needed)
```python
class ChatState(TypedDict):
    messages: Annotated[list, operator.add]
    # ... existing fields ...
    field_name: Optional[str]  # NEW FIELD
```

### Step 3: Register in Graph
```python
def _build_graph(self) -> CompiledStateGraph:
    graph_builder = StateGraph(ChatState)
    
    # Add your node
    graph_builder.add_node("my_tool", self._my_tool)
    
    # Connect edges
    graph_builder.add_edge("previous_node", "my_tool")
    graph_builder.add_edge("my_tool", "next_node")
    
    return graph_builder.compile()
```

---

## Tool Registration Points

### Only File to Modify
**`/src/agent/core.py`**

**Register here**: Lines 78-93 in `_build_graph()` method

---

## Graph Node Operations

### Standard Node (Always Execute)
```python
graph_builder.add_edge("node_a", "my_node")
graph_builder.add_edge("my_node", "node_b")
```

### Conditional Routing
```python
graph_builder.add_conditional_edges(
    "from_node",
    self._my_router,  # Function returning node name
    {
        "path_a": "node_a",
        "path_b": "node_b"
    }
)

def _my_router(self, state: ChatState) -> str:
    if condition:
        return "path_a"
    return "path_b"
```

---

## State Access Patterns

### Read from State
```python
value = state.get("field_name")                    # Safe read
value = state["field_name"]                        # Direct read
messages = state["messages"]                       # Message list
info = state["gathered_info"]                      # Customer info
```

### Update State
```python
return {
    "field_name": new_value,
    "messages": [new_message],
    "gathered_info": updated_info
}
```

### Access Latest User Message
```python
messages = state["messages"]
user_messages = [m for m in messages if isinstance(m, HumanMessage)]
latest = user_messages[-1].content if user_messages else ""
```

---

## Message Types

```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Create messages
human_msg = HumanMessage(content="User said this")
ai_msg = AIMessage(content="Agent responded with this")
sys_msg = SystemMessage(content="System instruction")
```

---

## Knowledge Retrieval

```python
# Already integrated in Node 2 (_retrieve_knowledge)
# Returns: {"structured": {...}, "faqs": [...]}

# Access in other nodes:
retrieved_knowledge = state.get("retrieved_knowledge")
if retrieved_knowledge:
    # Use it in prompt
```

---

## Testing Your Changes

```bash
# Run the agent CLI
python cli/chat.py

# Or in Python:
from src.agent import SoomgoAgent

agent = SoomgoAgent()
response, info, state, closure = agent.chat(
    "자소서 가격이 얼마예요?",
    [],  # history
    None,  # gathered_info
    None,  # conversation_state
    None   # last_closure_response
)
print(response)
```

---

## Common Mistakes & Fixes

| Problem | Solution |
|---------|----------|
| Tool never runs | Check edges in `_build_graph()` |
| State not updating | Return `{"field": value}` from node |
| Can't access state field | Add field to `ChatState` TypedDict |
| Router not working | Verify returns exact node name string |
| Conditional never triggers | Check router logic and conditions |

---

## Node Execution Order

```
START
  ↓
extract_info (Parse user intent)
  ↓
retrieve_knowledge (Get relevant knowledge)
  ↓
agent (Generate response)
  ↓
END
```

Each node receives full state, can read/write it.

---

## Configuration

File: `/src/agent/config.py`

```python
model: str = "gpt-4o-mini"              # LLM model
temperature: float = 0.85               # Response variability
max_tokens: int = 300                   # Max response length
prompt_path: Path = "prompts/base_prompt.txt"  # System prompt
```

Override via environment:
```bash
export AGENT_MODEL="gpt-4o"
export AGENT_TEMPERATURE="0.7"
```

---

## Debugging Tips

### Log State
```python
def _my_tool(self, state: ChatState) -> dict:
    from loguru import logger
    logger.debug(f"State: {state}")
    return {}
```

### View Graph
```python
graph = self._build_graph()
print(graph.get_graph().draw_ascii())
```

### Print Messages
```python
messages = state["messages"]
for m in messages:
    print(f"{type(m).__name__}: {m.content}")
```

---

## File Locations

```
/Users/joonnam/Workspace/vf-data/

Core Agent:
  src/agent/
    ├── core.py           ← MAIN FILE (only one you need to edit)
    ├── config.py
    └── __init__.py

Knowledge:
  src/knowledge/
    └── retriever.py
  
  data/knowledge/
    ├── structured/
    │   ├── services.json
    │   └── policies.json
    └── semantic/
        └── faq.json

CLI:
  cli/
    └── chat.py           ← User interface

Prompts:
  prompts/
    └── base_prompt.txt   ← System prompt
```

---

## LangGraph Imports

```python
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from typing import TypedDict, Annotated, Literal, Optional
import operator
```

---

## Example: Add a Price Lookup Tool

```python
# 1. Add function
def _lookup_price(self, state: ChatState) -> dict:
    gathered_info = state.get("gathered_info", {})
    service_type = gathered_info.get("service_type")
    
    price_map = {
        "자소서": "50,000원",
        "이력서": "30,000원"
    }
    
    price = price_map.get(service_type, "상담 필요")
    return {"looked_up_price": price}

# 2. Update state (optional)
class ChatState(TypedDict):
    # ... existing ...
    looked_up_price: Optional[str]

# 3. Register
def _build_graph(self):
    # ...
    graph_builder.add_node("lookup_price", self._lookup_price)
    graph_builder.add_edge("retrieve_knowledge", "lookup_price")
    graph_builder.add_edge("lookup_price", "agent")
    # ...
```

---

## API Reference

### SoomgoAgent Class

```python
# Initialize
agent = SoomgoAgent(config=None)

# Chat
response, gathered_info, conv_state, closure = agent.chat(
    user_message: str,
    conversation_history: Optional[list[dict]] = None,
    gathered_info: Optional[dict] = None,
    conversation_state: Optional[str] = None,
    last_closure_response: Optional[str] = None
) -> tuple[str, dict, str, Optional[str]]

# Reset
agent.reset()
```

---

## Need More Details?

See:
- **Full Analysis**: `CLI_AGENT_ANALYSIS.md`
- **Tool Guide**: `TOOL_REGISTRATION_GUIDE.md`
- **Architecture**: `ARCHITECTURE.md`
