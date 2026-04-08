"""Terminal backend client for the travel recommendation project.

How it works:
- Uses the existing Flask app in app.py for database configuration.
- Reads destination data directly from the same MySQL database using the SQLAlchemy
  session/engine already configured in app.py.
- Uses the REST API in app.py for CRUD operations (GET/POST/PUT/DELETE) so you can
  still demonstrate the required HTTP methods.

Why both DB + API are used here:
- The current /destinations API only returns id, city, and country.
- Mood-based recommendations need more columns such as culture, adventure,
  beaches, nightlife, wellness, seclusion, etc.
- So this terminal program reads the richer destination data from the DB for
  scoring, and uses the API routes for CRUD operations.
"""

from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass
from typing import Any

import requests
from sqlalchemy import text

from app import app, db

API_BASE_URL = "http://127.0.0.1:5000"
TOP_RESULTS = 5

# Moods map to one or more columns in the Kaggle-based travel_data table.
MOOD_WEIGHTS: dict[str, dict[str, float]] = {
    "relaxed": {"wellness": 0.45, "seclusion": 0.35, "beaches": 0.20},
    "adventurous": {"adventure": 0.55, "nature": 0.30, "urban": 0.15},
    "romantic": {"beaches": 0.25, "wellness": 0.25, "cuisine": 0.20, "seclusion": 0.30},
    "energetic": {"nightlife": 0.45, "urban": 0.35, "adventure": 0.20},
    "curious": {"culture": 0.50, "cuisine": 0.30, "urban": 0.20},
    "nature_lover": {"nature": 0.60, "seclusion": 0.25, "adventure": 0.15},
    "beachy": {"beaches": 0.70, "wellness": 0.15, "seclusion": 0.15},
    "social": {"nightlife": 0.45, "urban": 0.35, "cuisine": 0.20},
}

BUDGET_PREFERENCE = {
    "1": None,
    "2": "Budget",
    "3": "Mid-range",
    "4": "Luxury",
}

CLIMATE_PREFERENCE = {
    "1": None,
    "2": "cold",
    "3": "mild",
    "4": "warm",
}

RATING_COLUMNS = [
    "culture",
    "adventure",
    "nature",
    "beaches",
    "nightlife",
    "cuisine",
    "wellness",
    "urban",
    "seclusion",
]


@dataclass
class Destination:
    id: str
    city: str
    country: str
    region: str | None
    short_description: str | None
    budget_level: str | None
    avg_temp_monthly: str | None
    ideal_durations: str | None
    culture: int
    adventure: int
    nature: int
    beaches: int
    nightlife: int
    cuisine: int
    wellness: int
    urban: int
    seclusion: int

    def annual_average_temp(self) -> float | None:
        if not self.avg_temp_monthly:
            return None
        try:
            monthly = json.loads(self.avg_temp_monthly)
            avgs = [float(v["avg"]) for v in monthly.values() if isinstance(v, dict) and "avg" in v]
            return round(sum(avgs) / len(avgs), 1) if avgs else None
        except (json.JSONDecodeError, TypeError, ValueError, KeyError):
            return None

    def durations_text(self) -> str:
        if not self.ideal_durations:
            return "Unknown"
        try:
            values = json.loads(self.ideal_durations)
            if isinstance(values, list):
                return ", ".join(values)
        except json.JSONDecodeError:
            pass
        return str(self.ideal_durations)


def banner() -> None:
    print("\n" + "=" * 72)
    print("TRAVEL MOOD RECOMMENDER - TERMINAL BACKEND")
    print("=" * 72)


def menu() -> None:
    print(
        "\nChoose an option:\n"
        "1. Get destination recommendations\n"
        "2. View all destinations (GET)\n"
        "3. Add a destination (POST)\n"
        "4. Update a destination city name (PUT)\n"
        "5. Delete a destination (DELETE)\n"
        "6. Exit\n"
    )


def fetch_destinations_for_scoring() -> list[Destination]:
    query = text(
        """
        SELECT id, city, country, region, short_description, budget_level,
               avg_temp_monthly, ideal_durations,
               culture, adventure, nature, beaches, nightlife,
               cuisine, wellness, urban, seclusion
        FROM travel_data
        """
    )

    with app.app_context():
        rows = db.session.execute(query).mappings().all()

    destinations: list[Destination] = []
    for row in rows:
        destinations.append(
            Destination(
                id=str(row.get("id", "")),
                city=str(row.get("city", "Unknown")),
                country=str(row.get("country", "Unknown")),
                region=row.get("region"),
                short_description=row.get("short_description"),
                budget_level=row.get("budget_level"),
                avg_temp_monthly=row.get("avg_temp_monthly"),
                ideal_durations=row.get("ideal_durations"),
                culture=_safe_int(row.get("culture")),
                adventure=_safe_int(row.get("adventure")),
                nature=_safe_int(row.get("nature")),
                beaches=_safe_int(row.get("beaches")),
                nightlife=_safe_int(row.get("nightlife")),
                cuisine=_safe_int(row.get("cuisine")),
                wellness=_safe_int(row.get("wellness")),
                urban=_safe_int(row.get("urban")),
                seclusion=_safe_int(row.get("seclusion")),
            )
        )
    return destinations


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def prompt_for_moods() -> list[str]:
    print("\nHow are you feeling right now? Pick one or more moods.")
    keys = list(MOOD_WEIGHTS.keys())
    for index, mood in enumerate(keys, start=1):
        print(f"{index}. {mood.replace('_', ' ').title()}")

    while True:
        raw = input("Enter mood numbers separated by commas (example: 1,3,5): ").strip()
        choices = [part.strip() for part in raw.split(",") if part.strip()]
        try:
            selected = []
            for choice in choices:
                idx = int(choice)
                if idx < 1 or idx > len(keys):
                    raise ValueError
                selected.append(keys[idx - 1])
            if not selected:
                raise ValueError
            return list(dict.fromkeys(selected))
        except ValueError:
            print("Invalid input. Please enter valid mood numbers like 1,3,5.")


def prompt_for_budget() -> str | None:
    print("\nAny budget preference?")
    print("1. No preference")
    print("2. Budget")
    print("3. Mid-range")
    print("4. Luxury")
    while True:
        choice = input("Choose 1-4: ").strip()
        if choice in BUDGET_PREFERENCE:
            return BUDGET_PREFERENCE[choice]
        print("Invalid choice. Please enter 1, 2, 3, or 4.")


def prompt_for_climate() -> str | None:
    print("\nAny climate preference?")
    print("1. No preference")
    print("2. Cold")
    print("3. Mild")
    print("4. Warm")
    while True:
        choice = input("Choose 1-4: ").strip()
        if choice in CLIMATE_PREFERENCE:
            return CLIMATE_PREFERENCE[choice]
        print("Invalid choice. Please enter 1, 2, 3, or 4.")


def classify_climate(avg_temp: float | None) -> str | None:
    if avg_temp is None:
        return None
    if avg_temp < 10:
        return "cold"
    if avg_temp < 20:
        return "mild"
    return "warm"


def score_destination(destination: Destination, moods: list[str], budget_pref: str | None, climate_pref: str | None) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    for mood in moods:
        weights = MOOD_WEIGHTS.get(mood, {})
        mood_total = 0.0
        for column, weight in weights.items():
            value = getattr(destination, column, 0)
            mood_total += value * weight
        score += mood_total
        reasons.append(f"{mood.replace('_', ' ')} match")

    if budget_pref and destination.budget_level == budget_pref:
        score += 1.5
        reasons.append(f"matches {budget_pref.lower()} budget")

    avg_temp = destination.annual_average_temp()
    climate_label = classify_climate(avg_temp)
    if climate_pref and climate_label == climate_pref:
        score += 1.0
        reasons.append(f"fits {climate_pref} climate")

    return round(score, 2), reasons


def recommend_destinations() -> None:
    try:
        destinations = fetch_destinations_for_scoring()
    except Exception as exc:
        print(f"Could not load destination data from the database: {exc}")
        return

    moods = prompt_for_moods()
    budget_pref = prompt_for_budget()
    climate_pref = prompt_for_climate()

    ranked: list[tuple[float, list[str], Destination]] = []
    for destination in destinations:
        score, reasons = score_destination(destination, moods, budget_pref, climate_pref)
        ranked.append((score, reasons, destination))

    ranked.sort(key=lambda item: item[0], reverse=True)
    top = ranked[:TOP_RESULTS]

    print("\n" + "-" * 72)
    print("YOUR TOP DESTINATION MATCHES")
    print("-" * 72)
    print(f"Selected moods: {', '.join(m.replace('_', ' ') for m in moods)}")
    print(f"Budget preference: {budget_pref or 'No preference'}")
    print(f"Climate preference: {climate_pref or 'No preference'}\n")

    for index, (score, reasons, destination) in enumerate(top, start=1):
        avg_temp = destination.annual_average_temp()
        print(f"{index}. {destination.city}, {destination.country}  |  Score: {score}")
        print(f"   Region: {destination.region or 'Unknown'}")
        print(f"   Budget: {destination.budget_level or 'Unknown'}")
        print(f"   Avg yearly temp: {avg_temp if avg_temp is not None else 'Unknown'}")
        print(f"   Ideal durations: {destination.durations_text()}")
        print(f"   Why it matched: {', '.join(reasons[:3])}")
        if destination.short_description:
            wrapped = textwrap.fill(destination.short_description, width=65)
            print("   Description:")
            for line in wrapped.splitlines():
                print(f"     {line}")
        print()


def api_get_destinations() -> None:
    try:
        response = requests.get(f"{API_BASE_URL}/destinations", timeout=10)
        response.raise_for_status()
        destinations = response.json()
    except requests.RequestException as exc:
        print(f"GET request failed: {exc}")
        return

    print("\nDESTINATIONS FROM API")
    print("-" * 72)
    for item in destinations[:25]:  # keep terminal output manageable
        print(f"{item.get('id')} | {item.get('city')}, {item.get('country')}")
    if len(destinations) > 25:
        print(f"... and {len(destinations) - 25} more")


def api_add_destination() -> None:
    print("\nAdd a new destination through the API")
    destination_id = input("ID (UUID or unique text): ").strip()
    city = input("City: ").strip()
    country = input("Country: ").strip()

    payload = {"id": destination_id, "city": city, "country": country}
    try:
        response = requests.post(f"{API_BASE_URL}/destinations", json=payload, timeout=10)
        response.raise_for_status()
        print(f"Success: {response.json()}")
    except requests.RequestException as exc:
        print(f"POST request failed: {exc}")


def api_update_destination() -> None:
    print("\nUpdate a destination city name through the API")
    destination_id = input("Destination ID to update: ").strip()
    city = input("New city name: ").strip()

    payload = {"city": city}
    try:
        response = requests.put(f"{API_BASE_URL}/destinations/{destination_id}", json=payload, timeout=10)
        response.raise_for_status()
        print(f"Success: {response.json()}")
    except requests.RequestException as exc:
        print(f"PUT request failed: {exc}")


def api_delete_destination() -> None:
    print("\nDelete a destination through the API")
    destination_id = input("Destination ID to delete: ").strip()
    confirm = input(f"Type DELETE to confirm removal of {destination_id}: ").strip()
    if confirm != "DELETE":
        print("Delete cancelled.")
        return

    try:
        response = requests.delete(f"{API_BASE_URL}/destinations/{destination_id}", timeout=10)
        response.raise_for_status()
        print(f"Success: {response.json()}")
    except requests.RequestException as exc:
        print(f"DELETE request failed: {exc}")


def main() -> None:
    banner()
    print(
        "Before using options 2-5, make sure your Flask API from app.py is running\n"
        "in another terminal with: python app.py\n"
    )

    while True:
        menu()
        choice = input("Enter your choice (1-6): ").strip()

        if choice == "1":
            recommend_destinations()
        elif choice == "2":
            api_get_destinations()
        elif choice == "3":
            api_add_destination()
        elif choice == "4":
            api_update_destination()
        elif choice == "5":
            api_delete_destination()
        elif choice == "6":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please choose a number from 1 to 6.")


if __name__ == "__main__":
    main()
