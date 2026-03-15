# AI Mode — Intelligent Research Search Engine

A research search engine that takes a question, runs it through a multi-step AI pipeline, and delivers a structured answer with inline citations and source links. Built with LangGraph on the backend and React on the frontend.

Inspired by Google's AI Mode and Perplexity.

## How It Works

The backend runs a 7-node LangGraph pipeline. Each node handles one part of the research process:

```
User Question
  │
  ▼
Query Rewriter ──→ Search Planner ──→ Web Search (Serper/Google)
  │
  ▼
Document Filter ──→ Source Summarizer ──→ Answer Generator ──→ Citation Injector
  │
  ▼
Cited Answer + Sources
```

**Fast tasks** (rewriting, filtering, summarizing) use **Llama 4 Scout 17B** via Groq.  
**Heavy tasks** (answer generation, citations) use **GPT-OSS 120B** via Groq.

The frontend streams pipeline progress over SSE so you can watch each step complete in real time.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, Tailwind CSS v4, shadcn/ui, Vite |
| Backend | Python, FastAPI, LangGraph, LangChain |
| LLMs | Llama 4 Scout 17B (fast) · GPT-OSS 120B (reasoning) |
| LLM Provider | Groq |
| Web Search | Serper API (Google results) |

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Groq API key](https://console.groq.com/keys)
- [Serper API key](https://serper.dev)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:

```
GROQ_API_KEY=your_groq_key
SERPER_API_KEY=your_serper_key
```

Start the server:

```bash
python main.py
```

The API runs at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Project Structure

```
AImode/
├── backend/
│   ├── main.py           # FastAPI server, SSE streaming endpoint
│   ├── graph.py          # LangGraph pipeline wiring
│   ├── nodes.py          # All 7 node implementations
│   ├── state.py          # TypedDict shared state definition
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Main app — state management + view routing
│   │   ├── index.css               # Tailwind config + dark theme
│   │   └── components/
│   │       ├── SearchBar.jsx       # Search input + suggestion chips
│   │       ├── ThinkingSteps.jsx   # Real-time pipeline progress
│   │       ├── LoadingAnimation.jsx
│   │       ├── ResultCard.jsx      # Markdown answer + sources section
│   │       └── SourceCard.jsx      # Individual source card
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
└── README.md
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check — reports which API keys are configured |
| `POST` | `/api/search` | Run the full pipeline, return the final result |
| `POST` | `/api/search/stream` | Stream each step's progress via SSE |

### SSE Stream Format

Each event is a JSON object with a `step` field indicating which pipeline node just completed, plus any relevant data from that step:

```json
data: {"step": "query_rewriter", "rewritten_query": "...", "steps_completed": ["query_rewriter"]}
data: {"step": "web_search", "documents_found": 12, "steps_completed": ["query_rewriter", "search_planner", "web_search"]}
data: {"step": "complete"}
```
