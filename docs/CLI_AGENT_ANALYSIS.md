# VF-Data Project: CLI Agent Implementation Analysis

## Executive Summary

The VF-Data project uses **LangGraph** as the agent framework with a **custom node-based workflow** approach. There are **NO external tools/functions registered** yet—the agent is purely an LLM-based conversational system using state management.

---

## 1. Current CLI Agent Implementation

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Entry Point                          │
│                   (cli/chat.py)                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
         ┌────────────────────────┐
         │  SoomgoAgent Class      │
         │ (src/agent/core.py)    │
         └────────┬───────────────┘
                  │
         ┌────────┴──────────────┐
         ▼                       ▼
    LangGraph                 OpenAI LLM
    Workflow                  (gpt-4o-mini)
    (3 nodes)                 
         │
    ┌────┴─────┬──────────┐
    ▼          ▼          ▼
  Node 1    Node 2     Node 3
Extract  Retrieve   Generate
 Info   Knowledge  Response
```

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `/Users/joonnam/Workspace/vf-data/cli/chat.py` | Interactive CLI interface | 179 |
| `/Users/joonnam/Workspace/vf-data/src/agent/core.py` | Main agent implementation (LangGraph) | 537 |
| `/Users/joonnam/Workspace/vf-data/src/agent/config.py` | Agent configuration | 29 |
| `/Users/joonnam/Workspace/vf-data/src/knowledge/retriever.py` | Knowledge retrieval system | 299 |
| `/Users/joonnam/Workspace/vf-data/src/agent/__init__.py` | Package exports | 6 |

---

## 2. How Tools/Functions Are Currently Defined and Used

### Current State: NO Traditional Tools

The agent does **NOT** use LangChain's `tool`, `@tool`, or `bind_tools()` pattern. Instead:

1. **No tool registration system exists**
2. **Functions are implemented as LangGraph nodes** that are part of the workflow
3. **State mutations happen through graph edges**

### How It Works Now

#### A. Graph-Based Workflow (LangGraph)

**File**: `/Users/joonnam/Workspace/vf-data/src/agent/core.py` (lines 78-93)

```python
def _build_graph(self) -> CompiledStateGraph:
    """Build LangGraph workflow with information extraction and knowledge retrieval."""
    graph_builder = StateGraph(ChatState)

    # Add nodes - These are the "functions" in the workflow
    graph_builder.add_node("extract_info", self._extract_information)
    graph_builder.add_node("retrieve_knowledge", self._retrieve_knowledge)
    graph_builder.add_node("agent", self._run_agent)

    # Build workflow: START -> extract info -> retrieve knowledge -> generate response -> END
    graph_builder.add_edge(START, "extract_info")
    graph_builder.add_edge("extract_info", "retrieve_knowledge")
    graph_builder.add_edge("retrieve_knowledge", "agent")
    graph_builder.add_edge("agent", END)

    return graph_builder.compile()
```

**Execution Flow**:
```
User Input → Graph State
    ↓
1. extract_info node      (Extract gathered_info, conversation_state)
    ↓
2. retrieve_knowledge node (Fetch relevant knowledge from KB)
    ↓
3. agent node             (LLM generates response)
    ↓
Agent Response
```

#### B. Node Implementations (These act like "tools")

**Node 1: `_extract_information`** (lines 95-207)
- Extracts: service_type, company_role, deadline, experience, difficulties, budget
- Calls LLM to parse customer intent
- Updates `gathered_info` in state

**Node 2: `_retrieve_knowledge`** (lines 209-247)
- Queries knowledge base (FAQs, pricing, policies)
- Uses OpenAI embeddings for semantic search
- Formatted knowledge returned to state

**Node 3: `_run_agent`** (lines 249-322)
- Generates final response
- Takes system prompt + conversation history + state info
- Returns AIMessage response

#### C. State Definition

**File**: `/Users/joonnam/Workspace/vf-data/src/agent/core.py` (lines 34-40)

```python
class ChatState(TypedDict):
    """State for the conversation."""
    messages: Annotated[list, operator.add]
    gathered_info: GatheredInfo
    conversation_state: Literal["active", "waiting", "deferred", "closed"]
    last_closure_response: Optional[str]
    retrieved_knowledge: Optional[str]
```

This state flows through all nodes and is updated as needed.

---

## 3. Framework: LangGraph (NOT LangChain Tool Framework)

### Why LangGraph?

**Chosen framework**: LangGraph with StateGraph pattern

**Why NOT traditional LangChain tools**:
- The project needed complex multi-step workflows
- Each step depends on previous state (information gathering)
- Message history and conversation state management needed
- Knowledge retrieval happens conditionally
- State mutation across nodes needed

### Framework Components Used

| Component | Usage | File |
|-----------|-------|------|
| `StateGraph` | Graph builder | core.py:80 |
| `ChatState` | TypedDict for state | core.py:34 |
| `START`, `END` | Graph edges | core.py:88-91 |
| `HumanMessage`, `AIMessage`, `SystemMessage` | Message types | core.py:10 |
| `ChatOpenAI` | LLM integration | core.py:290, 169 |
| `CompiledStateGraph` | Compiled workflow | core.py:13 |

### No Tool Binding

There is **NO** code like:
```python
# THIS DOES NOT EXIST IN THE PROJECT
tools = [some_function_tool, another_function_tool]
agent = model.bind_tools(tools)
```

Instead, tools are represented as **workflow nodes**.

---

## 4. Where Would Functions/Tools Be Registered or Added?

### Option A: Add as LangGraph Nodes (Current Pattern)

To add a new "tool" capability, create a new node:

**Example: Adding a price calculator tool**

```python
# File: src/agent/core.py

def _build_graph(self) -> CompiledStateGraph:
    graph_builder = StateGraph(ChatState)
    
    # Existing nodes
    graph_builder.add_node("extract_info", self._extract_information)
    graph_builder.add_node("retrieve_knowledge", self._retrieve_knowledge)
    
    # NEW NODE: Price calculator
    graph_builder.add_node("calculate_price", self._calculate_price)
    
    graph_builder.add_node("agent", self._run_agent)

    # Edges with conditional routing
    graph_builder.add_edge(START, "extract_info")
    graph_builder.add_edge("extract_info", "retrieve_knowledge")
    
    # NEW: Add conditional edge to price calculator
    graph_builder.add_conditional_edges(
        "retrieve_knowledge",
        self._should_calculate_price,  # Function that returns node name
        {
            "calculate_price": "calculate_price",
            "agent": "agent"  # Default to agent
        }
    )
    
    graph_builder.add_edge("calculate_price", "agent")
    graph_builder.add_edge("agent", END)

    return graph_builder.compile()

# NEW NODE IMPLEMENTATION
def _calculate_price(self, state: ChatState) -> dict:
    """Calculate service price based on gathered info."""
    gathered_info = state.get("gathered_info", {})
    
    # Your price calculation logic
    price = self._calculate_from_info(gathered_info)
    
    # Update state
    return {
        "messages": [SystemMessage(content=f"Price: {price}")]
    }

# NEW ROUTING FUNCTION
def _should_calculate_price(self, state: ChatState) -> str:
    """Decide if we should calculate price."""
    messages = state["messages"]
    latest = messages[-1].content.lower() if messages else ""
    
    if any(word in latest for word in ["가격", "비용", "얼마"]):
        return "calculate_price"
    return "agent"
```

**Advantages**:
- ✅ Fits current architecture
- ✅ Can access full state
- ✅ Can use conditional routing
- ✅ Type-safe with TypedDict

**Disadvantages**:
- ❌ Less reusable across projects
- ❌ Tight coupling to graph

### Option B: Add as LangChain Tool (Alternative Pattern)

To add traditional tools that the LLM can invoke, use this pattern:

```python
# File: src/agent/tools.py (NEW FILE)

from langchain_core.tools import tool

@tool
def calculate_service_price(service_type: str, complexity: str) -> str:
    """Calculate the price for a Soomgo service.
    
    Args:
        service_type: Type of service (자소서, 이력서, etc.)
        complexity: Complexity level (basic, standard, premium)
    
    Returns:
        Price as formatted string
    """
    pricing = {
        "자소서": {"basic": 50000, "standard": 75000, "premium": 100000},
        "이력서": {"basic": 30000, "standard": 50000, "premium": 70000},
    }
    
    if service_type in pricing:
        return f"{pricing[service_type].get(complexity, 0):,}원"
    return "가격 정보 없음"

@tool
def check_service_availability(service_type: str, deadline: str) -> str:
    """Check if a service is available within the deadline.
    
    Args:
        service_type: Type of service
        deadline: Deadline (e.g., "3일", "1주일")
    
    Returns:
        Availability message
    """
    # Implementation
    return "가능합니다"

# Collect tools
TOOLS = [calculate_service_price, check_service_availability]
```

Then integrate with agent:

```python
# In src/agent/core.py _run_agent method

model = ChatOpenAI(...)
model_with_tools = model.bind_tools(TOOLS)

# Now model will suggest tool calls in responses
response = model_with_tools.invoke(messages)
```

**Advantages**:
- ✅ Reusable across different agents
- ✅ LLM decides when to use tools
- ✅ Standard LangChain pattern
- ✅ Easy to test in isolation

**Disadvantages**:
- ❌ Requires tool invocation loop
- ❌ More complex state handling
- ❌ Extra API calls to LLM

### Option C: Hybrid Approach (Recommended)

Combine both patterns:

```python
# Use LangGraph nodes for:
# - Information extraction
# - Knowledge retrieval  
# - State management
# - Business logic

# Use LangChain tools for:
# - Reusable utilities (pricing, availability)
# - External API calls
# - Features LLM can invoke dynamically
```

**Architecture**:
```
LangGraph Node
    ↓
├─ Extract Info (Node)
├─ Retrieve Knowledge (Node)
├─ Call LLM with Tools (Node)
│   ├─ Tool: calculate_price()
│   ├─ Tool: check_availability()
│   └─ Tool: format_package()
└─ Process Response (Node)
```

---

## 5. Knowledge Retrieval System (Existing "Tool")

The only "tool-like" external system currently is the **KnowledgeRetriever**:

**File**: `/Users/joonnam/Workspace/vf-data/src/knowledge/retriever.py` (lines 1-299)

### How It Works

```python
# Initialization
from src.knowledge import KnowledgeRetriever

retriever = KnowledgeRetriever()

# Retrieval
retrieved = retriever.retrieve(
    query="자소서 가격이 얼마예요?",
    top_k=3,
    threshold=0.4
)

# Result structure
{
    "structured": {
        "자소서": {
            "name": "자기소개서",
            "pricing": {"rate": 50000, "unit": "개"},
            "turnaround": "2-3일"
        }
    },
    "faqs": [
        {
            "question": "가격이 비싸지 않나요?",
            "answer": "저희 가격은...",
            "similarity_score": 0.87
        }
    ]
}
```

### Data Structure

Located at: `/Users/joonnam/Workspace/vf-data/data/knowledge/`

```
knowledge/
├── structured/          # Exact data (keyword-based)
│   ├── services.json    # Pricing, turnaround
│   └── policies.json    # Refund, payment terms
└── semantic/            # Semantic search (embedding-based)
    └── faq.json         # Q&A pairs
```

### Integration with Agent

**File**: `/Users/joonnam/Workspace/vf-data/src/agent/core.py` (lines 209-247)

```python
def _retrieve_knowledge(self, state: ChatState) -> dict:
    """Retrieve relevant knowledge for the user's latest message."""
    messages = state["messages"]
    gathered_info = state.get("gathered_info", {})
    
    # Get latest user message
    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    if not user_messages:
        return {"retrieved_knowledge": None}
    
    latest_message = user_messages[-1].content
    
    # Enhanced query with context
    query = latest_message
    service_type = gathered_info.get("service_type")
    
    if len(latest_message) < 20 and service_type:
        query = f"{service_type} {latest_message}"
    
    try:
        # THIS IS THE "TOOL" - Knowledge retrieval
        retrieved = self.retriever.retrieve(query, top_k=3, threshold=0.4)
        
        if retrieved.get("structured") or retrieved.get("faqs"):
            formatted = self.retriever.format_knowledge(retrieved)
            return {"retrieved_knowledge": formatted}
        else:
            return {"retrieved_knowledge": None}
    
    except Exception as e:
        logger.error(f"Error retrieving knowledge: {e}")
        return {"retrieved_knowledge": None}
```

Then in `_run_agent`:

```python
# Knowledge section is appended to system prompt
knowledge_section = f"""

## 📚 관련 지식 (참고용)
{retrieved_knowledge}

**지시사항:** 위 정보를 참고하되, 자연스럽게 답변하세요."""

full_prompt = f"""{self.system_prompt}
{state_summary}
{conv_state_instructions}{knowledge_section}"""
```

---

## 6. Tool/Function Registration Points

### Current Registration System (Graph-Based)

**Location**: `/Users/joonnam/Workspace/vf-data/src/agent/core.py` (lines 78-93)

```python
def _build_graph(self) -> CompiledStateGraph:
    """Where all 'tools' (nodes) are registered."""
    graph_builder = StateGraph(ChatState)

    # REGISTRATION POINT 1: Node definitions
    graph_builder.add_node("extract_info", self._extract_information)
    graph_builder.add_node("retrieve_knowledge", self._retrieve_knowledge)
    graph_builder.add_node("agent", self._run_agent)

    # REGISTRATION POINT 2: Workflow edges
    graph_builder.add_edge(START, "extract_info")
    graph_builder.add_edge("extract_info", "retrieve_knowledge")
    graph_builder.add_edge("retrieve_knowledge", "agent")
    graph_builder.add_edge("agent", END)

    return graph_builder.compile()
```

### To Add a New Tool (Node)

1. **Implement the node function**:
   ```python
   def _my_new_tool(self, state: ChatState) -> dict:
       """Process something and update state."""
       # Access state
       messages = state["messages"]
       
       # Do work
       result = self._do_something()
       
       # Return state updates
       return {"key_to_update": result}
   ```

2. **Register in graph**:
   ```python
   graph_builder.add_node("my_tool", self._my_new_tool)
   ```

3. **Add edges**:
   ```python
   graph_builder.add_edge("previous_node", "my_tool")
   graph_builder.add_edge("my_tool", "next_node")
   ```

---

## 7. Dependencies and Imports

### Core Dependencies

```python
# From pyproject.toml

# Graph orchestration
langgraph>=0.2.0
langchain>=0.3.0
langchain-core>=0.3.0
langchain-openai>=0.2.0

# LLM
openai>=1.0.0

# Configuration
python-dotenv>=1.2.1
pydantic>=2.12.3

# CLI/UI
rich>=14.2.0
prompt-toolkit>=3.0.0
streamlit>=1.40.0

# Utilities
loguru>=0.7.3
```

### Used in Agent

```python
# Message handling
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# LLM
from langchain_openai import ChatOpenAI

# Graph
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

# Config
from pydantic import BaseModel
from pathlib import Path
from typing import Annotated, Literal, Optional, TypedDict
```

---

## 8. CLI Entry Point

**File**: `/Users/joonnam/Workspace/vf-data/cli/chat.py` (lines 79-174)

```python
def main():
    """Main CLI loop."""
    print_banner()

    # Initialize agent
    try:
        agent = SoomgoAgent()  # ← Creates graph
    except Exception as e:
        console.print(f"[{COLORS['error']}]✗ Failed: {e}")
        return 1

    # Main loop
    while True:
        try:
            console.print(f"[bold {COLORS['user']}]You[/bold {COLORS['user']}]")
            user_input = get_input()
            
            # Handle commands
            if user_input.lower() == '/quit':
                break
            # ... other commands ...
            
            # Get response
            response, gathered_info, conversation_state, last_closure_response = agent.chat(
                user_input, 
                history, 
                gathered_info, 
                conversation_state, 
                last_closure_response
            )
            
            # Display and update history
            console.print(f"[bold {COLORS['primary']}]Agent[/bold {COLORS['primary']}]")
            console.print(f"[{COLORS['text']}]{response}[/{COLORS['text']}]")
            
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response})
```

**Execution Flow**:
```
cli/chat.py
    ↓
agent.chat(user_input, history, ...)
    ↓
src/agent/core.py: chat() method
    ↓
graph.invoke(state) ← Runs all nodes in sequence
    ↓
Return response
```

---

## 9. Summary Comparison Table

| Aspect | Current | Alternative A | Alternative B |
|--------|---------|---------------|---------------|
| **Framework** | LangGraph + StateGraph | LangGraph + Tool Binding | Pure LangChain |
| **Tool Definition** | Graph Nodes | @tool decorators | StructuredTool |
| **Where Registered** | _build_graph() | _run_agent() | agent.bind_tools() |
| **Reusability** | Node methods | External functions | External functions |
| **State Access** | Full ChatState | Partial via context | Via tool params |
| **Tool Invocation** | Sequential nodes | LLM decides | LLM decides |
| **Complexity** | Moderate | Higher | Higher |
| **Best For** | Deterministic flows | Autonomous agents | LLM-controlled tools |

---

## 10. Recommendation: Adding New Capabilities

### For Deterministic Logic (Use LangGraph Nodes)
- Information extraction rules
- State mutations
- Conditional routing
- Business logic

**Example**: "If user asks about price AND we have service type, fetch from knowledge base"

### For LLM-Driven Features (Use LangChain Tools)
- External API calls
- Dynamic function invocation
- Features LLM should decide when to use
- Reusable utilities

**Example**: "Assistant can decide to call calculator, formatter, or API based on request"

### For Hybrid Systems (Recommended)
Combine both patterns:
1. **Node 1**: Extract information deterministically
2. **Node 2**: Retrieve knowledge deterministically  
3. **Node 3**: Invoke LLM with available tools (it decides which to use)
4. **Node 4**: Process tool outputs and generate final response

---

## Quick Reference: File Locations

```
Project Root: /Users/joonnam/Workspace/vf-data/

Core Agent:
  - /src/agent/core.py           (Main agent class, graph building)
  - /src/agent/config.py         (Configuration)
  - /src/agent/__init__.py        (Package exports)

Knowledge System:
  - /src/knowledge/retriever.py   (Knowledge retrieval)
  - /data/knowledge/              (Knowledge data files)

CLI:
  - /cli/chat.py                  (Interactive chat interface)

Entry Point:
  - /main.py                      (Scraper CLI - not agent)
```

---

## Conclusion

The VF-Data CLI agent is a **LangGraph-based conversation system** with:
- ✅ **No traditional tool framework** (yet)
- ✅ **3-node workflow** (extract → retrieve → respond)
- ✅ **State-driven architecture** with rich conversation state
- ✅ **Knowledge retrieval system** for domain-specific information
- ✅ **Ready for tool integration** at multiple points

To add tools:
1. **Simple approach**: Add new nodes to the graph
2. **Flexible approach**: Integrate LangChain @tool functions
3. **Best approach**: Hybrid pattern combining both

