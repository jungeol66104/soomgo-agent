# VF-Data: Soomgo AI Agent & Data Platform

A comprehensive Python platform for collecting Soomgo chat data, building intelligent AI agents, and optimizing conversation strategies. This system combines large-scale web scraping, LangGraph-powered chatbots, knowledge retrieval, and DSPy prompt optimization.

## Features

### Data Collection & Management
- **Chat List Scraping**: Automated collection of all conversations with API interception
- **Message Scraping**: Concurrent per-chat message collection with deduplication
- **Central Database**: JSONL-based storage for efficient querying of 16,000+ chats
- **Data Quality System**: Comprehensive validation with graded quality scores (0-100)
- **Export Utilities**: Package data with analysis, CSV exports, and documentation

### AI Agent & Chatbot
- **LangGraph-Based Agent**: Multi-node conversation workflow with state management
- **Conversation States**: Active, waiting, deferred, and closed state tracking
- **Information Extraction**: Automatic extraction of service type, deadlines, budget, experience
- **Knowledge Integration**: Hybrid semantic + structured retrieval for accurate responses
- **Tool Support**: Character counting, extensible for RAG, pricing DB, calendar tools
- **Brief & Natural Responses**: Optimized for conversational flow (avg 100 chars)

### Training & Optimization
- **DSPy Integration**: Stanford's framework for prompt optimization
- **Multi-Optimizer Support**: BootstrapFewShot, SignatureOptimizer, MIPRO
- **Conversation Simulation**: Test agent against 16,000+ real historical conversations
- **Quality Metrics**: Automated evaluation of response quality

### Interfaces
- **CLI Commands**: Development (`soomgo-dev`) and production (`soomgo`) modes
- **Interactive TUI**: Dashboard and chat viewer with Textual framework
- **REPL**: Interactive chat testing interface

## Quick Start

### 1. Install Dependencies

```bash
# Install using uv (fast, deterministic package manager)
uv sync
```

### 2. Configure Credentials

Create `.env` file:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
SOOMGO_EMAIL=your-email@example.com
SOOMGO_PASSWORD=your-password
OPENAI_API_KEY=sk-...
HEADLESS=false
```

**Environment Variables**:
- `SOOMGO_EMAIL` / `SOOMGO_PASSWORD`: Soomgo account credentials
- `OPENAI_API_KEY`: For AI agent and embeddings
- `HEADLESS`: `true` for production (no visible browser), `false` for debugging

### 3. Test Authentication

```bash
uv run python tests/test_auth.py
```

**What happens**:
- First run: Logs in and saves session to `data/sessions/soomgo_session.json`
- Subsequent runs: Reuses saved session (no re-login needed)
- Takes screenshot to `logs/logged_in.png` for verification

## CLI Commands

### Entry Points

**Development Mode** (`soomgo-dev`):
- Uses project directory: `vf-data/`
- Data stored in: `data/`, `logs/`, `db/`
- For active development and testing

**Production Mode** (`soomgo`):
- Uses home directory: `~/.soomgo/`
- Data stored in: `~/.soomgo/data/`, `~/.soomgo/logs/`, etc.
- For deployed agent

### Available Commands

#### Agent/Chat Commands

```bash
# Interactive chat with AI agent (for testing)
soomgo-dev chat
soomgo chat

# Main interface (default command)
# Dev mode: Launches TUI with menu (Run, Stop, Status controls + Chat browsing)
# Prod mode: Launches shell/launcher
soomgo-dev
soomgo
```

#### Daemon Management

```bash
# Start agent daemon
soomgo run                    # Normal mode
soomgo run --shadow           # Shadow mode (no messages sent)

# Control daemon
soomgo stop                   # Stop daemon
soomgo status                 # Show status & statistics
soomgo logs                   # View logs
soomgo logs -f                # Follow logs (live)
soomgo logs -n 100            # Show last 100 lines
```

## Data Scraping

### Chat List Scraping

Scrape all conversations from `/pro/chats`:

```bash
# Full production run
python -m src.cli.scraper chats

# Dry run (preview only, no full save)
python -m src.cli.scraper chats --dry-run

# Filter by date (default: 30days)
python -m src.cli.scraper chats --filter all
python -m src.cli.scraper chats --filter 30days

# Limit for testing
python -m src.cli.scraper chats --dry-run --limit 50
```

**What it does**:
1. Authenticates with saved session (or logs in)
2. Navigates to https://soomgo.com/pro/chats
3. Intercepts API calls for clean structured data
4. Scrolls automatically to load all chats (pagination detection)
5. Applies humanization measures (random delays, mouse movements, breaks)
6. Deduplicates by chat ID
7. Generates data quality report with graded score

**Output** (timestamped directory):
```
data/runs/YYYY-MM-DD_HH-MM-SS_chat_list_XXXX/
├── chat_list.jsonl              # One chat per line (JSONL)
├── chat_list.json               # Pretty-printed JSON
├── run_summary.json             # Statistics & metadata
├── data_quality_report.json     # Quality score & validation
├── run.log                      # Detailed logs
├── screenshots/                 # Before/after screenshots
└── api_responses/               # Raw API responses (optional)
```

**Humanization & Safety**:
- Random delays (2-5s between scrolls)
- Reading pauses (20% chance, 2-4s)
- Random scroll-ups (15% chance)
- Mouse movement randomization (30% chance)
- Session breaks (5% chance, 10-30s)
- Viewport randomization (every 10 scrolls)
- Rate limiting with exponential backoff
- Smart stop detection (API `next=null` + timeout)

### Message Scraping

Scrape messages for each chat:

```bash
# Full run (all chats)
python -m src.cli.scraper messages

# Filter by date
python -m src.cli.scraper messages --filter 30days
python -m src.cli.scraper messages --filter all

# Concurrent workers (1-3)
python -m src.cli.scraper messages --workers 3

# Skip already scraped chats
python -m src.cli.scraper messages --skip-existing

# Dry run
python -m src.cli.scraper messages --dry-run --dry-run-limit 5

# Limit for testing
python -m src.cli.scraper messages --limit 100
```

**What it does**:
1. Loads chat list from central database
2. For each chat: intercepts message API calls
3. Saves messages to `data/messages/chat_<id>.jsonl`
4. Concurrent processing with progress tracking
5. Deduplicates messages by ID
6. Tracks success/failure statistics

**Output**:
```
data/messages/
├── chat_158837874.jsonl
├── chat_158841234.jsonl
└── ... (16,000+ files)

data/runs/YYYY-MM-DD_HH-MM-SS_messages_XXXX/
├── run_summary.json
└── run.log
```

### Central Database

Scraped data is automatically merged into central databases:

```
data/
├── chat_list_master.jsonl       # Master chat list (all runs merged)
└── messages/                    # Per-chat message files
    ├── chat_<id>.jsonl
    └── ...
```

**Features**:
- Automatic deduplication by ID
- Incremental updates from new scraping runs
- Efficient JSONL format (one record per line)
- Lazy loading for large datasets

## Data Quality System

Every scraping run generates a comprehensive quality report.

### Quality Score (0-100)

Weighted scoring system:
- **Completeness (40%)**: Required field coverage
- **Validity (30%)**: Format and range checks
- **Consistency (20%)**: No duplicates, timeline logic
- **Anomalies (10%)**: Outlier detection

### Grading Scale

- **A (90-100)**: Excellent
- **B (80-89)**: Very Good
- **C (70-79)**: Good
- **D (60-69)**: Acceptable
- **F (<60)**: Poor

### Validation Checks

**Completeness**:
- Required fields: id, dates, messages, service, user, price
- Optional fields tracked separately

**Validity**:
- Date format (ISO 8601)
- No future dates
- No negative values (prices, counts)
- Range validation

**Consistency**:
- No duplicate IDs
- Timeline: created_at ≤ updated_at
- Cross-field validation

**Anomaly Detection**:
- Price outliers (IQR method)
- Excessive unread messages (>50)
- Frequent users (>10 chats)
- User status patterns (banned, dormant, left)

**Coverage Analysis**:
- Date range and span
- Date gaps (>7 days)
- Service distribution (top 20)

### Example Report

```json
{
  "quality_score": 92.5,
  "quality_grade": "A (Very Good)",
  "overall_completeness_percent": 96.8,
  "valid_records_count": 245,
  "total_records": 247,
  "duplicate_ids": [],
  "validation_issues": [...],
  "anomalies": [...],
  "statistics": {
    "hiring": {
      "hired_count": 87,
      "hiring_rate_percent": 35.22
    },
    "price": {
      "min": 50000,
      "max": 5000000,
      "mean": 850000,
      "median": 600000
    }
  }
}
```

## Data Export

Create shareable data packages with analysis and documentation:

```bash
# Create timestamped export package
uv run python scripts/create_export.py
```

**What it exports**:

```
export/YYYY-MM-DD_HH-MM-SS_export/
├── data/
│   ├── chat_list_master.jsonl        # All chats
│   └── messages/                     # All message files
├── analysis/
│   ├── data_summary.json             # High-level stats
│   ├── data_overview.json            # Detailed analysis
│   ├── services_breakdown.csv        # Service distribution
│   ├── chat_list_export.csv          # Full chat list (Excel-ready)
│   └── missing_chats.csv             # Any incomplete chats
├── models.py                         # Pydantic data models
├── requirements.txt                  # Python dependencies
└── README.md                         # Auto-generated docs (Korean)
```

**Export Statistics**:
```
📦 Total chats: 16,102
📊 Messages: 285,864
✓  Completion rate: 100.0%
📈 Avg messages/chat: 17.75
```

**Use Cases**:
- Share with colleagues/data engineers
- Data analysis in Excel/Python
- Handoff to ML pipeline
- Audit trail with quality metrics

## AI Agent & Chatbot

### Architecture

**LangGraph-based workflow** with state management:

```
Customer Message → Extract Info → Retrieve Knowledge → Generate Response → Update State
                        ↓              ↓                      ↓              ↓
                   Service type   Pricing/FAQ           Brief reply    Active/Waiting/
                   Deadline       Policies              Ask questions  Deferred/Closed
                   Budget         Examples
```

### Conversation State Management

The agent tracks conversation state to provide contextually appropriate responses:

- **Active**: Gathering information, asking questions
- **Waiting**: Customer sending files or preparing materials
- **Deferred**: Customer considering, thinking about offer
- **Closed**: Conversation naturally ended

**State-aware behavior**:
- Prevents repetitive closure messages
- Adapts tone based on state
- Remembers context across messages

### Information Extraction

Automatically extracts structured data:

```python
{
  "service_type": "자소서",           # Resume, cover letter, interview, portfolio
  "company_role": "카카오 프론트엔드",
  "deadline": "이번 주 금요일",
  "experience_level": "신입",
  "budget": "30만원 정도",
  "difficulties": "경력 어필이 어려워요",
  "existing_materials": True
}
```

### Knowledge Retrieval System

**Hybrid approach**: Structured + Semantic Search

#### Structured Lookup
- Service definitions with pricing
- Policies (refund, payment, revision)
- Keyword-based exact matching

#### Semantic Search
- OpenAI embeddings (`text-embedding-3-small`)
- FAQ database with pre-computed embeddings
- Top-k retrieval with similarity threshold (0.4)

**Data Sources**:
```
data/knowledge/
├── structured/
│   ├── services.json           # Service types & pricing
│   └── policies.json           # Refund, payment policies
└── semantic/
    └── faq.json                # FAQ with embeddings
```

**Usage**:
```python
from src.knowledge.retriever import KnowledgeRetriever

retriever = KnowledgeRetriever()
result = retriever.retrieve(
    query="자소서 가격이 얼마인가요?",
    top_k=3,
    threshold=0.4
)

# Returns: {structured: {...}, faqs: [...]}
formatted = retriever.format_knowledge(result)
# Inject into agent prompt
```

### Agent Configuration

Edit `src/agent/config.py`:

```python
AGENT_CONFIG = {
    "model": "gpt-4o-mini",        # Or gpt-4o, gpt-4-turbo
    "temperature": 0.85,           # 0.0-1.0
    "max_tokens": 300,             # Response length limit
    "system_prompt_path": "prompts/system_prompt.txt"
}
```

### Testing the Agent

```bash
# Interactive REPL
soomgo-dev chat

# Automated tests
uv run pytest tests/test_user_scenario.py        # Specific scenarios
uv run pytest tests/test_goal_oriented.py        # Info gathering
uv run pytest tests/test_closure.py              # Closure handling
uv run pytest tests/test_real_conversation.py    # Replay real chats
uv run pytest tests/test_context_pricing.py      # Knowledge integration
uv run pytest tests/test_brief_responses.py      # Response quality
```

**Test Coverage**:
- User scenario handling (exact customer needs)
- Goal-oriented information gathering
- Conversation closure logic
- Real conversation playback (16,000+ chats)
- Context-aware pricing responses
- Brief & natural response generation
- Tool execution (character counting)
- Knowledge retrieval accuracy

## DSPy Prompt Optimization

Optimize agent prompts using real successful conversations.

### Run Optimization

```bash
# Full optimization (all hired chats)
python -m src.cli.scraper optimize-prompt

# Quick test with sample
python -m src.cli.scraper optimize-prompt --sample-chats 50

# Dry run (data prep only, no LLM calls)
python -m src.cli.scraper optimize-prompt --dry-run
```

### Configuration Options

```bash
--model gpt-4o                    # LLM model (gpt-4o, gpt-4-turbo, gpt-3.5-turbo)
--approach few-shot               # few-shot or instruction-only
--optimizer BootstrapFewShot      # BootstrapFewShot, SignatureOptimizer, MIPRO
--max-examples 8                  # Max few-shot examples in prompt
--train-split 0.8                 # Train/validation split
--min-response-length 50          # Filter short responses
--max-turn-number 20              # Focus on early conversation
--sample-chats 100                # Random sample for faster testing
```

### How It Works

1. **Load Data**: All hired conversations (successful outcomes)
2. **Filter**: Remove system messages, keep TEXT messages only
3. **Format**: Create turn-by-turn training examples
4. **Optimize**: DSPy runs chosen optimizer (BootstrapFewShot, etc.)
5. **Evaluate**: Test on validation set
6. **Save**: Optimized prompt + metrics

**Output**:
```
data/runs/YYYY-MM-DD_HH-MM-SS_prompt_optimize_XXXX/
├── optimized_prompt.txt           # Human-readable prompt
├── optimized_prompt.json          # Structured prompt data
├── training_examples.jsonl        # All training examples
├── validation_results.json        # Validation scores
├── run_summary.json               # Metadata
├── optimization_report.json       # Quality metrics
└── run.log                        # Detailed logs
```

### Results

From 138 hired conversations:
- **Validation Score**: 0.91 (91%)
- **Best Approach**: Few-shot with Korean prompt
- **Optimal Filtering**: 50+ chars, max 20 turns
- **Cost**: ~$10-20 for full optimization, ~$2-3 for 50 chats

### Optimization Approaches

**Few-Shot Learning** (default):
- DSPy selects best examples automatically
- Includes 3-8 conversation examples in prompt
- Better for maintaining conversational tone

**Instruction-Only**:
- No examples, just optimized instructions
- Faster, cheaper
- Good for clear, structured tasks

### Quality Metrics

Automated evaluation checks:
- Response length (50-500 chars)
- Korean content (>50%)
- Questions asked (engagement)
- Proper punctuation
- No hallucinations

## Conversation Simulation

Test agent against real historical conversations.

### Run Simulation

```python
from src.simulation.runner import ConversationSimulator
from src.agent.core import SoomgoAgent

# Initialize
simulator = ConversationSimulator()
agent = SoomgoAgent()

# Run simulation on chat
result = simulator.simulate_conversation(
    chat_id=158837874,
    agent=agent
)

# Access results
print(f"Generated {len(result.simulated_messages)} responses")
print(f"Duration: {result.metadata.duration_seconds}s")
```

### How It Works

1. **Load Messages**: Get all messages for chat from database
2. **Group by Time**: Group customer messages into turns (5min window)
3. **Simulate**: Replace agent responses with AI-generated ones
4. **Track State**: Maintain conversation context across turns
5. **Save Results**: Store simulated conversation with metadata

**Features**:
- Time-window-based message grouping
- Conversation context preservation
- Start/end trigger detection
- Progress tracking
- Error handling

**Output**:
```
data/shadow/<chat_id>/
├── simulation_metadata.json      # Run info
└── simulated_messages.jsonl      # AI-generated responses
```

### Simulation Models

```python
MessageGroup:
  - messages: list[MessageItem]
  - time_window: 300s (5 minutes)
  - start_trigger: "new_chat" | "customer_message"

SimulatedMessage:
  - id: negative int (distinguishes from real)
  - content: str
  - timestamp: datetime
  - group_index: int

SimulationMetadata:
  - chat_id: int
  - total_groups: int
  - simulated_count: int
  - start_trigger: str
  - end_trigger: str
  - duration_seconds: float
```

### Testing Simulation

```bash
# Run simulation tests
uv run pytest tests/test_real_conversation.py

# Test specific chat
uv run pytest tests/test_real_conversation.py::test_replay_hired_chat
```

## Main TUI Interface

Interactive terminal UI - the main interface for the entire system:

```bash
soomgo-dev  # Launches TUI in dev mode
```

**Features**:

*Menu & Controls*:
- Run, Stop, Status controls (coming soon)
- Direct access to all features
- Clean menu-based navigation

*Chat Browsing*:
- Browse all 16,000+ conversations
- Filter by hired status, service type, date
- View full conversation history
- See simulation results side-by-side with originals
- Text wrapping for terminal display
- Fast navigation

**Navigation**:
- Use arrow keys to navigate menu/lists
- Enter to select
- Q to quit/go back

## Analysis Scripts

Additional standalone scripts in `scripts/`:

### Explore Conversations

Random sampling and analysis:

```bash
uv run python scripts/explore_conversations.py
```

**Output**:
- Random sample of conversations
- Message type distribution (TEXT, SYSTEM, FILE, etc.)
- Message length statistics
- Conversation structure analysis
- Turn-taking patterns

### Analyze Conversations

2-stage filtering (heuristic + LLM):

```bash
uv run python scripts/analyze_conversations.py
```

**What it does**:
1. **Stage 1 (Heuristic)**: Remove system messages, templates, file uploads
2. **Stage 2 (LLM)**: Identify natural conversations vs. automated responses
3. **Output**: Filtered dataset of high-quality conversations

**Use Cases**:
- Data cleaning for training
- Quality assessment
- Template detection
- Conversation pattern analysis

### Inspect Login

Debug authentication issues:

```bash
uv run python scripts/inspect_login.py
```

**Features**:
- Step-by-step login flow
- Screenshot at each step
- Session validation
- Cookie inspection
- Detailed error messages

## Project Structure

```
vf-data/
├── src/
│   ├── agent/                        # AI Agent (LangGraph)
│   │   ├── core.py                  # Main agent class & workflow
│   │   └── config.py                # Agent configuration
│   ├── cli/                          # Command-line interfaces
│   │   ├── main.py                  # Main CLI entry (dev/prod)
│   │   ├── scraper.py               # Scraping commands
│   │   ├── agent_repl.py            # Interactive agent testing REPL
│   │   ├── tui.py                   # Main TUI application
│   │   ├── daemon.py                # Daemon management
│   │   ├── shell.py                 # Simple shell/launcher
│   │   └── dev_entry.py             # Dev mode entry
│   ├── scraper/                      # Web scraping
│   │   ├── auth.py                  # Authentication & sessions
│   │   ├── chat_list_scraper.py     # Chat list scraping
│   │   ├── chat_message_scraper.py  # Message scraping
│   │   ├── central_db.py            # Chat database (JSONL)
│   │   ├── message_central_db.py    # Message database
│   │   └── data_quality.py          # Quality validation
│   ├── training/                     # DSPy optimization
│   │   ├── optimizer.py             # DSPy optimization engine
│   │   ├── data_loader.py           # Load conversations
│   │   ├── formatter.py             # Format data for DSPy
│   │   ├── models.py                # Training data models
│   │   └── signature.py             # DSPy signatures
│   ├── simulation/                   # Conversation simulation
│   │   ├── simulator.py             # Core simulation engine
│   │   ├── runner.py                # High-level runner
│   │   ├── grouper.py               # Message grouping
│   │   ├── models.py                # Simulation models
│   │   └── storage.py               # Result storage
│   ├── knowledge/                    # Knowledge retrieval
│   │   └── retriever.py             # Hybrid semantic + structured
│   ├── models.py                     # Pydantic data models
│   ├── config.py                     # Global configuration
│   └── utils.py                      # Shared utilities
├── scripts/                          # Analysis scripts
│   ├── create_export.py             # Data export package
│   ├── explore_conversations.py     # Conversation sampling
│   ├── analyze_conversations.py     # 2-stage filtering
│   └── inspect_login.py             # Login debugging
├── tests/                            # Test suite
│   ├── test_auth.py                 # Authentication
│   ├── test_chat_list.py            # Chat list scraping
│   ├── test_chat_messages.py        # Message scraping
│   ├── test_central_db.py           # Database
│   ├── test_user_scenario.py        # User scenarios
│   ├── test_goal_oriented.py        # Goal-oriented conversation
│   ├── test_closure.py              # Closure handling
│   ├── test_real_conversation.py    # Real chat replay
│   ├── test_context_pricing.py      # Pricing context
│   ├── test_brief_responses.py      # Response quality
│   ├── test_knowledge.py            # Knowledge retrieval
│   └── test_character_count_tool.py # Tool execution
├── data/                             # Data storage (gitignored)
│   ├── chat_list_master.jsonl       # Master chat list
│   ├── messages/                    # Per-chat messages
│   ├── runs/                        # Scraping runs
│   ├── sessions/                    # Browser sessions
│   ├── shadow/                      # Simulation results
│   ├── prompts/                     # System prompts
│   └── knowledge/                   # Knowledge base
│       ├── structured/              # Services, policies
│       └── semantic/                # FAQ with embeddings
├── logs/                             # Log files (gitignored)
├── db/                               # SQLite databases (gitignored)
├── export/                           # Export packages (gitignored)
├── .env                              # Credentials (gitignored)
├── .env.example                      # Template
├── pyproject.toml                    # Project config (uv)
└── README.md                         # This file
```

### Development vs Production

**Development Mode** (`soomgo-dev`):
- Base directory: `vf-data/` (project root)
- Data: `data/`, `logs/`, `db/`, `config/`
- For active development, testing, debugging

**Production Mode** (`soomgo`):
- Base directory: `~/.soomgo/` (home directory)
- Data: `~/.soomgo/data/`, `~/.soomgo/logs/`, etc.
- For deployed agent in production

## Testing

### Run All Tests

```bash
# Run entire test suite
uv run pytest

# Run specific test file
uv run pytest tests/test_agent.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src
```

### Test Categories

**Authentication & Scraping**:
```bash
uv run pytest tests/test_auth.py
uv run pytest tests/test_chat_list.py
uv run pytest tests/test_chat_messages.py
uv run pytest tests/test_central_db.py
```

**Agent & Conversation**:
```bash
uv run pytest tests/test_user_scenario.py
uv run pytest tests/test_goal_oriented.py
uv run pytest tests/test_closure.py
uv run pytest tests/test_real_conversation.py
```

**Knowledge & Context**:
```bash
uv run pytest tests/test_knowledge.py
uv run pytest tests/test_context_pricing.py
uv run pytest tests/test_brief_responses.py
```

**Tools**:
```bash
uv run pytest tests/test_character_count_tool.py
```

## Key Dependencies

### Core Frameworks
- **LangGraph / LangChain**: Agent workflow and LLM integration
- **DSPy**: Prompt optimization framework (Stanford)
- **OpenAI**: LLM API (GPT-4o, GPT-4o-mini) and embeddings
- **Playwright**: Browser automation for scraping

### Data & Validation
- **Pydantic**: Data validation and models
- **JSONL**: Efficient large-scale data storage

### CLI & UI
- **Click**: CLI framework
- **Rich**: Terminal formatting and progress bars
- **Textual**: TUI framework (dashboard, chat viewer)
- **Prompt Toolkit**: Interactive CLI

### Utilities
- **Loguru**: Beautiful logging
- **python-dotenv**: Environment variable management
- **uv**: Fast package manager

## Environment Configuration

### .env File

```env
# Soomgo credentials
SOOMGO_EMAIL=your-email@example.com
SOOMGO_PASSWORD=your-password

# OpenAI API
OPENAI_API_KEY=sk-...

# Browser settings
HEADLESS=false                    # true for production, false for debugging

# Agent settings (optional)
AGENT_MODEL=gpt-4o-mini
AGENT_TEMPERATURE=0.85
AGENT_MAX_TOKENS=300
```

### Agent Configuration

Edit `src/agent/config.py` or `data/prompts/system_prompt.txt`:

```python
# config.py
AGENT_CONFIG = {
    "model": "gpt-4o-mini",
    "temperature": 0.85,
    "max_tokens": 300,
    "system_prompt_path": "data/prompts/system_prompt.txt"
}
```

### Knowledge Base

Add services, policies, FAQs to knowledge base:

```
data/knowledge/
├── structured/
│   ├── services.json           # Add service definitions
│   └── policies.json           # Add policies
└── semantic/
    └── faq.json                # Add FAQs (auto-embed)
```

## Current Status

### Completed Features ✓

- [x] Chat list scraping (16,000+ chats)
- [x] Message scraping (285,000+ messages)
- [x] Central database (JSONL format)
- [x] Data quality system (graded validation)
- [x] Data export utilities
- [x] LangGraph-based AI agent
- [x] Conversation state management
- [x] Information extraction
- [x] Knowledge retrieval (hybrid semantic + structured)
- [x] DSPy prompt optimization
- [x] Conversation simulation
- [x] Chat viewer (TUI)
- [x] Dashboard (TUI)
- [x] Interactive REPL
- [x] Comprehensive test suite
- [x] Analysis scripts

### In Progress / Planned

- [ ] Production daemon (background process)
- [ ] Calendar tool integration
- [ ] Pricing database tool
- [ ] Attachment downloads
- [ ] Web UI (FastAPI + React)
- [ ] API endpoints
- [ ] Real-time monitoring dashboard
- [ ] Multi-agent coordination
- [ ] A/B testing framework

## Architecture Highlights

### LangGraph Workflow

```
┌─────────────────┐
│ Customer Message│
└────────┬────────┘
         ↓
┌────────────────────┐
│ Extract Information│  (Service, deadline, budget, etc.)
└────────┬───────────┘
         ↓
┌─────────────────────┐
│ Retrieve Knowledge  │  (Pricing, FAQ, policies)
└────────┬────────────┘
         ↓
┌─────────────────────┐
│ Generate Response   │  (Brief, natural, Korean)
└────────┬────────────┘
         ↓
┌─────────────────────┐
│ Update State        │  (Active, Waiting, Deferred, Closed)
└─────────────────────┘
```

### Data Flow

```
Scraping → Central DB → Agent Training → Simulation → Production
   ↓           ↓              ↓              ↓            ↓
Raw Data    JSONL       DSPy Optimize   Test Agent   Live Agent
16K chats   285K msgs   91% score       Historical   Real-time
                                        conversations
```

### Hybrid Knowledge Retrieval

```
Customer Query
    ↓
    ├─→ Structured Lookup (Keyword matching)
    │   ├─ services.json → "자소서: 10만원~"
    │   └─ policies.json → "환불 규정: ..."
    │
    └─→ Semantic Search (Embeddings + Cosine)
        └─ faq.json → Top-3 most similar FAQs

    ↓
Combined Context → Inject into Agent Prompt
```

## Performance & Scale

### Current Dataset
- **16,102 chats** (100% scraped)
- **285,864 messages** (avg 17.75/chat)
- **100% completion rate** (no missing data)
- **Quality score**: A-grade (90+)

### Agent Performance
- **Response time**: ~2-3s (GPT-4o-mini)
- **Context window**: Up to 16K tokens
- **Response length**: 50-300 chars (configurable)
- **Validation score**: 91% on real conversations

### Scraping Performance
- **Chat list**: ~5-10 minutes for 16K chats
- **Messages**: ~2-4 hours with 3 workers
- **Humanization delay**: 2-5s between requests
- **Rate limiting**: Exponential backoff on errors

## Troubleshooting

### Authentication Issues

```bash
# Test authentication
uv run python tests/test_auth.py

# Debug login flow
uv run python scripts/inspect_login.py

# Clear session and re-login
rm data/sessions/soomgo_session.json
uv run python tests/test_auth.py
```

### Scraping Issues

```bash
# Check browser visibility (set HEADLESS=false)
# Check screenshots in logs/
# Check run.log for detailed errors

# Test with small sample
python -m src.cli.scraper chats --dry-run --limit 10
```

### Agent Issues

```bash
# Test with interactive REPL
soomgo-dev chat

# Run specific test
uv run pytest tests/test_user_scenario.py -v

# Check agent logs
tail -f logs/agent.log
```

### Knowledge Retrieval Issues

```bash
# Test retrieval
uv run pytest tests/test_knowledge.py -v

# Check embeddings
python -c "from src.knowledge.retriever import KnowledgeRetriever; r = KnowledgeRetriever(); print(r.retrieve('가격'))"
```

## Contributing

This is a research/personal project. For questions or issues:

1. Check existing tests: `uv run pytest tests/`
2. Review logs: `logs/` directory
3. Check documentation: This README
4. Debug with: `--dry-run` flags and `HEADLESS=false`

## License

Private/Internal Use

## Acknowledgments

- **LangGraph**: Agent workflow framework
- **DSPy**: Prompt optimization (Stanford NLP)
- **OpenAI**: GPT-4o and embeddings API
- **Playwright**: Browser automation
- **uv**: Fast Python package manager
