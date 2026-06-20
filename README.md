# NGO-OPS-AGENT — AI Agent Prototype
**AI Agent Internship Deliverable**

A working multi-agent assistant for NGO operations: donor management,
volunteer coordination, event planning, and task automation — built as a
single, dependency-light Python project that runs entirely on your machine.

## Why this design

No paid LLM API key is required to run it (you said you don't have one yet),
but the architecture is built so a real LLM can be dropped in later with
minimal changes — every place you'd plug one in is marked
`# LLM UPGRADE POINT` in the code, plus a ready-made snippet is included near
the bottom of this file.

"Intelligence" here comes from two things instead of an LLM:
1. **Rule-based intent routing** — the Coordinator reads each message and
   matches it against keyword patterns to decide which specialist agent
   should respond (see `agents.py: CoordinatorAgent._classify`).
2. **Fuzzy text matching** for FAQs, using Python's built-in `difflib`, so
   users don't have to type questions in an exact format.

## How each internship requirement is met

| Requirement | Where it lives | What it does |
|---|---|---|
| **Add Memory** | `memory.py` | A SQLite database (`nayapankh_memory.db`) gives the agents **long-term memory** that survives across runs — donors, volunteers, tasks, events, and the full conversation log. A `session_context` dict gives **short-term/working memory** within a single run. |
| **Connect APIs** | `apis.py` | Calls two real, free, no-key-needed public APIs: **Open-Meteo** (weather forecasts) and **Nager.Date** (public holidays), used by the Event Agent to assess event feasibility. Wrapped in try/except so the system degrades gracefully if offline. |
| **Multi-Agent System** | `agents.py` | A `CoordinatorAgent` routes work to five specialists: `DonorAgent`, `VolunteerAgent`, `EventAgent`, `TaskAgent`, `FAQAgent`. Agents also talk to each other — see "agent-to-agent automation" below. |
| **Automate Tasks** | `agents.py`, `main.py` | (1) `EventAgent` automatically asks `TaskAgent` to create a logistics-prep reminder whenever an event is planned, with no user request needed — true agent-to-agent automation. (2) `DonorAgent` auto-drafts a thank-you message for every donation. (3) `CoordinatorAgent.daily_summary()` auto-generates a cross-agent status report on demand. |

## Project structure

```
nayapankh_agent/
├── main.py      # entry point: scripted demo + interactive chat mode
├── agents.py    # Coordinator + 5 specialist agents (the multi-agent system)
├── memory.py    # SQLite-backed long-term + short-term memory
├── apis.py      # Open-Meteo + Nager.Date API connectors
├── data.py      # sample seed data + FAQ knowledge base (edit freely)
└── README.md    # this file
```

## How to run it

Requires Python 3.8+ and the `requests` library (`pip install requests` if
you don't have it).

```bash
# 1. Scripted demo — runs a fixed conversation showing every feature.
#    Best for screenshots / your report.
python3 main.py

# 2. Interactive mode — type your own messages.
python3 main.py --chat

# 3. Reset memory and start fresh (deletes nayapankh_memory.db)
python3 main.py --reset
```

In interactive mode, try:
- `Record a donation of 3000 from Anita Sharma`
- `I want to volunteer, my name is Dev Patel, skills are fundraising`
- `Plan an outdoor event on 2026-08-01` (calls live weather + holiday APIs)
- `Remind us to order event banners`
- `Give me a summary report`
- `How can I donate?`
- Quick lookups: type `donors`, `volunteers`, `tasks`, or `events`

Run the script twice in a row and you'll see donor totals and task counts
carry over — that's the persistent memory at work. Open
`nayapankh_memory.db` with any SQLite browser (e.g. "DB Browser for SQLite")
to literally see what the agents remember.

> **Note on the live APIs:** Open-Meteo and Nager.Date are genuinely free,
> public, no-signup endpoints — they will work as soon as you run this on a
> machine with normal internet access. If a network is firewalled (e.g. a
> locked-down lab PC), the agent will say the service is unreachable instead
> of crashing, then carry on with the rest of the conversation.

## Customizing for the real Foundation

- Edit `FOUNDATION_LOCATION` in `data.py` with the Foundation's actual city
  (lat/lon) so weather checks are accurate for real event locations.
- Replace `SEED_DONORS` / `SEED_VOLUNTEERS` with real records, or wire
  `memory.py` up to a real spreadsheet/CRM export.
- Replace `FAQ_KNOWLEDGE_BASE` in `data.py` with the Foundation's real
  mission statement, programs, and contact info.

## Upgrading to a real LLM (optional, once you have an API key)

Drop this into `FAQAgent.handle()` in `agents.py` (or anywhere marked
`# LLM UPGRADE POINT`) to replace rule-based logic with real generated text:

```python
import requests

def call_llm(prompt):
    resp = requests.post(
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
    return resp.json()["content"][0]["text"]
```

Once that's in place, the same multi-agent / memory / API-automation
architecture carries over unchanged — only the "thinking" inside each agent
gets smarter.

## Suggested next steps for the internship

1. Swap in the Foundation's real data and FAQ content.
2. Add a real channel connector (WhatsApp Business API, Telegram bot, or a
   simple web form) so the Coordinator receives messages from outside the
   terminal.
3. Add the LLM upgrade above for genuinely generative responses.
4. Add an email-sending API (e.g. SendGrid) so `DonorAgent`'s thank-you
   drafts are actually sent, not just printed.
