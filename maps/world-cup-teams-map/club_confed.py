"""Map club host countries to FIFA confederations for dashboard aggregations."""

from __future__ import annotations

from viz import confed_key

# Normalise inconsistent country strings from clubs.json enrichment.
COUNTRY_ALIASES: dict[str, str] = {
    "UAE": "United Arab Emirates",
    "Czechia": "Czech Republic",
}

# Values that are not real countries (bad geocoding / wiki parse).
INVALID_COUNTRIES: frozenset[str] = frozenset(
    {
        "Unknown",
        "Gdańsk",
        "Schleswig-Holstein",
        "Toulouse",
        "the top division of French football",
        "Czechoslovakia",
    }
)

# FIFA member association -> confederation (club host country).
COUNTRY_CONFED: dict[str, str] = {
    # UEFA
    "Albania": "UEFA",
    "Armenia": "UEFA",
    "Austria": "UEFA",
    "Azerbaijan": "UEFA",
    "Belgium": "UEFA",
    "Bosnia and Herzegovina": "UEFA",
    "Bulgaria": "UEFA",
    "Croatia": "UEFA",
    "Cyprus": "UEFA",
    "Czech Republic": "UEFA",
    "Denmark": "UEFA",
    "England": "UEFA",
    "Finland": "UEFA",
    "France": "UEFA",
    "Germany": "UEFA",
    "Greece": "UEFA",
    "Hungary": "UEFA",
    "Ireland": "UEFA",
    "Israel": "UEFA",
    "Italy": "UEFA",
    "Monaco": "UEFA",
    "Netherlands": "UEFA",
    "Norway": "UEFA",
    "Poland": "UEFA",
    "Portugal": "UEFA",
    "Romania": "UEFA",
    "Russia": "UEFA",
    "Scotland": "UEFA",
    "Serbia": "UEFA",
    "Slovakia": "UEFA",
    "Slovenia": "UEFA",
    "Spain": "UEFA",
    "Sweden": "UEFA",
    "Switzerland": "UEFA",
    "Turkey": "UEFA",
    "Ukraine": "UEFA",
    "United Kingdom": "UEFA",
    "Wales": "UEFA",
    # CONMEBOL
    "Argentina": "CONMEBOL",
    "Brazil": "CONMEBOL",
    "Chile": "CONMEBOL",
    "Colombia": "CONMEBOL",
    "Ecuador": "CONMEBOL",
    "Paraguay": "CONMEBOL",
    "Uruguay": "CONMEBOL",
    "Venezuela": "CONMEBOL",
    # CONCACAF
    "Canada": "CONCACAF",
    "Costa Rica": "CONCACAF",
    "Haiti": "CONCACAF",
    "Honduras": "CONCACAF",
    "Mexico": "CONCACAF",
    "Panama": "CONCACAF",
    "United States": "CONCACAF",
    # CAF
    "Algeria": "CAF",
    "Egypt": "CAF",
    "Ghana": "CAF",
    "Morocco": "CAF",
    "South Africa": "CAF",
    "Tunisia": "CAF",
    # AFC
    "Australia": "AFC",
    "China": "AFC",
    "Indonesia": "AFC",
    "Iran": "AFC",
    "Iraq": "AFC",
    "Japan": "AFC",
    "Jordan": "AFC",
    "Kazakhstan": "AFC",
    "Malaysia": "AFC",
    "Qatar": "AFC",
    "Saudi Arabia": "AFC",
    "South Korea": "AFC",
    "United Arab Emirates": "AFC",
    "Uzbekistan": "AFC",
    # OFC
    "New Zealand": "OFC",
}

# Nations whose players may count as "domestic" at clubs in these countries.
NATION_HOME_COUNTRIES: dict[str, frozenset[str]] = {
    "Bosnia and Herzegovina": frozenset({"Bosnia and Herzegovina"}),
    "Czech Republic": frozenset({"Czech Republic", "Czechia"}),
    "DR Congo": frozenset({"DR Congo", "Democratic Republic of the Congo"}),
    "England": frozenset({"England", "United Kingdom"}),
    "Ivory Coast": frozenset({"Ivory Coast", "Côte d'Ivoire"}),
    "South Korea": frozenset({"South Korea", "Korea Republic"}),
    "United States": frozenset({"United States", "USA"}),
}


def normalize_country(country: str) -> str:
    if country in INVALID_COUNTRIES:
        return "Unknown"
    return COUNTRY_ALIASES.get(country, country)


def club_confederation(country: str) -> str:
    normalized = normalize_country(country)
    if normalized == "Unknown":
        return "OTHER"
    return COUNTRY_CONFED.get(normalized, "OTHER")


def nation_confederation(confederation: str) -> str:
    return confed_key(confederation)


def is_domestic(nation: str, club_country: str) -> bool:
    normalized = normalize_country(club_country)
    if normalized == "Unknown":
        return False
    home = NATION_HOME_COUNTRIES.get(nation, frozenset({nation}))
    return normalized in home
