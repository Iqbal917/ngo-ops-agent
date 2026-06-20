"""
data.py
-------
Seed/sample data for the Nayapankh Foundation AI Agent prototype.

In a real deployment, this would be replaced by data pulled from the
Foundation's actual CRM / spreadsheet / database. For this prototype,
everything here is sample data so the system is runnable out-of-the-box.
"""

# Default location used for event weather checks (New Delhi as a placeholder
# since most NGO ops in India are concentrated around NCR; change freely).
FOUNDATION_LOCATION = {
    "city": "New Delhi",
    "lat": 28.6139,
    "lon": 77.2090,
    "country_code": "IN",
}

SEED_DONORS = [
    {"name": "Ravi Kumar", "contact": "ravi.k@example.com", "total_donated": 5000},
    {"name": "Anita Sharma", "contact": "anita.sharma@example.com", "total_donated": 12000},
    {"name": "Mehta Family Trust", "contact": "contact@mehtatrust.org", "total_donated": 50000},
]

SEED_VOLUNTEERS = [
    {"name": "Priya Singh", "contact": "priya.s@example.com", "skills": "teaching, first-aid", "available": 1},
    {"name": "Arjun Verma", "contact": "arjun.v@example.com", "skills": "logistics, driving", "available": 1},
    {"name": "Fatima Khan", "contact": "fatima.k@example.com", "skills": "fundraising, social media", "available": 0},
]

# Simple local knowledge base for the FAQ agent. Each entry has a set of
# trigger phrases and a canned but editable answer. Retrieval is done with
# fuzzy text matching (see agents.FAQAgent), so users don't need to type the
# question exactly.
FAQ_KNOWLEDGE_BASE = [
    {
        "question": "What does Nayapankh Foundation do",
        "answer": (
            "Nayapankh Foundation works on community welfare programs including "
            "education support, volunteer-driven outreach, and donation-funded "
            "relief activities. (Edit this answer in data.py with the real mission "
            "statement.)"
        ),
    },
    {
        "question": "How can I volunteer",
        "answer": (
            "You can volunteer by sharing your name, contact, and skills with the "
            "Volunteer Agent (try: 'I want to volunteer, my name is ..., skills are ...')."
        ),
    },
    {
        "question": "How can I donate",
        "answer": (
            "You can register a donation through the Donor Agent (try: 'Record a "
            "donation of 2000 from Ravi Kumar'). In production this would connect "
            "to a real payment gateway API."
        ),
    },
    {
        "question": "How do I check if an event can happen outdoors",
        "answer": (
            "Ask the Event Agent, e.g. 'Plan an outdoor event on 2026-07-01' and it "
            "will check the weather forecast and public holidays for that date."
        ),
    },
    {
        "question": "What can this assistant do",
        "answer": (
            "I can manage donor records, coordinate volunteers, plan events "
            "(checking live weather and holidays), create and track tasks, and "
            "answer common questions -- all while remembering context across our "
            "conversation and across sessions."
        ),
    },
]
