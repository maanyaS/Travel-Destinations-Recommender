"""Terminal backend for the Travel Destination Recommender.

How it works:
- The user picks which travel features they value most (culture, adventure,
  nature, beaches, nightlife, cuisine, wellness, urban, seclusion) by typing
  the corresponding numbers separated by commas.
- Each selected feature is weighted equally. A destination's score is the
  sum of its ratings for those features.
- CRUD operations (GET / POST / PUT / DELETE) are demonstrated through the
  REST API running in app.py. Start that server first with: python app.py
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

# The nine feature columns available in the database
FEATURES: list[str] = [
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


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_destination(destination: Destination, selected_features: list[str]) -> float:
    """Sum the destination's ratings for every feature the user selected."""
    total = 0.0
    for feature in selected_features:
        total += getattr(destination, feature, 0)
    return total


# ---------------------------------------------------------------------------
# User prompts
# ---------------------------------------------------------------------------

def banner() -> None:
    print("\n" + "=" * 72)
    print("   TRAVEL DESTINATION RECOMMENDER")
    print("=" * 72)


def menu() -> None:
    print(
        "\nChoose an option:\n"
        "  1. Get destination recommendations\n"
        "  2. Look up a destination by city (GET)\n"
        "  3. Add a destination             (POST)\n"
        "  4. Update a destination          (PUT)\n"
        "  5. Delete a destination          (DELETE)\n"
        "  6. Exit\n"
    )


def prompt_for_features() -> list[str]:
    """Ask the user which features they value and return the selected list."""
    print("\nWhich travel features matter most to you?")
    print("Enter the numbers of the features you value, separated by commas.\n")
    for i, feature in enumerate(FEATURES, start=1):
        print(f"  {i}. {feature.capitalize()}")

    while True:
        raw = input("\nYour choices (e.g. 1,3,5): ").strip()
        choices = [part.strip() for part in raw.split(",") if part.strip()]
        try:
            selected: list[str] = []
            for choice in choices:
                idx = int(choice)
                if idx < 1 or idx > len(FEATURES):
                    raise ValueError(f"Number {idx} is out of range.")
                feature = FEATURES[idx - 1]
                if feature not in selected:  # deduplicate
                    selected.append(feature)
            if not selected:
                raise ValueError("You must choose at least one feature.")
            return selected
        except ValueError as err:
            print(f"Invalid input ({err}). Please enter numbers like 1,3,5.")


# ---------------------------------------------------------------------------
# Recommendation flow
# ---------------------------------------------------------------------------

def recommend_destinations() -> None:
    try:
        destinations = fetch_destinations_for_scoring()
    except Exception as exc:
        print(f"\nCould not load destination data from the database: {exc}")
        return

    selected_features = prompt_for_features()

    # Score and rank every destination
    ranked: list[tuple[float, Destination]] = []
    for dest in destinations:
        score = score_destination(dest, selected_features)
        ranked.append((score, dest))

    ranked.sort(key=lambda item: item[0], reverse=True)
    top = ranked[:TOP_RESULTS]

    # Display results
    print("\n" + "-" * 72)
    print("  YOUR TOP DESTINATION MATCHES")
    print("-" * 72)
    print(f"  Features you value: {', '.join(f.capitalize() for f in selected_features)}\n")

    for rank, (score, dest) in enumerate(top, start=1):
        avg_temp = dest.annual_average_temp()
        ratings = "  |  ".join(
            f"{f.capitalize()}: {getattr(dest, f)}"
            for f in selected_features
        )
        print(f"{rank}. {dest.city}, {dest.country}  |  Total Score: {int(score)}")
        print(f"   Region : {dest.region or 'Unknown'}")
        print(f"   Budget : {dest.budget_level or 'Unknown'}")
        print(f"   Avg yearly temp : {avg_temp if avg_temp is not None else 'Unknown'} °C")
        print(f"   Ideal trip lengths: {dest.durations_text()}")
        print(f"   Ratings — {ratings}")
        if dest.short_description:
            wrapped = textwrap.fill(dest.short_description, width=65)
            print("   Description:")
            for line in wrapped.splitlines():
                print(f"     {line}")
        print()


# ---------------------------------------------------------------------------
# API (CRUD) operations
# ---------------------------------------------------------------------------

def api_get_destinations() -> None:
    print("\n[ GET ] Look up a destination by city name")
    city_name = input("  Enter city name: ").strip()

    try:
        response = requests.get(f"{API_BASE_URL}/destinations", timeout=10)
        response.raise_for_status()
        destinations = response.json()
    except requests.RequestException as exc:
        print(f"  GET request failed: {exc}")
        return

    # Filter results by city name (case-insensitive)
    matches = [d for d in destinations if d.get('city', '').lower() == city_name.lower()]

    if not matches:
        print(f"\n  No destination found with the city name '{city_name}'.")
        return

    print(f"\n  Results for '{city_name}':\n")
    for dest in matches:
        print(f"  City        : {dest.get('city')}")
        print(f"  Country     : {dest.get('country')}")
        print(f"  Region      : {dest.get('region') or 'Unknown'}")
        print(f"  Budget      : {dest.get('budget_level') or 'Unknown'}")
        print(f"  Culture     : {dest.get('culture')}")
        print(f"  Adventure   : {dest.get('adventure')}")
        print(f"  Nature      : {dest.get('nature')}")
        print(f"  Beaches     : {dest.get('beaches')}")
        print(f"  Nightlife   : {dest.get('nightlife')}")
        print(f"  Cuisine     : {dest.get('cuisine')}")
        print(f"  Wellness    : {dest.get('wellness')}")
        print(f"  Urban       : {dest.get('urban')}")
        print(f"  Seclusion   : {dest.get('seclusion')}")
        print()


def api_add_destination() -> None:
    print("\n[ POST ] Add a new destination via the API")
    dest_id = input("  Unique ID (e.g. a UUID or short code): ").strip()
    city    = input("  City name                            : ").strip()
    country = input("  Country                              : ").strip()
    region  = input("  Region (optional)                    : ").strip() or None
    budget  = input("  Budget level (Budget/Mid-range/Luxury): ").strip() or None

    print("\n  Rate each feature from 1 (low) to 5 (high).")
    ratings: dict[str, str] = {}
    for feature in FEATURES:
        while True:
            val = input(f"    {feature.capitalize()} [1-5]: ").strip()
            if val in {"1", "2", "3", "4", "5"}:
                ratings[feature] = val
                break
            print("    Please enter a number between 1 and 5.")

    payload = {
        "id": dest_id,
        "city": city,
        "country": country,
        "region": region,
        "budget_level": budget,
        **ratings,
    }

    try:
        response = requests.post(f"{API_BASE_URL}/destinations", json=payload, timeout=10)
        response.raise_for_status()
        print(f"\n  Success: {response.json().get('message')}")
    except requests.RequestException as exc:
        print(f"\n  POST request failed: {exc}")


def api_update_destination() -> None:
    print("\n[ PUT ] Update a destination via the API")
    dest_id = input("  Destination ID to update: ").strip()

    print(f"  What would you like to update? (Leave blank to skip)")
    payload: dict = {}
    city = input("  New city name       : ").strip()
    if city:
        payload["city"] = city
    budget = input("  New budget level    : ").strip()
    if budget:
        payload["budget_level"] = budget

    print("  Update feature ratings? Enter new value 1-5 or press Enter to skip.")
    for feature in FEATURES:
        val = input(f"    {feature.capitalize()} [1-5 or blank]: ").strip()
        if val in {"1", "2", "3", "4", "5"}:
            payload[feature] = val

    if not payload:
        print("  Nothing to update.")
        return

    try:
        response = requests.put(
            f"{API_BASE_URL}/destinations/{dest_id}",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        print(f"\n  Success: {response.json().get('message')}")
    except requests.RequestException as exc:
        print(f"\n  PUT request failed: {exc}")


def api_delete_destination() -> None:
    print("\n[ DELETE ] Remove a destination via the API")
    city_name = input("  Enter city name to delete: ").strip()

    # First fetch all destinations and find matches
    try:
        response = requests.get(f"{API_BASE_URL}/destinations", timeout=10)
        response.raise_for_status()
        destinations = response.json()
    except requests.RequestException as exc:
        print(f"  GET request failed: {exc}")
        return

    matches = [d for d in destinations if d.get('city', '').lower() == city_name.lower()]

    if not matches:
        print(f"\n  No destination found with the city name '{city_name}'.")
        return

    # Show matches and let user pick if there are multiple
    if len(matches) == 1:
        dest = matches[0]
    else:
        print(f"\n  Multiple destinations found with the name '{city_name}':")
        for i, d in enumerate(matches, start=1):
            print(f"  {i}. {d.get('city')}, {d.get('country')} — {d.get('region')} — {d.get('budget_level')}")
        while True:
            choice = input("\n  Which one do you want to delete? Enter number: ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(matches):
                    dest = matches[idx]
                    break
                else:
                    print("  Invalid number, try again.")
            except ValueError:
                print("  Please enter a valid number.")

    # Confirm before deleting
    print(f"\n  You are about to delete: {dest.get('city')}, {dest.get('country')} ({dest.get('region')})")
    confirm = input("  Type DELETE to confirm: ").strip()
    if confirm != "DELETE":
        print("  Delete cancelled.")
        return

    try:
        response = requests.delete(
            f"{API_BASE_URL}/destinations/{dest.get('id')}",
            timeout=10,
        )
        response.raise_for_status()
        print(f"\n  Success: {response.json().get('message')}")
    except requests.RequestException as exc:
        print(f"\n  DELETE request failed: {exc}")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    banner()
    print(
        "Note: Options 2-5 require the Flask API to be running.\n"
        "      In a separate terminal, run: python app.py\n"
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
            print("\nGoodbye! Safe travels!\n")
            break
        else:
            print("Invalid option. Please enter a number from 1 to 6.")


if __name__ == "__main__":
    main()
