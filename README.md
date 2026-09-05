# LLM Council

![llmcouncil](header.jpg)

The idea of this repo is that instead of asking a question to your favorite LLM provider (e.g. OpenAI GPT 5.1, Google Gemini 3.0 Pro, Anthropic Claude Sonnet 4.5, xAI Grok 4, eg.c), you can group them into your "LLM Council". This repo is a simple, local web app that essentially looks like ChatGPT except it uses OpenRouter to send your query to multiple LLMs, it then asks them to review and rank each other's work, and finally a Chairman LLM produces the final response.

In a bit more detail, here is what happens when you submit a query:

1. **Stage 1: First opinions**. The user query is given to all LLMs individually, and the responses are collected. The individual responses are shown in a "tab view", so that the user can inspect them all one by one.
2. **Stage 2: Review**. Each individual LLM is given the responses of the other LLMs. Under the hood, the LLM identities are anonymized so that the LLM can't play favorites when judging their outputs. The LLM is asked to rank them in accuracy and insight.
3. **Stage 3: Final response**. The designated Chairman of the LLM Council takes all of the model's responses and compiles them into a single final answer that is presented to the user.

## Vibe Code Alert

This project was 99% vibe coded as a fun Saturday hack because I wanted to explore and evaluate a number of LLMs side by side in the process of [reading books together with LLMs](https://x.com/karpathy/status/1990577951671509438). It's nice and useful to see multiple responses side by side, and also the cross-opinions of all LLMs on each other's outputs. I'm not going to support it in any way, it's provided here as is for other people's inspiration and I don't intend to improve it. Code is ephemeral now and libraries are over, ask your LLM to change it in whatever way you like.

## Anleitung ohne Technik

Wann sich ein Konzil-Lauf lohnt, wie man eine brauchbare Frage stellt und was man
dem Ergebnis nicht glauben darf: **[ANLEITUNG-KONZIL.md](ANLEITUNG-KONZIL.md)** —
geschrieben für Nutzung, nicht für Entwicklung.

## Use it from any repository

The council is not only a web app. It runs headless, so you can call it from any
project.

### CLI

```bash
uv tool install --editable .          # once; puts `council` on your PATH

council profiles                      # what is available
council ask "Monorepo oder Polyrepo fuer 4 Entwickler?"
council ask "Wo ist der Bias in dieser Datei?" --file backend/council.py
council ask "Ist dieser Refactor sicher?" --diff main --adr
council log                           # recent runs
```

Useful flags: `--profile`, `--file` (repeatable), `--diff [REF]`, `--stdin`,
`--out FILE`, `--json`, `--adr` (writes `docs/decisions/NNNN-slug.md` into the
current repo), `--quiet`.

Runs are stored in `~/.llm-council/conversations` (override with
`LLM_COUNCIL_HOME`), so the CLI, the MCP server and the web UI share one history.

### Claude Code (MCP + skill)

```bash
claude mcp add --scope user council -- \
  uv run --directory /path/to/llm-council python -m backend.mcp_server
```

That makes `council_start`, `council_result`, `council_ask`, `council_profiles`
and `council_write_adr` available in every project. Install the bundled plugin for
the `/council` command and the gatekeeper skill:

```bash
/plugin marketplace add /path/to/llm-council
/plugin install council@llm-council
```

### Profiles

| Profile | Models | Peer review | Calls | Latency | For |
|---|---|---|---|---|---|
| `quick` | 2 | no | ~3 | ~20-40s | cheap second opinion |
| `decision` | 4 | yes | ~9 | ~90-180s | architecture / technical decisions |
| `research` | 4 | yes | ~9 | ~90-180s | open questions |

### When it is worth the money

A `decision` run costs ~9 model calls and 1-3 minutes. Only spend that when the
question is expensive to reverse, has no cheap ground truth (no test or benchmark
settles it), and is open enough that different models explore different branches.
Everything else: ask one model.

The peer ranking measures how models rate each other's writing, not correctness.
Treat it as a weak signal.

## Setup

### 1. Install Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for project management.

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 2. Configure API Key

Create a `.env` file in the project root:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

Get your API key at [openrouter.ai](https://openrouter.ai/). Make sure to purchase the credits you need, or sign up for automatic top up.

### 3. Configure Models (Optional)

Edit `backend/config.py` to customize the council:

```python
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]

CHAIRMAN_MODEL = "google/gemini-3-pro-preview"
```

## Running the Application

**Option 1: Use the start script**
```bash
./start.sh
```

**Option 2: Run manually**

Terminal 1 (Backend):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## Tech Stack

- **Backend:** FastAPI (Python 3.10+), async httpx, OpenRouter API
- **Frontend:** React + Vite, react-markdown for rendering
- **Storage:** JSON files in `data/conversations/`
- **Package Management:** uv for Python, npm for JavaScript
