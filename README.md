# Personal Assistant — Second Brain

An AI-powered personal memory assistant that captures, organises, and retrieves your notes using natural language. Tell it anything — meetings, tasks, reminders, facts — and ask it back conversationally.

**Stack:** Python · LlamaIndex · ChromaDB · Google Gemini · OpenTelemetry · Click

---

## How It Works

User input flows through a multi-agent pipeline:

```
CLI (tell / ask / remind / chat)
        │
   RouterAgent          ← classifies intent
        │
   ┌────┴──────────────────────┐
   │           │               │
NoteCaptureAgent  QueryAgent  ReminderAgent
   │           │               │
   └────┬──────────────────────┘
        │
  LlamaIndexManager
  ├── Gemini LLM + Embeddings
  └── ChromaDB (vector store)
```

- **NoteCaptureAgent** — extracts dates, classifies note type (event/task/reminder/fact), scrubs PII, stores in ChromaDB
- **QueryAgent** — semantic search with optional date-range filters
- **ReminderAgent** — queries notes with future `date_epoch` metadata, groups by date
- **RouterAgent** — keyword-based intent classification routes to the right agent

---

## Prerequisites

- Python 3.10+
- A free [Google Gemini API key](https://aistudio.google.com/app/apikey)

---

## Installation

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd personal-assistant

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key
echo "GEMINI_API_KEY=your_key_here" > .env
```

---

## Running the App

All commands use the `python -m assistant` entry point.

### Store a note

```bash
python -m assistant tell "Meeting with Sarah tomorrow at 3pm"
python -m assistant tell "Remind me to call the dentist next week"
python -m assistant tell "Mom's birthday is June 15th"
python -m assistant tell "Need to finish the quarterly report by Friday"

# Omit the message to be prompted interactively
python -m assistant tell
```

### Ask a question

```bash
python -m assistant ask "When is my meeting with Sarah?"
python -m assistant ask "Where does my sister work?"
python -m assistant ask "What tasks do I need to complete?"
python -m assistant ask "What do I have scheduled this week?"

# Omit the question to be prompted interactively
python -m assistant ask
```

### View upcoming reminders

```bash
# Default: look 7 days ahead
python -m assistant remind

# Custom window
python -m assistant remind --days 14
python -m assistant remind --days 3
```

### Chat mode (intent routing)

```bash
# Interactive loop — type 'exit' to quit
python -m assistant chat

# Single message
python -m assistant chat "Remember my passport expires in May"
```

In chat mode, the RouterAgent automatically decides whether to store, query, or surface reminders based on your message.

### Manage stored notes

```bash
# List all notes (default: up to 20)
python -m assistant notes list
python -m assistant notes list --limit 50

# Search by keyword
python -m assistant notes search "dentist"
python -m assistant notes search "meeting"
```

### Manage your profile

```bash
# View current profile
python -m assistant profile show

# Set fields (supports dotted paths for nested keys)
python -m assistant profile set name "Pritika"
python -m assistant profile set timezone "IST"
python -m assistant profile set default_reminder_time "08:00"
python -m assistant profile set preferences.theme "dark"
```

### Run the evaluation suite

```bash
python -m assistant eval
```

Seeds the index with sample notes, runs 10 test scenarios (store, query, remind), and prints pass/fail metrics:

```
Running evaluation suite...

Overall pass rate: 80%
✅ Overall Pass Rate: 80%
✅ Query Recall: 83%
✅ Storage Accuracy: 80%
✅ Reminder Coverage: 100%
```

---

## Configuration

Edit `config.yaml` at the project root to tune the system:

```yaml
llm:
  model: "models/gemini-2.0-flash-exp"
  temperature: 0.7

embeddings:
  model: "models/text-embedding-004"

chroma:
  persist_dir: "./data/chroma_db"
  collection_name: "personal_notes"

chat:
  memory_buffer_tokens: 3000
  context_window: 10

indexing:
  chunk_size: 512
  chunk_overlap: 50
```

---

## Project Structure

```
personal-assistant/
├── assistant/
│   ├── __init__.py
│   └── __main__.py              # Entry point: python -m assistant
│
├── src/
│   ├── llama_index_setup.py     # LlamaIndex + ChromaDB + Gemini setup
│   ├── date_parser.py           # Natural language date extraction
│   ├── note_classifier.py       # Note type classification
│   ├── guardrails.py            # PII scrubbing (email, phone, SSN, CC)
│   │
│   ├── agents/
│   │   ├── router_agent.py      # Intent classification + delegation
│   │   ├── note_capture_agent.py
│   │   ├── query_agent.py
│   │   └── reminder_agent.py
│   │
│   ├── cli/
│   │   └── commands.py          # All Click commands
│   │
│   ├── evals/
│   │   ├── metrics.py           # Evaluation runner + metrics
│   │   └── test_cases.py        # 10 evaluation scenarios
│   │
│   └── observability/
│       └── otel.py              # OpenTelemetry → logs/otel_spans.jsonl
│
├── data/
│   ├── sample_notes.py          # Sample notes used in eval
│   ├── user_profile.json        # User preferences
│   └── chroma_db/               # Vector database (created on first run)
│
├── logs/
│   └── otel_spans.jsonl         # Trace logs (appended on each run)
│
├── config.yaml
├── requirements.txt
└── .env                         # GEMINI_API_KEY (not committed)
```

---

## Observability

Every command writes OpenTelemetry spans to `logs/otel_spans.jsonl`. Watch traces accumulate in real time:

```bash
tail -f logs/otel_spans.jsonl
```

Each span captures intent type, note type, date presence, success/failure, and exception traces.

---

## Troubleshooting

**API key not found**
```bash
# Verify .env is set up correctly
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GEMINI_API_KEY'))"
```

**Reset the vector database**
```bash
rm -rf data/chroma_db/
# It will be recreated automatically on the next run
```

**Import errors**
```bash
# Make sure you're inside the virtual environment
which python   # Should show venv/bin/python

pip install -r requirements.txt --force-reinstall
```
