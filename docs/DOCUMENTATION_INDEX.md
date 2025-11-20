# VF-Data Documentation Index

## New Documentation Created

This analysis provides comprehensive documentation of the CLI agent implementation.

### Three New Files:

1. **CLI_AGENT_ANALYSIS.md** (20 KB - COMPREHENSIVE)
   - Complete architectural overview
   - How tools/functions are currently defined
   - Framework explanation (LangGraph)
   - Where and how to register functions/tools
   - 10 detailed sections with code examples
   - Knowledge retrieval system walkthrough
   - Dependencies and imports
   - **Use this for:** Deep understanding of the entire system

2. **TOOL_REGISTRATION_GUIDE.md** (14 KB - PRACTICAL)
   - Quick reference for adding tools
   - 4 different methods with examples
   - Full working example from start to finish
   - Checklist for implementation
   - Common patterns and anti-patterns
   - Debugging guide
   - **Use this for:** Implementing new tool/function additions

3. **QUICK_REFERENCE.md** (8.2 KB - AT-A-GLANCE)
   - System overview diagram
   - State structure reference
   - 3-step tool addition formula
   - Common mistakes and fixes
   - API reference
   - File locations
   - **Use this for:** Quick lookups while coding

---

## Quick Navigation

### If you want to...

**Understand the overall architecture**
- Start: `QUICK_REFERENCE.md` (Overview section)
- Then: `CLI_AGENT_ANALYSIS.md` (Sections 1-3)

**Add a new tool/function**
- Start: `QUICK_REFERENCE.md` (Adding a Tool: 3 Steps)
- Then: `TOOL_REGISTRATION_GUIDE.md` (choose your method)
- Reference: `CLI_AGENT_ANALYSIS.md` (Section 4)

**Understand tool registration**
- Start: `CLI_AGENT_ANALYSIS.md` (Sections 2, 4, 6)
- Then: `TOOL_REGISTRATION_GUIDE.md` (Full example section)

**Set up debugging**
- See: `TOOL_REGISTRATION_GUIDE.md` (Debugging section)
- Or: `QUICK_REFERENCE.md` (Debugging Tips)

**Understand the knowledge system**
- See: `CLI_AGENT_ANALYSIS.md` (Section 5)
- Or: `QUICK_REFERENCE.md` (Knowledge Retrieval section)

---

## Key Information Summary

### Framework
- **Framework**: LangGraph (NOT traditional LangChain tools)
- **Pattern**: StateGraph with typed state
- **Workflow**: 3-node pipeline (extract → retrieve → respond)

### Main Files
- **Agent**: `/src/agent/core.py` (537 lines) - THE ONLY FILE TO MODIFY
- **CLI**: `/cli/chat.py` (179 lines)
- **Knowledge**: `/src/knowledge/retriever.py` (299 lines)
- **Config**: `/src/agent/config.py` (29 lines)

### Tool Registration
- **Location**: `/src/agent/core.py` lines 78-93 in `_build_graph()`
- **Method**: `graph_builder.add_node()` then `graph_builder.add_edge()`
- **Options**: Sequential, Conditional, or External function patterns

### Current Workflow
```
User Input
    ↓
Node 1: extract_information (Parse intent, gather data)
    ↓
Node 2: retrieve_knowledge (Fetch FAQs, pricing, policies)
    ↓
Node 3: agent (Generate response with LLM)
    ↓
Response
```

### State Structure
```python
ChatState = {
    "messages": [...],           # Conversation history
    "gathered_info": {           # Customer data
        "service_type": str,
        "company_role": str,
        "deadline": str,
        "experience": str,
        "existing_resume": str,
        "difficulties": str,
        "budget": str
    },
    "conversation_state": str,   # active|waiting|deferred|closed
    "last_closure_response": str,
    "retrieved_knowledge": str
}
```

---

## 3-Step Tool Addition

**Step 1: Write the function**
```python
def _my_tool(self, state: ChatState) -> dict:
    result = do_something()
    return {"field_name": result}
```

**Step 2: Update state (if needed)**
```python
class ChatState(TypedDict):
    # ... existing fields ...
    field_name: Optional[str]  # NEW
```

**Step 3: Register in graph**
```python
def _build_graph(self):
    # ...
    graph_builder.add_node("my_tool", self._my_tool)
    graph_builder.add_edge("previous_node", "my_tool")
    graph_builder.add_edge("my_tool", "next_node")
```

---

## Important File Locations

```
/Users/joonnam/Workspace/vf-data/

Documentation (NEW):
  ├── CLI_AGENT_ANALYSIS.md
  ├── TOOL_REGISTRATION_GUIDE.md
  ├── QUICK_REFERENCE.md
  └── DOCUMENTATION_INDEX.md (this file)

Existing Documentation:
  ├── ARCHITECTURE.md
  └── README.md

Core Code:
  src/agent/
    ├── core.py           ← TOOL REGISTRATION POINT
    ├── config.py
    └── __init__.py
  
  src/knowledge/
    └── retriever.py      ← Knowledge retrieval
  
  cli/
    └── chat.py           ← User interface
  
  data/knowledge/
    ├── structured/
    │   ├── services.json
    │   └── policies.json
    └── semantic/
        └── faq.json
```

---

## Adding Different Tool Types

### Sequential Tool (Always Runs)
Used for: Processing that happens every time
```python
graph_builder.add_edge("from_node", "my_tool")
graph_builder.add_edge("my_tool", "to_node")
```

### Conditional Tool (Runs Sometimes)
Used for: Logic that only applies in certain cases
```python
graph_builder.add_conditional_edges(
    "from_node",
    self._my_router,  # Function returning node name
    {"path_a": "node_a", "path_b": "node_b"}
)
```

### External Function (Utility)
Used for: Helper functions and calculations
```python
# In separate file or same file
def format_service_package(...) -> str:
    # Your logic
    return result

# Use in node
result = format_service_package(...)
```

---

## Testing

```bash
# Run the agent CLI
python cli/chat.py

# Or test programmatically
from src.agent import SoomgoAgent

agent = SoomgoAgent()
response, info, state, closure = agent.chat("Your test message", [], None, None, None)
print(response)
```

---

## Debugging

**View graph structure**:
```python
graph = self._build_graph()
print(graph.get_graph().draw_ascii())
```

**Log state**:
```python
from loguru import logger
logger.debug(f"State: {state}")
```

**Check node execution**:
Add debug prints in node functions to trace execution order

---

## Common Issues

| Problem | Solution |
|---------|----------|
| Node doesn't run | Check edges in `_build_graph()` |
| State not updating | Ensure returning `{"field": value}` |
| Field not accessible | Add to `ChatState` TypedDict first |
| Router not working | Verify it returns exact node name string |

---

## File Descriptions

### CLI_AGENT_ANALYSIS.md
Complete technical documentation covering:
- Current CLI agent implementation (Section 1)
- How tools/functions are defined and used (Section 2)
- Framework explanation: LangGraph (Section 3)
- Where to register functions/tools (Section 4)
- Knowledge retrieval system (Section 5)
- Tool registration points (Section 6)
- Dependencies and imports (Section 7)
- CLI entry point walkthrough (Section 8)
- Comparison table (Section 9)
- Recommendations (Section 10)

**Best for**: Understanding the complete architecture in depth

### TOOL_REGISTRATION_GUIDE.md
Practical implementation guide covering:
- Current architecture visualization
- File location for modifications
- 4 different tool addition methods with complete examples
- Full working example with all steps
- Checklist for implementation
- Common patterns and anti-patterns
- Testing approaches
- Debugging techniques
- Troubleshooting guide

**Best for**: Actually implementing new features

### QUICK_REFERENCE.md
One-page reference guide covering:
- System overview
- Key files table
- State structure at a glance
- 3-step tool addition formula
- Graph node operations
- State access patterns
- Message types
- Knowledge retrieval usage
- Testing commands
- Common mistakes matrix
- Node execution order
- Configuration reference
- File locations
- API reference

**Best for**: Quick lookups while working

---

## Getting Started

1. **New to this codebase?**
   - Read: `QUICK_REFERENCE.md` (Overview)
   - Then: `CLI_AGENT_ANALYSIS.md` (Sections 1-3)

2. **Want to add a feature?**
   - Read: `TOOL_REGISTRATION_GUIDE.md` (Method section)
   - Reference: `QUICK_REFERENCE.md` (3-Step formula)

3. **Need to debug?**
   - See: `TOOL_REGISTRATION_GUIDE.md` (Debugging section)
   - Or: `QUICK_REFERENCE.md` (Debugging Tips)

4. **Need architectural details?**
   - See: `CLI_AGENT_ANALYSIS.md` (Full technical depth)

---

## Next Steps

1. **Review the current implementation**
   - Open `/src/agent/core.py`
   - Look at `_build_graph()` method (lines 78-93)
   - Understand the three nodes

2. **Test the system**
   - Run `python cli/chat.py`
   - Try interacting with the agent

3. **Plan your tool additions**
   - Use `TOOL_REGISTRATION_GUIDE.md` to plan
   - Identify which method to use
   - Write and test your code

4. **Refer back as needed**
   - Use `QUICK_REFERENCE.md` for quick lookups
   - Use `TOOL_REGISTRATION_GUIDE.md` for implementation
   - Use `CLI_AGENT_ANALYSIS.md` for deep dives

---

## Questions Answered

**1. What is the current CLI agent implementation?**
- LangGraph-based system with 3-node workflow
- See: `CLI_AGENT_ANALYSIS.md` Section 1

**2. How are tools/functions currently defined and used?**
- As LangGraph nodes in StateGraph
- See: `CLI_AGENT_ANALYSIS.md` Section 2

**3. What framework or library is being used?**
- LangGraph (not traditional LangChain tools)
- See: `CLI_AGENT_ANALYSIS.md` Section 3

**4. Where would functions/tools be registered or added?**
- `/src/agent/core.py` in `_build_graph()` method
- See: `CLI_AGENT_ANALYSIS.md` Section 4 & 6

---

## Related Documentation

- **ARCHITECTURE.md** - Overall project structure and design principles
- **README.md** - Project overview and getting started

---

**Last Updated**: November 11, 2025
**Status**: Complete analysis of CLI agent implementation
