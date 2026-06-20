# NGO Ops Agent

A multi-agent CLI assistant for NGO operations: donor tracking, volunteer coordination, event planning, and task reminders. Built as a prototype for the NayePankh Foundation AI Agent internship to demonstrate persistent memory, external API integration, multi-agent coordination, and task automation.

No LLM API key is required. Intent routing and FAQ matching are handled with rule-based logic (keyword cascades and fuzzy string matching), with clearly marked extension points for plugging in a real model later.

## How it works

A `CoordinatorAgent` receives each message, classifies its intent, and dispatches it to one of five specialist agents:

- `DonorAgent` — records donations, maintains running totals per donor, drafts thank-you messages
- `VolunteerAgent` — registers volunteers and their skills, tracks availability
- `EventAgent` — plans events, checking live weather (Open-Meteo) and public holiday (Nager.Date) data before confirming
- `TaskAgent` — creates and tracks reminders, including ones created automatically by other agents
- `FAQAgent` — answers common questions via fuzzy matching against a local knowledge base, and logs anything it can't answer

Agents aren't fully isolated behind the coordinator — `EventAgent` calls `TaskAgent` directly to schedule a logistics-prep reminder whenever an event is planned, with no user request needed. That's the one piece of genuine agent-to-agent delegation in the system; everything else goes through the coordinator.

Intent classification is a priority cascade over keyword sets (see `CoordinatorAgent._classify`), with a basic question-detection heuristic so that a sentence like "Do you offer tax exemption certificates for donations?" routes to the FAQ agent instead of being misread as a command to record a donation. The coordinator also tracks a `pending` follow-up state, so if an agent asks a clarifying question ("what date?"), the next message is merged with the original request and retried by the same agent rather than being reclassified from scratch.

## Memory

`memory.py` wraps a SQLite database (`ngo_ops_memory.db`) that persists across runs: donors, volunteers, tasks, events, the full conversation log, and any FAQ questions the agent couldn't answer. Close the program and reopen it later — the data is still there. A `session_context` dict on the `Memory` object holds short-term state (recent turns, pending follow-ups) for the current process only.

## External APIs

`apis.py` integrates two free, key-free public APIs, called by `EventAgent` when planning an event:

- **Open-Meteo** — weather forecast for the event date
- **Nager.Date** — public holiday lookup, to flag scheduling conflicts

Both calls are wrapped in `try/except` with a short timeout. If the network is unavailable, the agent reports the forecast as unreachable and continues rather than crashing.

## Task automation

- `EventAgent` automatically creates a `TaskAgent` reminder for logistics/headcount whenever an event is scheduled.
- `DonorAgent` auto-drafts a thank-you message for every donation logged.
- `CoordinatorAgent.daily_summary()` generates a cross-agent status report (donor totals, open tasks, planned events, unanswered question backlog) on request.
- `FAQAgent` logs every unmatched question to `unanswered_questions` instead of discarding it, so the FAQ knowledge base can be expanded based on real usage.

## Project structure

```
ngo-ops-agent/
├── main.py           # CLI entry point — scripted demo and interactive chat mode
├── agents.py         # CoordinatorAgent + five specialist agents
├── memory.py         # SQLite-backed persistent + session memory
├── apis.py           # Open-Meteo and Nager.Date API clients
├── data.py           # seed data and FAQ knowledge base
├── pyproject.toml    # project metadata and dependencies
├── uv.lock           # locked dependency versions
├── .python-version   # pinned Python version for uv
├── .gitignore
└── README.md
```

## Setup

Requires Python (version pinned in `.python-version`) and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

This creates `.venv` and installs dependencies from `uv.lock`.

## Usage

```bash
uv run main.py            # scripted demo covering every feature
uv run main.py --chat     # interactive mode
uv run main.py --reset    # wipe ngo_ops_memory.db and start fresh
```

Example interactive session:

```
You: Record a donation of 3000 from Anita Sharma
You: I want to volunteer, my name is Dev Patel, skills are fundraising
You: Plan an outdoor event on 2026-08-01
You: Remind us to order event banners
You: Give me a summary report
```

Quick lookups in chat mode: `donors`, `volunteers`, `tasks`, `events`, `unanswered`, `history`.

## Configuration

Before pointing this at a real organization:

- Set `FOUNDATION_LOCATION` in `data.py` to the actual operating city (lat/lon) so weather checks are relevant.
- Replace `SEED_DONORS` and `SEED_VOLUNTEERS` with real records, or wire `memory.py` to an existing CRM/spreadsheet export.
- Replace `FAQ_KNOWLEDGE_BASE` in `data.py` with the organization's actual mission statement, programs, and FAQs.

## Known limitations

- **FAQ coverage is fixed.** `FAQAgent` matches against a small hardcoded list via `difflib`; it has no general language understanding, so questions outside that list always fall through to the generic fallback. Unmatched questions are logged to `unanswered_questions` for manual review rather than dropped silently — visible via the `unanswered` command in chat mode or in the daily summary count.
- **Date and amount parsing are regex-based**, not a full NLU pipeline. Edge cases in phrasing (ambiguous dates, unusual number formats) may not parse correctly.
- **Single-user, single-process.** The SQLite backend is not built for concurrent writers; fine for a CLI prototype, not for a multi-user deployment.

## Extending with an LLM

Every point in the code suited for an LLM call is marked `# LLM UPGRADE POINT` (currently in `FAQAgent.handle`). A minimal integration:

```python
import requests

def call_llm(prompt):
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": "YOUR_API_KEY",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    return response.json()["content"][0]["text"]
```

The memory, API, and automation layers don't need to change — only the FAQ/intent logic gets replaced with a real model call.

## Roadmap

- Replace seed data with real Foundation records and FAQ content
- Add a messaging channel (WhatsApp Business API, Telegram, or a web form) so the coordinator isn't limited to a terminal
- Swap rule-based FAQ matching for an LLM-backed implementation
- Send donor thank-you messages via an email API (e.g. SendGrid) instead of printing them

## License

MIT
