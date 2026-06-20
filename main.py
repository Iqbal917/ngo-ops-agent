"""
main.py
-------
Entry point for the NayePankh Foundation AI Agent prototype.

Usage:
    python3 main.py            # runs a scripted demo (great for screenshots / report)
    python3 main.py --chat     # interactive mode, type your own messages
    python3 main.py --reset    # wipes the memory database and starts fresh

This single script ties together everything required by the internship brief:
  - Memory          -> memory.py (SQLite, persists across runs)
  - Connect APIs    -> apis.py (Open-Meteo weather + Nager.Date holidays, no key needed)
  - Multi-Agent     -> agents.py (Coordinator + 5 specialist agents)
  - Automate Tasks  -> EventAgent auto-creates follow-up tasks; DonorAgent
                       auto-drafts thank-you messages; CoordinatorAgent
                       auto-generates a cross-agent daily summary report.
"""

import argparse
import sys
from pathlib import Path

from memory import Memory, DB_PATH
from agents import CoordinatorAgent
from data import SEED_DONORS, SEED_VOLUNTEERS


def seed_if_empty(memory):
    """Load sample data on first run only, so repeated runs don't duplicate it."""
    if not memory.list_donors():
        for d in SEED_DONORS:
            memory.add_or_update_donor(d["name"], contact=d["contact"], amount=d["total_donated"])
    if not memory.list_volunteers():
        for v in SEED_VOLUNTEERS:
            memory.add_or_update_volunteer(v["name"], contact=v["contact"], skills=v["skills"], available=v["available"])


DEMO_SCRIPT = [
    "What can this assistant do?",
    "Record a donation of 2500 from Ravi Kumar",
    "I want to volunteer, my name is Karan Mehta, skills are teaching, logistics",
    "Plan an outdoor event on 2026-07-15",
    "Remind the team to print donation receipts",
    "Do you offer tax exemption certificates for donations above 50000?",
    "Give me a summary report",
]


def run_demo(memory):
    coordinator = CoordinatorAgent(memory)
    print("\n=========== NAYEPANKH FOUNDATION AI AGENT -- SCRIPTED DEMO ===========")
    print(f"(memory file: {DB_PATH})\n")
    for line in DEMO_SCRIPT:
        print(f"\nUser: {line}")
        coordinator.route(line)
    print("\n=========== END OF DEMO ===========")
    print("Run again with --chat to type your own messages, or inspect")
    print(f"{DB_PATH} with any SQLite browser to see what the agents remembered.\n")


def run_chat(memory):
    coordinator = CoordinatorAgent(memory)
    print("\n=========== NAYEPANKH FOUNDATION AI AGENT -- INTERACTIVE MODE ===========")
    print("Type a message (or 'history' to see recent conversation, 'quit' to exit).")
    print("Quick lookups: 'donors', 'volunteers', 'tasks', 'events', 'unanswered'")
    print("Try things like:")
    print("  - Record a donation of 3000 from Anita Sharma")
    print("  - I want to volunteer, my name is Dev Patel, skills are fundraising")
    print("  - Plan an outdoor event on 2026-08-01")
    print("  - Remind us to order event banners")
    print("  - Give me a summary report")
    print("  - How can I donate?\n")
    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not text:
            continue
        if text.lower() in ("quit", "exit"):
            print("Goodbye!")
            break
        if text.lower() == "history":
            for turn in memory.recent_history(10):
                print(f"  [{turn['role']}/{turn['agent']}] {turn['message'][:100]}")
            continue
        if text.lower() in ("list donors", "donors"):
            coordinator.donor_agent.list_donors()
            continue
        if text.lower() in ("list volunteers", "volunteers"):
            coordinator.volunteer_agent.list_volunteers()
            continue
        if text.lower() in ("list tasks", "tasks"):
            coordinator.task_agent.list_tasks()
            continue
        if text.lower() in ("list events", "events"):
            coordinator.event_agent.list_events()
            continue
        if text.lower() in ("list unanswered", "unanswered"):
            rows = memory.list_unanswered_questions()
            if not rows:
                print("[Coordinator] No unanswered questions logged -- FAQ coverage looks good!")
            else:
                print("[Coordinator] Unanswered questions awaiting review:")
                for r in rows:
                    print(f"  - #{r['id']} \"{r['question']}\" (asked {r['timestamp']})")
            continue
        coordinator.route(text)


def main():
    parser = argparse.ArgumentParser(description="NayePankh Foundation AI Agent prototype")
    parser.add_argument("--chat", action="store_true", help="interactive chat mode")
    parser.add_argument("--reset", action="store_true", help="wipe memory and start fresh")
    args = parser.parse_args()

    if args.reset and DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Memory reset: deleted {DB_PATH}")

    memory = Memory()
    seed_if_empty(memory)

    if args.chat:
        run_chat(memory)
    else:
        run_demo(memory)

    memory.close()


if __name__ == "__main__":
    main()
