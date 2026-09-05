# CLAUDE.md - Technical Notes for LLM Council

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

LLM Council is a 3-stage deliberation system where multiple LLMs collaboratively answer user questions. The key innovation is anonymized peer review in Stage 2, preventing models from playing favorites.

## Architecture

### Backend Structure (`backend/`)

**`config.py`**
- Contains `COUNCIL_MODELS` (list of OpenRouter model identifiers)
- Contains `CHAIRMAN_MODEL` (model that synthesizes final answer)
- Uses environment variable `OPENROUTER_API_KEY` from `.env`
- `require_api_key()` raises `MissingAPIKeyError` with an actionable message - never let a missing key surface as "all models failed"
- `DATA_DIR` is **absolute** (`~/.llm-council/conversations`, override via `LLM_COUNCIL_HOME`). It must stay absolute: the CLI and MCP server run from arbitrary working directories and would otherwise create a second store per repo.
- Backend runs on **port 8001** (NOT 8000 - user had another app on 8000)

**`profiles.py`**
- `Profile` = models + chairman + rubric + output schema + context budget + `peer_review` flag
- `quick` (2 models, no Stage 2), `decision` (default), `research`
- Every entry point takes a `Profile`; `_resolve(None)` falls back to `decision`
- `peer_review=False` skips Stage 2 entirely - both `run_full_council` and the streaming endpoint must honour this (the stream emits `stage2_skipped`)

**`context.py`**
- `ContextBlock` + `build_prompt()`: context blocks first, question last
- Blocks share `profile.max_context_chars` evenly; truncation is head+tail with a visible marker
- `git_diff_block()` / `repo_info_block()` shell out to git and return `None` outside a repo

**`cli.py`** - `council ask | profiles | log`, installed via `[project.scripts]`

**`mcp_server.py`** - MCP (SDK **2.x**: `MCPServer`, not `FastMCP`)
- `council_start` + `council_result` are split because a deep run takes 1-3 minutes, longer than most MCP clients wait on one tool call
- `council_ask` is blocking and quick-profile only
- `_RUNS` is in-memory: run ids do not survive a server restart

**`export.py`** - ADR writer, `docs/decisions/NNNN-slug.md`, numbering from existing files

**`openrouter.py`**
- `query_model()`: Single async model query, 2 retries with exponential backoff on timeouts / 429 / 5xx
- `query_models_parallel()`: Parallel queries using `asyncio.gather()`
- Returns dict with 'content', 'reasoning_details', 'usage' and 'duration'
- Graceful degradation: returns None on failure, continues with successful responses
- **Exception:** `OpenRouterAuthError` (401/403) propagates instead of degrading - a bad key breaks every model, so failing loudly is correct

**`council.py`** - The Core Logic
- `stage1_collect_responses()`: Parallel queries to all council models
- `stage2_collect_rankings()`:
  - Anonymizes responses as "Response A, B, C, etc."
  - Creates `label_to_model` mapping for de-anonymization
  - Prompts models to evaluate and rank (with strict format requirements)
  - Returns tuple: (rankings_list, label_to_model_dict)
  - Each ranking includes both raw text and `parsed_ranking` list
- `stage3_synthesize_final()`: Chairman synthesizes from all responses + rankings
- `parse_ranking_from_text()`: Extracts "FINAL RANKING:" section, handles both numbered lists and plain format
- `calculate_aggregate_rankings()`: Computes average rank position across all peer evaluations

**`storage.py`**
- JSON-based conversation storage in `data/conversations/`
- Each conversation: `{id, created_at, messages[]}`
- Assistant messages contain: `{role, stage1, stage2, stage3}`
- `add_assistant_message(..., metadata=...)` persists `label_to_model`, `aggregate_rankings`, `profile` and `run_stats`, so a reopened conversation still shows its rankings. The field is optional on read, so pre-0.2 files still load.

**`main.py`**
- FastAPI app with CORS enabled for localhost:5173 and localhost:3000
- POST `/api/conversations/{id}/message` returns metadata in addition to stages
- Metadata includes: label_to_model mapping and aggregate_rankings

### Frontend Structure (`frontend/src/`)

**`App.jsx`**
- Main orchestration: manages conversations list and current conversation
- Handles message sending and metadata storage
- Important: metadata is stored in the UI state for display but not persisted to backend JSON

**`components/ChatInterface.jsx`**
- Multiline textarea (3 rows, resizable)
- Enter to send, Shift+Enter for new line
- User messages wrapped in markdown-content class for padding

**`components/Stage1.jsx`**
- Tab view of individual model responses
- ReactMarkdown rendering with markdown-content wrapper

**`components/Stage2.jsx`**
- **Critical Feature**: Tab view showing RAW evaluation text from each model
- De-anonymization happens CLIENT-SIDE for display (models receive anonymous labels)
- Shows "Extracted Ranking" below each evaluation so users can validate parsing
- Aggregate rankings shown with average position and vote count
- Explanatory text clarifies that boldface model names are for readability only

**`components/Stage3.jsx`**
- Final synthesized answer from chairman
- Green-tinted background (#f0fff0) to highlight conclusion

**Styling (`*.css`)**
- Light mode theme (not dark mode)
- Primary color: #4a90e2 (blue)
- Global markdown styling in `index.css` with `.markdown-content` class
- 12px padding on all markdown content to prevent cluttered appearance

## Key Design Decisions

### Stage 2 Prompt Format
The Stage 2 prompt is very specific to ensure parseable output:
```
1. Evaluate each response individually first
2. Provide "FINAL RANKING:" header
3. Numbered list format: "1. Response C", "2. Response A", etc.
4. No additional text after ranking section
```

This strict format allows reliable parsing while still getting thoughtful evaluations.

### De-anonymization Strategy
- Models receive: "Response A", "Response B", etc.
- Backend creates mapping: `{"Response A": "openai/gpt-5.1", ...}`
- Frontend displays model names in **bold** for readability
- Users see explanation that original evaluation used anonymous labels
- This prevents bias while maintaining transparency

### Error Handling Philosophy
- Continue with successful responses if some models fail (graceful degradation)
- Never fail the entire request due to single model failure
- Log errors but don't expose to user unless all models fail

### UI/UX Transparency
- All raw outputs are inspectable via tabs
- Parsed rankings shown below raw text for validation
- Users can verify system's interpretation of model outputs
- This builds trust and allows debugging of edge cases

## Important Implementation Details

### Relative Imports
All backend modules use relative imports (e.g., `from .config import ...`) not absolute imports. This is critical for Python's module system to work correctly when running as `python -m backend.main`.

### Port Configuration
- Backend: 8001 (changed from 8000 to avoid conflict)
- Frontend: 5173 (Vite default)
- Update both `backend/main.py` and `frontend/src/api.js` if changing

### Markdown Rendering
All ReactMarkdown components must be wrapped in `<div className="markdown-content">` for proper spacing. This class is defined globally in `index.css`.

### Model Configuration
Models are hardcoded in `backend/config.py`. Chairman can be same or different from council members. The current default is Gemini as chairman per user preference.

## Common Gotchas

1. **Module Import Errors**: Always run backend as `python -m backend.main` from project root, not from backend directory
2. **CORS Issues**: Frontend must match allowed origins in `main.py` CORS middleware
3. **Ranking Parse Failures**: If models don't follow format, fallback regex extracts any "Response X" patterns in order
4. **Missing Metadata**: Metadata is ephemeral (not persisted), only available in API responses

## Known biases in the ranking (Phase 2 backlog)

Deliberately still open, to be fixed after a week of real usage:
1. **Models rank their own responses** - `stage2_collect_rankings()` sends one shared prompt to all `profile.models`. Fix: one prompt per evaluator excluding its own answer, then normalise positions to percentiles since lists become n-1 long.
2. **The chairman sees model names** - `build_chairman_prompt()` emits `Model: {name}`, which undoes Stage 2's anonymisation. Fix: label-only, de-anonymise in the output layer.
3. Rankings correlate with verbosity. The rubric (per profile) mitigates but does not solve this.

Report the ranking as a weak signal, never as a verdict.

## Future Enhancement Ideas

- Configurable council/chairman via UI instead of config file
- Streaming responses instead of batch loading
- Export conversations to markdown/PDF
- Model performance analytics over time
- Custom ranking criteria (not just accuracy/insight)
- Support for reasoning models (o1, etc.) with special handling

## Testing Notes

```bash
uv sync --group dev
uv run pytest        # 69 tests, ~1s, no API key
```

`tests/conftest.py` replaces `query_model` - the single external dependency -
with a stub that answers by prompt type. So the suite runs offline and CI needs
no secret. See `tests/README.md` for what each file covers.

**What the suite does not prove:** that a model id in `config.py` still exists on
OpenRouter, or that the key is valid. Only a real run shows that; the escalation
procedure is in `ANLEITUNG-KONZIL.md`.

When changing `council.py`, `context.py` or `main.py`, run the suite before
pushing - it covers the anonymisation in Stage 2, the per-profile rubric and
output schema, metadata persistence and the streaming event sequence, all of
which are easy to break silently.

## Data Flow Summary

```
User Query
    ↓
Stage 1: Parallel queries → [individual responses]
    ↓
Stage 2: Anonymize → Parallel ranking queries → [evaluations + parsed rankings]
    ↓
Aggregate Rankings Calculation → [sorted by avg position]
    ↓
Stage 3: Chairman synthesis with full context
    ↓
Return: {stage1, stage2, stage3, metadata}
    ↓
Frontend: Display with tabs + validation UI
```

The entire flow is async/parallel where possible to minimize latency.
