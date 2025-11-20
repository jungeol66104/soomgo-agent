# Tool Registration Guide - VF-Data Agent

Quick reference for adding tools/functions to the Soomgo agent.

---

## Current Architecture

```
┌─────────────────────────────────────────────────────┐
│  SoomgoAgent (_build_graph method)                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  START                                              │
│    ↓                                                │
│  Node: extract_info                                 │
│    ↓                                                │
│  Node: retrieve_knowledge                           │
│    ↓                                                │
│  Node: agent                                        │
│    ↓                                                │
│  END                                                │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Where to Add Tools

### File: `/Users/joonnam/Workspace/vf-data/src/agent/core.py`

This is the ONLY file you need to modify to add new "tools" as nodes.

---

## Method 1: Add a Sequential Node

### Use Case
You want to process something **every time** before or after another node.

**Example**: Add a node that validates the user's input format

```python
# Step 1: Add the method to SoomgoAgent class

def _validate_input(self, state: ChatState) -> dict:
    """Validate user input format and language."""
    messages = state["messages"]
    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    
    if not user_messages:
        return {"messages": []}
    
    latest = user_messages[-1].content
    
    # Validation logic
    is_valid = len(latest.strip()) > 0
    
    # You can update state here if needed
    validation_result = {
        "valid": is_valid,
        "length": len(latest)
    }
    
    # Return state updates
    return {}  # No state updates needed - just validation


# Step 2: Register in _build_graph

def _build_graph(self) -> CompiledStateGraph:
    """Build LangGraph workflow."""
    graph_builder = StateGraph(ChatState)

    # Add nodes
    graph_builder.add_node("validate_input", self._validate_input)  # ← NEW
    graph_builder.add_node("extract_info", self._extract_information)
    graph_builder.add_node("retrieve_knowledge", self._retrieve_knowledge)
    graph_builder.add_node("agent", self._run_agent)

    # Connect to workflow
    graph_builder.add_edge(START, "validate_input")  # ← NEW
    graph_builder.add_edge("validate_input", "extract_info")  # ← CHANGED
    graph_builder.add_edge("extract_info", "retrieve_knowledge")
    graph_builder.add_edge("retrieve_knowledge", "agent")
    graph_builder.add_edge("agent", END)

    return graph_builder.compile()
```

---

## Method 2: Add a Conditional Node

### Use Case
You want to route to different nodes based on state conditions.

**Example**: Call a price calculator only if user asks about pricing

```python
# Step 1: Add the node implementation

def _calculate_price(self, state: ChatState) -> dict:
    """Calculate service price based on gathered info."""
    gathered_info = state.get("gathered_info", {})
    service_type = gathered_info.get("service_type")
    
    # Pricing logic
    price = 50000  # Example
    
    # Could update state or just return empty
    return {}


# Step 2: Add a router function

def _route_to_pricing(self, state: ChatState) -> str:
    """Decide whether to calculate price."""
    messages = state["messages"]
    
    if not messages:
        return "agent"
    
    latest = messages[-1].content.lower()
    
    # Check if user asked about price
    if any(word in latest for word in ["가격", "비용", "얼마", "price", "cost"]):
        return "calculate_price"
    
    return "agent"


# Step 3: Register with conditional edges

def _build_graph(self) -> CompiledStateGraph:
    graph_builder = StateGraph(ChatState)

    # Add nodes
    graph_builder.add_node("extract_info", self._extract_information)
    graph_builder.add_node("retrieve_knowledge", self._retrieve_knowledge)
    graph_builder.add_node("calculate_price", self._calculate_price)  # ← NEW
    graph_builder.add_node("agent", self._run_agent)

    # Create edges
    graph_builder.add_edge(START, "extract_info")
    graph_builder.add_edge("extract_info", "retrieve_knowledge")
    
    # CONDITIONAL ROUTING - NEW
    graph_builder.add_conditional_edges(
        "retrieve_knowledge",
        self._route_to_pricing,  # Function that returns next node name
        {
            "calculate_price": "calculate_price",  # If router returns "calculate_price"
            "agent": "agent"                        # If router returns "agent"
        }
    )
    
    graph_builder.add_edge("calculate_price", "agent")  # After pricing, go to agent
    graph_builder.add_edge("agent", END)

    return graph_builder.compile()
```

---

## Method 3: Add State to Track Tool Results

### Use Case
You need to pass data between nodes without using messages.

**Example**: Track pricing calculations in state

```python
# Step 1: Extend ChatState TypedDict

class ChatState(TypedDict):
    """State for the conversation."""
    messages: Annotated[list, operator.add]
    gathered_info: GatheredInfo
    conversation_state: Literal["active", "waiting", "deferred", "closed"]
    last_closure_response: Optional[str]
    retrieved_knowledge: Optional[str]
    
    # NEW: Track pricing state
    calculated_price: Optional[str]
    pricing_valid: Optional[bool]


# Step 2: Update node to return state changes

def _calculate_price(self, state: ChatState) -> dict:
    """Calculate price and update state."""
    gathered_info = state.get("gathered_info", {})
    service_type = gathered_info.get("service_type")
    
    if service_type:
        price = self._get_price_for_service(service_type)
        
        return {
            "calculated_price": price,  # ← Update state
            "pricing_valid": True
        }
    
    return {
        "calculated_price": None,
        "pricing_valid": False
    }


# Step 3: Use in other nodes

def _run_agent(self, state: ChatState) -> dict:
    """Generate response with pricing info if available."""
    
    # Access calculated price
    calculated_price = state.get("calculated_price")
    
    if calculated_price:
        # Include price in prompt
        additional_context = f"가격: {calculated_price}"
    else:
        additional_context = ""
    
    # ... rest of agent logic ...
```

---

## Method 4: Call External Functions (Tools)

### Use Case
You have utility functions or API calls you want to use as "tools"

**Example**: Format user data as a package options list

```python
# Step 1: Create utility file (optional but recommended)

# File: src/agent/tools.py (NEW FILE)

def format_service_package(service_type: str, deadline: str) -> str:
    """Format service package options."""
    packages = {
        "자소서": ["기본형", "전문형", "프리미엄형"],
        "이력서": ["표준형", "맞춤형"]
    }
    
    if service_type in packages:
        return ", ".join(packages[service_type])
    return ""


def calculate_turnaround(service_type: str) -> str:
    """Calculate turnaround time."""
    turnarounds = {
        "자소서": "2-3일",
        "이력서": "1-2일"
    }
    return turnarounds.get(service_type, "상담 후 결정")


# Step 2: Import and use in agent

# In src/agent/core.py
from . import tools  # or direct import

def _prepare_options(self, state: ChatState) -> dict:
    """Prepare service options."""
    gathered_info = state.get("gathered_info", {})
    service_type = gathered_info.get("service_type")
    
    if service_type:
        packages = tools.format_service_package(service_type, "")
        turnaround = tools.calculate_turnaround(service_type)
        
        options_text = f"패키지: {packages}\n기간: {turnaround}"
        
        return {"option_info": options_text}
    
    return {}
```

---

## Full Example: Adding a "Format Service Options" Tool

Here's a complete, working example:

```python
# In src/agent/core.py

# Step 1: Add to ChatState if tracking result
class ChatState(TypedDict):
    """State for the conversation."""
    messages: Annotated[list, operator.add]
    gathered_info: GatheredInfo
    conversation_state: Literal["active", "waiting", "deferred", "closed"]
    last_closure_response: Optional[str]
    retrieved_knowledge: Optional[str]
    formatted_options: Optional[str]  # NEW


# Step 2: Add the node function
def _format_service_options(self, state: ChatState) -> dict:
    """Format service options based on gathered info."""
    gathered_info = state.get("gathered_info", {})
    service_type = gathered_info.get("service_type")
    
    if not service_type:
        return {"formatted_options": None}
    
    # Your logic here
    options = self._build_options_for_service(service_type)
    
    return {"formatted_options": options}


# Step 3: Add helper method
def _build_options_for_service(self, service_type: str) -> str:
    """Build options string for service type."""
    options_map = {
        "자소서": "기본형(5만원), 전문형(7.5만원), 프리미엄형(10만원)",
        "이력서": "표준형(3만원), 맞춤형(5만원)"
    }
    return options_map.get(service_type, "옵션 정보 없음")


# Step 4: Register in _build_graph
def _build_graph(self) -> CompiledStateGraph:
    graph_builder = StateGraph(ChatState)

    graph_builder.add_node("extract_info", self._extract_information)
    graph_builder.add_node("retrieve_knowledge", self._retrieve_knowledge)
    graph_builder.add_node("format_options", self._format_service_options)  # NEW
    graph_builder.add_node("agent", self._run_agent)

    graph_builder.add_edge(START, "extract_info")
    graph_builder.add_edge("extract_info", "retrieve_knowledge")
    graph_builder.add_edge("retrieve_knowledge", "format_options")  # NEW
    graph_builder.add_edge("format_options", "agent")  # NEW
    graph_builder.add_edge("agent", END)

    return graph_builder.compile()


# Step 5 (Optional): Use formatted_options in agent
def _run_agent(self, state: ChatState) -> dict:
    """Generate response."""
    formatted_options = state.get("formatted_options")
    
    # Add to system prompt if available
    if formatted_options:
        knowledge_section = f"\n\n## 서비스 옵션\n{formatted_options}"
    else:
        knowledge_section = ""
    
    # ... rest of agent logic ...
```

---

## Checklist: Adding a New Tool

- [ ] **Decide tool type**: Sequential, Conditional, or External function?
- [ ] **Create the function**: `def _tool_name(self, state: ChatState) -> dict:`
- [ ] **Update ChatState if needed**: Add fields to track results
- [ ] **Create router function if conditional**: `def _route_to_tool(self, state: ChatState) -> str:`
- [ ] **Register in _build_graph()**:
  - [ ] `graph_builder.add_node("tool_name", self._tool_name)`
  - [ ] `graph_builder.add_edge(from_node, "tool_name")`
  - [ ] `graph_builder.add_edge("tool_name", to_node)`
- [ ] **Use results**: Access via `state.get("field_name")` in other nodes
- [ ] **Test**: Run `python cli/chat.py` and verify behavior

---

## Common Patterns

### Pattern 1: Extract and Store
```python
def _my_tool(self, state: ChatState) -> dict:
    # Extract something
    result = self._process_something()
    
    # Store in state
    return {"my_result": result}
```

### Pattern 2: Conditional Routing
```python
def _router(self, state: ChatState) -> str:
    if some_condition:
        return "node_a"
    return "node_b"
```

### Pattern 3: Access Previous Results
```python
def _downstream_node(self, state: ChatState) -> dict:
    previous_result = state.get("previous_result_key")
    
    if previous_result:
        # Use it
        pass
    
    return {}
```

### Pattern 4: Modify Messages
```python
def _my_tool(self, state: ChatState) -> dict:
    return {
        "messages": [SystemMessage(content="New message")]
    }
```

---

## Testing Your Tool

```python
# Quick test
if __name__ == "__main__":
    agent = SoomgoAgent()
    
    # Test the workflow
    response, info, conv_state, closure = agent.chat(
        "자소서 가격이 얼마예요?",
        [],
        None,
        None,
        None
    )
    
    print(f"Response: {response}")
```

---

## Debugging

### View Graph Structure
```python
# In src/agent/core.py, after building graph
graph = self._build_graph()
print(graph.get_graph().draw_ascii())  # ASCII visualization
```

### Log State Changes
```python
def _my_tool(self, state: ChatState) -> dict:
    logger.debug(f"Input state: {state}")
    
    result = self._process()
    
    logger.debug(f"Output state: {result}")
    
    return result
```

### Check State at Runtime
Add temporary logging in any node to see what's in state.

---

## Common Issues

### Issue: Tool is never called
**Solution**: Check that edges are correctly connected in `_build_graph()`

### Issue: Tool doesn't have access to data
**Solution**: Add needed fields to `ChatState` TypedDict

### Issue: Conditional routing not working
**Solution**: Verify router function returns exact node name strings

### Issue: State changes not persisting
**Solution**: Make sure you `return {"field": value}` from the node

---

## Need Help?

Refer to:
- **Graph structure**: `/Users/joonnam/Workspace/vf-data/src/agent/core.py` (lines 78-93)
- **State definition**: `/Users/joonnam/Workspace/vf-data/src/agent/core.py` (lines 34-40)
- **Full guide**: See `CLI_AGENT_ANALYSIS.md` in project root
