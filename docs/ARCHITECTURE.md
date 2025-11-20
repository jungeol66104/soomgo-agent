# VF-Data Project Architecture

## Overview

This project serves multiple purposes:
1. **Data Collection**: Scrape Soomgo chat conversations
2. **Agent Development**: Build and test AI chatbot agent
3. **Evaluation**: Measure agent performance against real data
4. **Training**: Optimize prompts using collected conversations

---

## 🎯 Design Principles

1. **Separation of Concerns**: Each module has a single, clear purpose
2. **Reusable Core**: Agent logic is decoupled from interfaces (CLI/Web/API)
3. **Progressive Enhancement**: Start simple, add complexity as needed
4. **Data-Driven**: Leverage 10K+ real conversations for training and evaluation

---

## 📁 Directory Structure

```
vf-data/
├── src/
│   ├── scraper/                   # 🕷️ DATA COLLECTION
│   │   ├── __init__.py
│   │   ├── auth.py                # Authentication & session management
│   │   ├── chat_list_scraper.py   # Scrape chat list
│   │   ├── chat_message_scraper.py # Scrape individual messages
│   │   ├── central_db.py          # Chat list database
│   │   ├── message_central_db.py  # Messages database
│   │   ├── data_quality.py        # Data quality analysis
│   │   └── utils.py               # Scraper utilities
│   │
│   ├── agent/                     # 🤖 AGENT CORE (reusable)
│   │   ├── __init__.py
│   │   ├── core.py                # Main agent class (LangGraph)
│   │   ├── prompt_loader.py       # Load optimized prompts
│   │   ├── state_manager.py       # Conversation state management
│   │   ├── tools.py               # Agent tools (future: RAG, pricing DB)
│   │   └── config.py              # Agent configuration
│   │
│   ├── evaluation/                # 📊 TESTING & EVALUATION
│   │   ├── __init__.py
│   │   ├── evaluator.py           # Core evaluation engine
│   │   ├── metrics.py             # Quality metrics (similarity, engagement, etc.)
│   │   ├── test_loader.py         # Load test cases from real conversations
│   │   ├── reporters.py           # Generate evaluation reports
│   │   └── comparator.py          # Compare agent vs real provider responses
│   │
│   ├── training/                  # 🧠 PROMPT OPTIMIZATION
│   │   ├── __init__.py
│   │   ├── optimizer.py           # DSPy optimization logic
│   │   ├── data_loader.py         # Load training data
│   │   ├── formatter.py           # Format data for DSPy
│   │   ├── models.py              # Training data models
│   │   └── signature.py           # DSPy signature definitions
│   │
│   ├── viewer/                    # 👀 DATA VIEWER
│   │   ├── __init__.py
│   │   └── ...                    # Streamlit viewer components
│   │
│   └── shared/                    # 🛠️ SHARED CODE
│       ├── __init__.py
│       ├── models.py              # Common data models (Chat, Message, User, etc.)
│       ├── config.py              # Global configuration
│       └── utils.py               # Common utilities
│
├── cli/                           # 🖥️ COMMAND LINE INTERFACES
│   ├── chat.py                    # Interactive chat with agent
│   ├── scraper.py                 # Scraper CLI (replaces main.py)
│   ├── eval.py                    # Run evaluations
│   └── train.py                   # Train/optimize prompts
│
├── web/                           # 🌐 WEB INTERFACES
│   ├── viewer.py                  # Chat data viewer
│   └── agent_ui.py                # Agent chat UI (future)
│
├── api/                           # 🚀 API SERVER (future production)
│   ├── main.py                    # FastAPI application
│   ├── routes/
│   │   ├── chat.py                # POST /api/chat
│   │   ├── eval.py                # POST /api/eval (internal)
│   │   └── health.py              # GET /api/health
│   ├── schemas.py                 # API request/response schemas
│   └── middleware.py              # Auth, logging, etc.
│
├── tests/                         # ✅ UNIT TESTS
│   ├── test_agent.py
│   ├── test_scraper.py
│   ├── test_evaluation.py
│   └── ...
│
├── data/                          # 📦 DATA STORAGE
│   ├── chat_list_master.jsonl    # All scraped chats
│   ├── messages/                  # Individual chat messages
│   │   └── chat_<id>.jsonl
│   ├── runs/                      # Scraping/training run outputs
│   │   ├── <timestamp>_chat_list/
│   │   ├── <timestamp>_messages/
│   │   └── <timestamp>_prompt_optimize/
│   └── test_cases/                # Curated test conversations
│       ├── career_consulting_1.json
│       ├── price_negotiation_2.json
│       └── ...
│
├── prompts/                       # 📝 PROMPT STORAGE
│   ├── base_prompt.txt            # Hand-crafted baseline
│   ├── optimized_v1.txt           # DSPy optimized
│   ├── optimized_v2.txt           # Further refined
│   └── service_specific/          # Service-specific prompts
│       ├── career_consulting.txt
│       └── ...
│
├── scripts/                       # 🔧 UTILITY SCRIPTS
│   ├── create_export.py           # Export data package
│   ├── inspect_login.py           # Debug authentication
│   └── ...
│
├── docs/                          # 📚 DOCUMENTATION
│   ├── ARCHITECTURE.md            # This file
│   ├── DEVELOPMENT.md             # Development guide
│   ├── API.md                     # API documentation
│   └── EVALUATION.md              # Evaluation metrics guide
│
├── .env                           # Environment variables
├── .gitignore
├── pyproject.toml                 # Dependencies
├── uv.lock
└── README.md                      # Project overview
```

---

## 🔄 Component Interactions

### 1. Data Collection Flow
```
┌──────────┐
│ Scraper  │
│   CLI    │
└────┬─────┘
     │
     ▼
┌──────────────────┐
│ src/scraper/     │
│ - auth.py        │
│ - chat_list_...  │
│ - chat_message...│
└────┬─────────────┘
     │
     ▼
┌──────────────────┐
│ data/            │
│ - chat_list...   │
│ - messages/      │
└──────────────────┘
```

### 2. Agent Development Flow
```
┌──────────┐
│   CLI    │  or  ┌──────┐  or  ┌──────┐
│ chat.py  │      │ Web  │      │ API  │
└────┬─────┘      └───┬──┘      └───┬──┘
     │                │              │
     └────────────────┼──────────────┘
                      ▼
              ┌──────────────┐
              │ src/agent/   │
              │   core.py    │ ← Single source of truth
              └──────┬───────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌────────┐  ┌─────────┐  ┌────────┐
   │Prompts │  │ Tools   │  │ State  │
   └────────┘  └─────────┘  └────────┘
```

### 3. Evaluation Flow
```
┌──────────────┐
│ data/        │
│ messages/    │ ─────┐
└──────────────┘      │
                      ▼
              ┌───────────────┐
              │src/evaluation/│
              │test_loader.py │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐     ┌──────────┐
              │  evaluator.py │ ──▶ │ metrics  │
              └───────┬───────┘     └──────────┘
                      │
                      ▼
              ┌───────────────┐
              │  reporters.py │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │ Evaluation    │
              │ Report        │
              └───────────────┘
```

### 4. Training/Optimization Flow
```
┌──────────────┐
│ data/        │
│ messages/    │
│ (hired only) │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ src/training/    │
│ data_loader.py   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ optimizer.py     │
│ (DSPy)           │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ prompts/         │
│ optimized_vX.txt │
└──────────────────┘
```

---

## 🚀 Evolution Path

### Phase 1: Foundation (Week 1-2)
**Goal**: Working CLI agent with baseline performance

**Components**:
- `cli/chat.py` - Interactive chat interface
- `src/agent/core.py` - Basic agent using existing LangGraph code
- `src/agent/prompt_loader.py` - Load prompts from `prompts/`

**Output**: Can chat with agent, manual testing

---

### Phase 2: Evaluation (Week 2-3)
**Goal**: Automated quality measurement

**Components**:
- `src/evaluation/test_loader.py` - Load test cases from real data
- `src/evaluation/evaluator.py` - Run agent on test cases
- `src/evaluation/metrics.py` - Calculate quality scores
- `cli/eval.py` - Run evaluations from CLI

**Output**: "Agent achieves 45% hiring probability on test set"

---

### Phase 3: Optimization (Week 3-4)
**Goal**: Improve agent performance

**Components**:
- `src/training/optimizer.py` - Enhanced DSPy optimization
- Better prompt selection based on evaluation results
- Service-specific prompts

**Output**: "Agent v2 achieves 62% hiring probability"

---

### Phase 4: Web UI (Week 4-5)
**Goal**: Shareable demo

**Components**:
- `web/agent_ui.py` - Streamlit chat interface
- Reuses `src/agent/core.py` (no duplication!)

**Output**: Web demo you can share with stakeholders

---

### Phase 5: Production API (Month 2+)
**Goal**: Deployable service

**Components**:
- `api/main.py` - FastAPI server
- `api/routes/chat.py` - Chat endpoint
- Reuses `src/agent/core.py` (still no duplication!)
- Docker containerization
- Authentication & rate limiting

**Output**: `POST /api/chat` endpoint ready for production

---

## 🔑 Key Design Decisions

### 1. Why separate `cli/`, `web/`, `api/`?
- These are **interfaces**, not core logic
- Agent logic lives in `src/agent/` (reusable)
- Easy to add new interfaces without touching agent code

### 2. Why `src/agent/` not `src/chatbot/`?
- "Agent" is more accurate (uses tools, has reasoning)
- Clearer distinction from simple chatbot
- Future: can add multiple agent types

### 3. Why `evaluation/` separate from `training/`?
- Evaluation = measure performance (any agent)
- Training = improve specific agent
- Can evaluate without training, train without evaluating

### 4. Why `shared/` folder?
- Avoids circular imports
- Common models used by all modules
- Single source of truth for data structures

### 5. Migration from existing code?
- **Keep old code working** during transition
- Move to new structure incrementally
- Deprecate old paths after new ones proven

---

## 📊 Current State → Target State

### Current (Messy but Working)
```
src/
├── chatbot/agent.py     # Agent code
├── dspy/optimizer.py    # Training code
├── auth.py              # Scraper code
└── models.py            # Mixed models
main.py                  # Scraper CLI
chat_viewer.py           # Viewer
```

### Target (Clean & Scalable)
```
src/
├── agent/core.py        # Agent only
├── training/optimizer.py # Training only
├── scraper/auth.py      # Scraper only
└── shared/models.py     # Shared models
cli/
├── scraper.py           # Scraper CLI
├── chat.py              # Agent CLI
└── train.py             # Training CLI
web/viewer.py            # Viewer
```

---

## 🎯 Success Metrics

### Week 2
- [ ] CLI agent responds to messages
- [ ] Can run 100 test conversations
- [ ] Baseline score established

### Week 4
- [ ] Agent v2 outperforms baseline by 20%+
- [ ] Web UI deployed for demos
- [ ] Documentation complete

### Month 2
- [ ] API ready for production
- [ ] 70%+ hiring probability on test set
- [ ] Cost per conversation < $0.05

---

## 🛠️ Tech Stack

- **Python 3.13**: Modern Python features
- **LangGraph**: Agent orchestration
- **DSPy**: Prompt optimization
- **OpenAI**: LLM provider
- **Streamlit**: Web UI (rapid prototyping)
- **FastAPI**: Production API (future)
- **Playwright**: Web scraping
- **Pydantic**: Data validation
- **Rich**: CLI formatting
- **Pytest**: Testing

---

## 📝 Notes

- This architecture supports incremental development
- Each phase adds value independently
- Can deploy at any phase (don't need to complete all)
- Emphasis on measurement and iteration
- Reusable core enables multiple interfaces

---

**Last Updated**: 2025-11-05
**Status**: Proposed architecture for v0 implementation
