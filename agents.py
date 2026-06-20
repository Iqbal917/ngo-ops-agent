"""
agents.py
---------
The multi-agent system itself.

  CoordinatorAgent  -- reads each user message, decides which specialist
                       agent should handle it (simple keyword/intent
                       routing -- no paid LLM required), and can also
                       generate cross-agent summary reports.
       |
       |-- DonorAgent      -- records donations, auto-drafts thank-you notes
       |-- VolunteerAgent  -- registers volunteers, matches them to events
       |-- EventAgent      -- plans events: calls the weather + holiday APIs,
       |                      then AUTOMATICALLY creates a follow-up task via
       |                      TaskAgent (agent-to-agent collaboration)
       |-- TaskAgent       -- creates/lists/completes tasks & reminders
       |-- FAQAgent        -- answers common questions via fuzzy matching
       |                      against data.FAQ_KNOWLEDGE_BASE

This is intentionally "intelligence without an LLM": intent detection uses
keyword scoring and FAQ answers use difflib fuzzy text matching. Swap in a
real LLM call (see README) anywhere you see `# LLM UPGRADE POINT` to make
responses fully generative once you have an API key.
"""

import difflib
import re
from datetime import datetime

from apis import get_weather_forecast, is_public_holiday
from data import FAQ_KNOWLEDGE_BASE, FOUNDATION_LOCATION


def parse_flexible_date(text):
    """
    Finds a date-like token in free text and normalizes it to 'YYYY-MM-DD'.
    Accepts YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, and 2-digit-year variants
    like DD-MM-YY (e.g. '26-06-26' -> '2026-06-26'), using the day-month-year
    convention common in India. Returns None if no valid date is found.
    """
    match = re.search(r"\b(\d{1,4})[/-](\d{1,2})[/-](\d{1,4})\b", text)
    if not match:
        return None
    a, b, c = match.groups()
    try:
        if len(a) == 4:
            dt = datetime(int(a), int(b), int(c))  # YYYY-MM-DD
        elif len(c) == 4:
            dt = datetime(int(c), int(b), int(a))  # DD-MM-YYYY
        else:
            year = int(c)
            year += 2000 if year < 100 else 0
            dt = datetime(year, int(b), int(a))  # DD-MM-YY
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


class BaseAgent:
    name = "BaseAgent"

    def __init__(self, memory):
        self.memory = memory

    def say(self, message):
        print(f"[{self.name}] {message}")
        self.memory.log_conversation(role="agent", agent=self.name, message=message)
        return message


class DonorAgent(BaseAgent):
    name = "DonorAgent"

    def handle(self, text):
        amount_match = re.search(r"(\d{2,7})", text.replace(",", ""))
        name_match = re.search(r"from\s+([A-Za-z .]+)", text, re.IGNORECASE)
        if not amount_match or not name_match:
            self.memory.session_context["pending"] = {"agent": "donor", "text": text}
            return self.say(
                "I can log a donation if you tell me the amount and donor name, "
                "e.g. 'Record a donation of 2000 from Ravi Kumar'."
            )
        amount = float(amount_match.group(1))
        donor_name = name_match.group(1).strip()
        result = self.memory.add_or_update_donor(donor_name, amount=amount)
        thank_you = self._draft_thank_you(result["name"], amount, result["total_donated"])
        status = "new donor" if result["new"] else "existing donor"
        return self.say(
            f"Recorded \u20b9{amount:.0f} from {donor_name} ({status}). "
            f"Lifetime total: \u20b9{result['total_donated']:.0f}.\n"
            f"  Auto-drafted thank-you message:\n  \"{thank_you}\""
        )

    def _draft_thank_you(self, name, amount, total):
        # LLM UPGRADE POINT: replace this template with a generated message
        return (
            f"Dear {name}, thank you for your generous contribution of \u20b9{amount:.0f} "
            f"to NayePankh Foundation. Your continued support (\u20b9{total:.0f} lifetime) "
            f"helps us reach more communities. With gratitude, Team NayePankh."
        )

    def list_donors(self):
        donors = self.memory.list_donors()
        if not donors:
            return self.say("No donors recorded yet.")
        lines = [f"  - {d['name']}: \u20b9{d['total_donated']:.0f} (last: {d['last_donation_date']})" for d in donors]
        return self.say("Current donor records:\n" + "\n".join(lines))


class VolunteerAgent(BaseAgent):
    name = "VolunteerAgent"

    def handle(self, text):
        name_match = re.search(r"name is\s+([A-Za-z .]+?)(?:,|\.|$)", text, re.IGNORECASE)
        skills_match = re.search(r"skills?\s*(?:is|are|:)\s*([A-Za-z, ]+)", text, re.IGNORECASE)
        if not name_match:
            self.memory.session_context["pending"] = {"agent": "volunteer", "text": text}
            return self.say(
                "To register you as a volunteer, tell me your name (and optionally skills), "
                "e.g. 'I want to volunteer, my name is Priya Singh, skills are teaching'."
            )
        name = name_match.group(1).strip()
        skills = skills_match.group(1).strip() if skills_match else None
        result = self.memory.add_or_update_volunteer(name, skills=skills, available=1)
        status = "Welcome aboard" if result["new"] else "Welcome back"
        return self.say(f"{status}, {name}! You're registered as an available volunteer" + (f" with skills: {skills}." if skills else "."))

    def find_match_for_skill(self, skill_keyword):
        vols = self.memory.list_volunteers(only_available=True)
        matches = [v for v in vols if v["skills"] and skill_keyword.lower() in v["skills"].lower()]
        return matches

    def list_volunteers(self):
        vols = self.memory.list_volunteers()
        if not vols:
            return self.say("No volunteers registered yet.")
        lines = [f"  - {v['name']} (skills: {v['skills'] or 'n/a'}, available: {'yes' if v['available'] else 'no'})" for v in vols]
        return self.say("Current volunteers:\n" + "\n".join(lines))


class TaskAgent(BaseAgent):
    name = "TaskAgent"

    def handle(self, text):
        desc_match = re.search(r"(?:task|remind(?:er)?)\s*(?:to|:)?\s*(.+)", text, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else text.strip()
        task_id = self.memory.add_task(description, created_by_agent="User-requested")
        return self.say(f"Task #{task_id} created: '{description}'.")

    def auto_create(self, description, assigned_to=None, due_date=None, created_by_agent="System"):
        """Called by other agents to automate follow-up tasks (agent-to-agent automation)."""
        task_id = self.memory.add_task(description, assigned_to=assigned_to, due_date=due_date, created_by_agent=created_by_agent)
        self.say(f"(auto) Task #{task_id} created by {created_by_agent}: '{description}'" + (f" (due {due_date})" if due_date else ""))
        return task_id

    def list_tasks(self):
        tasks = self.memory.list_tasks(status="open")
        if not tasks:
            return self.say("No open tasks. Nice and clear!")
        lines = [f"  - #{t['id']} {t['description']} (created by {t['created_by_agent']}, due {t['due_date'] or 'n/a'})" for t in tasks]
        return self.say("Open tasks:\n" + "\n".join(lines))


class EventAgent(BaseAgent):
    name = "EventAgent"

    def __init__(self, memory, task_agent: TaskAgent):
        super().__init__(memory)
        self.task_agent = task_agent  # demonstrates agent-to-agent collaboration

    def handle(self, text):
        date_str = parse_flexible_date(text)
        name_match = re.search(r"event(?:\s+called)?\s+\"?([A-Za-z0-9 ]+?)\"?\s+on", text, re.IGNORECASE)
        if not date_str:
            self.memory.session_context["pending"] = {"agent": "event", "text": text}
            return self.say(
                "Tell me the date to plan an event -- formats like 2026-07-01, "
                "01-07-2026, or 26-06-26 all work."
            )
        event_name = name_match.group(1).strip() if name_match else "Community Outreach Event"

        # --- real API #1: weather ---
        weather = get_weather_forecast(FOUNDATION_LOCATION["lat"], FOUNDATION_LOCATION["lon"], date_str)
        # --- real API #2: public holiday check ---
        holiday = is_public_holiday(date_str, FOUNDATION_LOCATION["country_code"])

        notes = []
        if weather["ok"]:
            notes.append(f"Weather forecast for {FOUNDATION_LOCATION['city']}: {weather['summary']}.")
            if weather["precipitation_mm"] and weather["precipitation_mm"] > 5:
                notes.append("Heavy rain expected -- consider an indoor backup venue.")
        else:
            notes.append(f"Weather check unavailable: {weather['error']}")

        if holiday:
            notes.append(f"Note: {date_str} is a public holiday ({holiday}) -- volunteer turnout may be affected either way.")
        else:
            notes.append(f"{date_str} is not a listed public holiday.")

        feasibility_note = " ".join(notes)
        event_id = self.memory.add_event(event_name, date_str, FOUNDATION_LOCATION["city"], feasibility_note)

        # --- automation: EventAgent automatically asks TaskAgent to create a prep reminder ---
        self.task_agent.auto_create(
            description=f"Confirm logistics & volunteer headcount for '{event_name}'",
            due_date=date_str,
            created_by_agent=self.name,
        )

        return self.say(f"Event #{event_id} '{event_name}' on {date_str} planned.\n  {feasibility_note}")

    def list_events(self):
        events = self.memory.list_events()
        if not events:
            return self.say("No events planned yet.")
        lines = [f"  - {e['name']} on {e['date']} @ {e['location']}: {e['feasibility_note']}" for e in events]
        return self.say("Planned events:\n" + "\n".join(lines))


class FAQAgent(BaseAgent):
    name = "FAQAgent"

    def handle(self, text):
        # LLM UPGRADE POINT: replace fuzzy matching with a real generated answer
        questions = [f["question"] for f in FAQ_KNOWLEDGE_BASE]
        best = difflib.get_close_matches(text, questions, n=1, cutoff=0.55)
        if best:
            for f in FAQ_KNOWLEDGE_BASE:
                if f["question"] == best[0]:
                    return self.say(f["answer"])
        # No good match: log it instead of silently dropping it, so Foundation
        # staff can review real questions people asked and grow the FAQ over
        # time (see memory.list_unanswered_questions()).
        self.memory.log_unanswered_question(text)
        return self.say(
            "I don't have a canned answer for that yet, but I've logged your question "
            "so the team can follow up and grow the FAQ. Meanwhile, try asking about "
            "volunteering, donating, planning events, or what this assistant can do."
        )


class CoordinatorAgent(BaseAgent):
    """Routes each message to the right specialist agent using keyword scoring,
    and can produce a cross-agent daily summary (an automated report)."""

    name = "Coordinator"

    # Checked top-to-bottom as a priority cascade (not a pure keyword-count
    # vote) so that an action verb like "remind" always wins task-routing
    # even if the sentence also mentions "donation" as its subject, e.g.
    # "Remind the team to print donation receipts" -> TaskAgent, not DonorAgent.
    INTENT_CASCADE = [
        ("task", ["remind", "reminder", "task", "todo", "to-do"]),
        ("volunteer", ["volunteer"]),
        ("event", ["plan an event", "plan a", "outdoor event", "organi", " event "]),
        ("report", ["summary", "report", "status overview", "daily overview"]),
        ("donor", ["donate", "donation", "donor", "contribut"]),
    ]

    def __init__(self, memory):
        super().__init__(memory)
        self.task_agent = TaskAgent(memory)
        self.donor_agent = DonorAgent(memory)
        self.volunteer_agent = VolunteerAgent(memory)
        self.event_agent = EventAgent(memory, self.task_agent)
        self.faq_agent = FAQAgent(memory)
        self._agent_registry = {
            "donor": self.donor_agent,
            "volunteer": self.volunteer_agent,
            "event": self.event_agent,
            "task": self.task_agent,
            "faq": self.faq_agent,
        }

    def _looks_like_question(self, text):
        t = text.strip().lower()
        first_word = t.split()[0] if t.split() else ""
        question_starters = {
            "do", "does", "did", "can", "could", "is", "are", "was", "were",
            "should", "would", "will", "what", "how", "why", "who", "which",
        }
        return t.endswith("?") or first_word in question_starters

    def _classify(self, text):
        text_l = f" {text.lower()} "
        is_question = self._looks_like_question(text)
        for intent, keywords in self.INTENT_CASCADE:
            # "donor" and "report" keywords (e.g. "donation", "status") are
            # topic words that show up in genuine questions too -- e.g. "Do
            # you offer tax exemption for donations above 50000?" should hit
            # the FAQ agent, not be misread as a command to record a
            # donation. Action-oriented intents (task/volunteer/event) are
            # rarely phrased as questions in this domain, so they're left
            # unaffected.
            if is_question and intent in ("donor", "report"):
                continue
            if any(kw in text_l for kw in keywords):
                return intent
        return "faq"  # default: try to answer it as a question

    def route(self, user_text):
        self.memory.log_conversation(role="user", agent="User", message=user_text)

        # --- multi-turn follow-up handling ---
        # If the previous turn was an agent asking for missing info (e.g. "what
        # date?"), don't re-classify this reply from scratch -- that's what
        # caused short replies like "26-06-26" to fall through to the FAQ
        # agent. Instead, merge it with the original request and retry the
        # SAME agent -- but only if this new message doesn't itself look like
        # a distinct, fresh command (e.g. "Give me a summary report" arriving
        # while a donor follow-up was pending). That guard prevents a stale
        # pending state from swallowing an unrelated request.
        pending = self.memory.session_context.get("pending")
        if pending:
            fresh_intent = self._classify(user_text)
            if fresh_intent in ("faq", pending["agent"]):
                agent = self._agent_registry.get(pending["agent"])
                combined_text = f"{pending['text']} {user_text}".strip()
                self.memory.session_context["pending"] = None
                if agent:
                    return agent.handle(combined_text)
            else:
                self.memory.session_context["pending"] = None  # stale -- drop it, route fresh below

        intent = self._classify(user_text)

        if intent == "donor":
            return self.donor_agent.handle(user_text)
        elif intent == "volunteer":
            return self.volunteer_agent.handle(user_text)
        elif intent == "event":
            return self.event_agent.handle(user_text)
        elif intent == "task":
            return self.task_agent.handle(user_text)
        elif intent == "report":
            return self.daily_summary()
        else:
            return self.faq_agent.handle(user_text)

    def daily_summary(self):
        """Automated cross-agent report -- pulls from every agent's memory."""
        donors = self.memory.list_donors()
        volunteers = self.memory.list_volunteers()
        tasks = self.memory.list_tasks(status="open")
        events = self.memory.list_events()
        unanswered = self.memory.list_unanswered_questions()
        lines = [
            "=== NayePankh Foundation -- Automated Daily Summary ===",
            f"Donors on file: {len(donors)} (total raised: \u20b9{sum(d['total_donated'] for d in donors):.0f})",
            f"Registered volunteers: {len(volunteers)} ({sum(v['available'] for v in volunteers)} currently available)",
            f"Open tasks: {len(tasks)}",
            f"Planned events: {len(events)}",
            f"Unanswered questions awaiting review: {len(unanswered)}",
        ]
        return self.say("\n".join(lines))
