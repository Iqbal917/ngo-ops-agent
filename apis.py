"""
apis.py
-------
Connects the agent system to real, free, no-API-key-required public APIs.

1. Open-Meteo (https://open-meteo.com) - weather forecast, no key needed.
2. Nager.Date (https://date.nager.at) - public holidays by country/year, no key needed.

Both calls are wrapped in try/except with short timeouts so that the rest of
the system keeps working even if the machine running this script has no
internet access (e.g. a locked-down lab computer) -- the agent will just say
it couldn't reach the service instead of crashing.

If you DO have an LLM API key (OpenAI/Anthropic/etc.) you can drop a call to
it right here, e.g. inside FAQAgent in agents.py, to replace the rule-based
matching with real generated answers. See the README for a ready-made snippet.
"""

import requests

TIMEOUT = 6


def get_weather_forecast(lat, lon, date_str):
    """
    Returns a dict like {"ok": True, "max_temp": 33.2, "min_temp": 24.1,
    "precipitation_mm": 0.0, "summary": "..."} or {"ok": False, "error": "..."}.
    date_str must be 'YYYY-MM-DD' and within Open-Meteo's forecast window.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto",
        "start_date": date_str,
        "end_date": date_str,
    }
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})
        if not daily.get("time"):
            return {"ok": False, "error": "No forecast available for that date (too far out or in the past)."}
        max_t = daily["temperature_2m_max"][0]
        min_t = daily["temperature_2m_min"][0]
        precip = daily["precipitation_sum"][0]
        summary = f"{min_t}-{max_t}\u00b0C, {precip}mm precipitation expected"
        return {"ok": True, "max_temp": max_t, "min_temp": min_t, "precipitation_mm": precip, "summary": summary}
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": f"Could not reach weather service ({e.__class__.__name__})."}


def get_public_holidays(year, country_code="IN"):
    """
    Returns a list of dicts [{"date": "2026-01-26", "localName": "Republic Day"}, ...]
    or an empty list (with no crash) if the API can't be reached.
    """
    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException:
        return []


def is_public_holiday(date_str, country_code="IN"):
    """Convenience helper: checks a single 'YYYY-MM-DD' date against the holiday list."""
    year = date_str.split("-")[0]
    holidays = get_public_holidays(year, country_code)
    for h in holidays:
        if h.get("date") == date_str:
            return h.get("localName", "Public Holiday")
    return None
