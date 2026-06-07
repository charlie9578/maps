"""Merge curated club coordinates for common World Cup squad clubs.

Run after fetch_squads.py (and optionally enrich_clubs.py):
    python maps/world-cup-teams-map/seed_clubs.py
"""

from __future__ import annotations

import json
from pathlib import Path

from enrich_clubs import CLUB_ALIASES, apply_aliases_to_squads, canonical_club

MAP_DIR = Path(__file__).resolve().parent
CLUBS_JSON = MAP_DIR / "data" / "clubs.json"
SQUADS_JSON = MAP_DIR / "data" / "squads.json"

# stadium, city, country, lat, lon — city-level precision is fine for this map.
SUPPLEMENT: dict[str, dict] = {
    "Milan": {"stadium": "San Siro", "city": "Milan", "country": "Italy", "lat": 45.4781, "lon": 9.1240},
    "Bournemouth": {"stadium": "Vitality Stadium", "city": "Bournemouth", "country": "England", "lat": 50.7352, "lon": -1.8385},
    "Orlando Pirates": {"stadium": "Orlando Stadium", "city": "Johannesburg", "country": "South Africa", "lat": -26.2350, "lon": 27.9750},
    "Strasbourg": {"stadium": "Stade de la Meinau", "city": "Strasbourg", "country": "France", "lat": 48.5583, "lon": 7.7547},
    "Viktoria Plzen": {"stadium": "Doosan Arena", "city": "Plzen", "country": "Czechia", "lat": 49.7475, "lon": 13.3775},
    "Mainz 05": {"stadium": "Mewa Arena", "city": "Mainz", "country": "Germany", "lat": 50.0214, "lon": 8.2219},
    "Al Qadsiah": {"stadium": "Prince Saud bin Jalawi Stadium", "city": "Khobar", "country": "Saudi Arabia", "lat": 26.2172, "lon": 50.1972},
    "Al-Hussein": {"stadium": "Amman International Stadium", "city": "Amman", "country": "Jordan", "lat": 31.9928, "lon": 35.9242},
    "Norwich City": {"stadium": "Carrow Road", "city": "Norwich", "country": "England", "lat": 52.6220, "lon": 1.3090},
    "İstanbul Başakşehir": {"stadium": "Basaksehir Fatih Terim Stadium", "city": "Istanbul", "country": "Turkey", "lat": 41.0931, "lon": 28.8042},
    "Pyramids": {"stadium": "30 June Stadium", "city": "Cairo", "country": "Egypt", "lat": 30.0600, "lon": 31.2200},
    "Tractor": {"stadium": "Yadegar-e Emam Stadium", "city": "Tabriz", "country": "Iran", "lat": 38.0667, "lon": 46.3000},
    "Auckland FC": {"stadium": "Go Media Stadium", "city": "Auckland", "country": "New Zealand", "lat": -36.9170, "lon": 174.8090},
    "Sassuolo": {"stadium": "Mapei Stadium", "city": "Reggio Emilia", "country": "Italy", "lat": 44.7142, "lon": 10.6497},
    "FC Augsburg": {"stadium": "WWK Arena", "city": "Augsburg", "country": "Germany", "lat": 48.5914, "lon": 10.9381},
    "Freiburg": {"stadium": "Europa-Park Stadion", "city": "Freiburg", "country": "Germany", "lat": 48.0214, "lon": 7.8297},
    "Midtjylland": {"stadium": "MCH Arena", "city": "Herning", "country": "Denmark", "lat": 56.1331, "lon": 8.9336},
    "AEL Limassol": {"stadium": "Alphamega Stadium", "city": "Limassol", "country": "Cyprus", "lat": 34.7000, "lon": 33.0500},
    "Genk": {"stadium": "Cegeka Arena", "city": "Genk", "country": "Belgium", "lat": 50.9650, "lon": 5.5006},
    "Atletico Mineiro": {"stadium": "Arena MRV", "city": "Belo Horizonte", "country": "Brazil", "lat": -19.8658, "lon": -43.9711},
    "Auxerre": {"stadium": "Stade de l'Abbe-Deschamps", "city": "Auxerre", "country": "France", "lat": 47.8136, "lon": 3.5886},
    "Al-Zawraa": {"stadium": "Al-Shaab Stadium", "city": "Baghdad", "country": "Iraq", "lat": 33.3400, "lon": 44.4000},
    "Al-Shorta": {"stadium": "Al-Shaab Stadium", "city": "Baghdad", "country": "Iraq", "lat": 33.3400, "lon": 44.4000},
    "Al-Rayyan": {"stadium": "Ahmad bin Ali Stadium", "city": "Al Rayyan", "country": "Qatar", "lat": 25.3300, "lon": 51.3400},
    "Charleroi": {"stadium": "Stade du Pays de Charleroi", "city": "Charleroi", "country": "Belgium", "lat": 50.4086, "lon": 4.4447},
    "Melbourne City": {"stadium": "AAMI Park", "city": "Melbourne", "country": "Australia", "lat": -37.8250, "lon": 144.9835},
    "New York City FC": {"stadium": "Yankee Stadium", "city": "New York", "country": "United States", "lat": 40.8296, "lon": -73.9262},
    "Heart of Midlothian": {"stadium": "Tynecastle Park", "city": "Edinburgh", "country": "Scotland", "lat": 55.9392, "lon": -3.2322},
    "Watford": {"stadium": "Vicarage Road", "city": "Watford", "country": "England", "lat": 51.6498, "lon": -0.4015},
    "Swansea City": {"stadium": "Swansea.com Stadium", "city": "Swansea", "country": "Wales", "lat": 51.6428, "lon": -3.9347},
    "Werder Bremen": {"stadium": "Weserstadion", "city": "Bremen", "country": "Germany", "lat": 53.0664, "lon": 8.8376},
    "Venezia": {"stadium": "Stadio Pier Luigi Penzo", "city": "Venice", "country": "Italy", "lat": 45.4278, "lon": 12.3764},
    "Pafos": {"stadium": "Stelios Kyriakides Stadium", "city": "Paphos", "country": "Cyprus", "lat": 34.7667, "lon": 32.4167},
    "Hull City": {"stadium": "MKM Stadium", "city": "Hull", "country": "England", "lat": 53.7461, "lon": -0.3677},
    "Rijeka": {"stadium": "Stadion Rujevica", "city": "Rijeka", "country": "Croatia", "lat": 45.3397, "lon": 14.4094},
    "Chicago Fire": {"stadium": "Soldier Field", "city": "Chicago", "country": "United States", "lat": 41.8623, "lon": -87.6167},
    "Orlando City": {"stadium": "Inter&Co Stadium", "city": "Orlando", "country": "United States", "lat": 28.5389, "lon": -81.3832},
    "Union Saint-Gilloise": {"stadium": "Dender Football Complex", "city": "Denderleeuw", "country": "Belgium", "lat": 50.8833, "lon": 4.0667},
    "PEC Zwolle": {"stadium": "MAC3PARK Stadion", "city": "Zwolle", "country": "Netherlands", "lat": 52.5000, "lon": 6.0833},
    "Minnesota United": {"stadium": "Allianz Field", "city": "Saint Paul", "country": "United States", "lat": 44.9528, "lon": -93.1650},
    "FC Dallas": {"stadium": "Toyota Stadium", "city": "Frisco", "country": "United States", "lat": 33.1544, "lon": -96.8353},
    "Le Havre": {"stadium": "Stade Oceane", "city": "Le Havre", "country": "France", "lat": 49.4983, "lon": 0.1833},
    "UNAM": {"stadium": "Estadio Olimpico Universitario", "city": "Mexico City", "country": "Mexico", "lat": 19.3320, "lon": -99.1944},
    "Oviedo": {"stadium": "Estadio Carlos Tartiere", "city": "Oviedo", "country": "Spain", "lat": 43.3611, "lon": -5.8592},
    "Çaykur Rizespor": {"stadium": "Caykur Didi Stadium", "city": "Rize", "country": "Turkey", "lat": 41.0500, "lon": 40.5167},
    "Sepahan": {"stadium": "Foolad Shahr Stadium", "city": "Isfahan", "country": "Iran", "lat": 32.7500, "lon": 51.5667},
    "Al-Talaba": {"stadium": "Al-Shaab Stadium", "city": "Baghdad", "country": "Iraq", "lat": 33.3400, "lon": 44.4000},
    "Al-Karma": {"stadium": "Al-Najaf Stadium", "city": "Najaf", "country": "Iraq", "lat": 32.0000, "lon": 44.3333},
    "Al-Faisaly": {"stadium": "Amman International Stadium", "city": "Amman", "country": "Jordan", "lat": 31.9928, "lon": 35.9242},
    "Wellington Phoenix": {"stadium": "Sky Stadium", "city": "Wellington", "country": "New Zealand", "lat": -41.2883, "lon": 174.7761},
    "Bodø/Glimt": {"stadium": "Aspmyra Stadion", "city": "Bodo", "country": "Norway", "lat": 67.2764, "lon": 14.3847},
    "Al-Gharafa": {"stadium": "Thani bin Jassim Stadium", "city": "Doha", "country": "Qatar", "lat": 25.3361, "lon": 51.4572},
    "Lorient": {"stadium": "Stade du Moustoir", "city": "Lorient", "country": "France", "lat": 47.7486, "lon": -3.3681},
    "Kasimpasa": {"stadium": "Recep Tayyip Erdogan Stadium", "city": "Istanbul", "country": "Turkey", "lat": 41.0392, "lon": 28.9700},
    "Neftchi Fergana": {"stadium": "Fargona Stadium", "city": "Fergana", "country": "Uzbekistan", "lat": 40.3864, "lon": 71.7864},
    "Nasaf": {"stadium": "Markaziy Stadium", "city": "Qarshi", "country": "Uzbekistan", "lat": 38.8600, "lon": 65.7850},
    "USM Alger": {"stadium": "Stade du 5 Juillet", "city": "Algiers", "country": "Algeria", "lat": 36.7500, "lon": 3.0667},
    "JS Kabylie": {"stadium": "Stade du 1er Novembre", "city": "Tizi Ouzou", "country": "Algeria", "lat": 36.7167, "lon": 4.0500},
    "Twente": {"stadium": "De Grolsch Veste", "city": "Enschede", "country": "Netherlands", "lat": 52.3383, "lon": 6.7825},
    "Parma": {"stadium": "Stadio Ennio Tardini", "city": "Parma", "country": "Italy", "lat": 44.7947, "lon": 10.3400},
    "Genoa": {"stadium": "Stadio Luigi Ferraris", "city": "Genoa", "country": "Italy", "lat": 44.4142, "lon": 8.9544},
    "Brondby": {"stadium": "Brondby Stadium", "city": "Brondby", "country": "Denmark", "lat": 55.6494, "lon": 12.3514},
    "LASK": {"stadium": "Raiffeisen Arena", "city": "Linz", "country": "Austria", "lat": 48.2500, "lon": 14.2833},
    "Schalke 04": {"stadium": "Veltins-Arena", "city": "Gelsenkirchen", "country": "Germany", "lat": 51.5547, "lon": 7.0675},
    "Grêmio": {"stadium": "Arena do Gremio", "city": "Porto Alegre", "country": "Brazil", "lat": -30.0650, "lon": -51.2350},
    "Zenit Saint Petersburg": {"stadium": "Gazprom Arena", "city": "Saint Petersburg", "country": "Russia", "lat": 59.9727, "lon": 30.2214},
    "Dender": {"stadium": "Dender Football Complex", "city": "Denderleeuw", "country": "Belgium", "lat": 50.8833, "lon": 4.0667},
    "Southampton": {"stadium": "St Mary's Stadium", "city": "Southampton", "country": "England", "lat": 50.9058, "lon": -1.3911},
    "Al Bataeh": {"stadium": "Al Bataeh Stadium", "city": "Al Bataeh", "country": "UAE", "lat": 25.2833, "lon": 55.7333},
    "Krasnodar": {"stadium": "Krasnodar Stadium", "city": "Krasnodar", "country": "Russia", "lat": 45.0350, "lon": 38.9750},
    "Columbus Crew": {"stadium": "Lower.com Field", "city": "Columbus", "country": "United States", "lat": 39.9689, "lon": -83.0175},
    "San Diego FC": {"stadium": "Snapdragon Stadium", "city": "San Diego", "country": "United States", "lat": 32.7840, "lon": -117.1175},
    "Independiente": {"stadium": "Estadio Libertadores de America", "city": "Avellaneda", "country": "Argentina", "lat": -34.6750, "lon": -58.3650},
    "Osasuna": {"stadium": "El Sadar", "city": "Pamplona", "country": "Spain", "lat": 42.7964, "lon": -1.6372},
    "Miami FC": {"stadium": "Pitbull Stadium", "city": "Miami", "country": "United States", "lat": 25.7520, "lon": -80.3770},
    "RKC Waalwijk": {"stadium": "Mandemakers Stadion", "city": "Waalwijk", "country": "Netherlands", "lat": 51.6833, "lon": 5.0667},
    "Volendam": {"stadium": "Kras Stadion", "city": "Volendam", "country": "Netherlands", "lat": 52.4950, "lon": 5.0700},
    "Maccabi Haifa": {"stadium": "Sammy Ofer Stadium", "city": "Haifa", "country": "Israel", "lat": 32.7833, "lon": 34.9667},
    "NEC": {"stadium": "Goffertstadion", "city": "Nijmegen", "country": "Netherlands", "lat": 51.8225, "lon": 5.8375},
    "Kilmarnock": {"stadium": "Rugby Park", "city": "Kilmarnock", "country": "Scotland", "lat": 55.6042, "lon": -4.5083},
    "Standard Liege": {"stadium": "Stade Maurice Dufrasne", "city": "Liege", "country": "Belgium", "lat": 50.6097, "lon": 5.5436},
    "Huracán": {"stadium": "Estadio Tomas Adolfo Duco", "city": "Buenos Aires", "country": "Argentina", "lat": -34.6350, "lon": -58.3650},
    "Internacional": {"stadium": "Estadio Beira-Rio", "city": "Porto Alegre", "country": "Brazil", "lat": -30.0650, "lon": -51.2350},
    "Club Tijuana": {"stadium": "Estadio Caliente", "city": "Tijuana", "country": "Mexico", "lat": 32.5028, "lon": -117.0039},
    "Al-Najma": {"stadium": "Prince Abdullah bin Jalawi Stadium", "city": "Al-Ahsa", "country": "Saudi Arabia", "lat": 25.3833, "lon": 49.5833},
    "Nordsjaelland": {"stadium": "Right to Dream Park", "city": "Farum", "country": "Denmark", "lat": 55.8167, "lon": 12.3667},
    "Rayo Vallecano": {"stadium": "Campo de Futbol de Vallecas", "city": "Madrid", "country": "Spain", "lat": 40.3919, "lon": -3.6586},
    "Coventry City": {"stadium": "Coventry Building Society Arena", "city": "Coventry", "country": "England", "lat": 52.4481, "lon": -1.4956},
    "PAOK": {"stadium": "Toumba Stadium", "city": "Thessaloniki", "country": "Greece", "lat": 40.6139, "lon": 22.9703},
    "Saint-Étienne": {"stadium": "Stade Geoffroy-Guichard", "city": "Saint-Etienne", "country": "France", "lat": 45.4608, "lon": 4.3928},
    "Lugano": {"stadium": "Stadio di Cornaredo", "city": "Lugano", "country": "Switzerland", "lat": 46.0036, "lon": 8.9511},
    "Philadelphia Union": {"stadium": "Subaru Park", "city": "Chester", "country": "United States", "lat": 39.8328, "lon": -75.3786},
    "Panathinaikos": {"stadium": "Leoforos Alexandras Stadium", "city": "Athens", "country": "Greece", "lat": 37.9925, "lon": 23.7636},
    "Sint-Truiden": {"stadium": "Daknamstadion", "city": "Sint-Truiden", "country": "Belgium", "lat": 50.8167, "lon": 5.1833},
    "FC Tokyo": {"stadium": "Ajinomoto Stadium", "city": "Tokyo", "country": "Japan", "lat": 35.6640, "lon": 139.5272},
    "Kashima Antlers": {"stadium": "Kashima Soccer Stadium", "city": "Kashima", "country": "Japan", "lat": 35.9920, "lon": 140.6400},
    "Toluca": {"stadium": "Estadio Nemesio Diez", "city": "Toluca", "country": "Mexico", "lat": 19.2833, "lon": -99.6667},
    "Dynamo Moscow": {"stadium": "VTB Arena", "city": "Moscow", "country": "Russia", "lat": 55.7914, "lon": 37.5594},
    "Viking": {"stadium": "Viking Stadion", "city": "Stavanger", "country": "Norway", "lat": 58.9000, "lon": 5.7333},
    "Wrexham": {"stadium": "SToK Cae Ras", "city": "Wrexham", "country": "Wales", "lat": 53.0519, "lon": -3.0036},
    "Hannover 96": {"stadium": "Heinz von Heiden Arena", "city": "Hannover", "country": "Germany", "lat": 52.3600, "lon": 9.7310},
    "Stoke City": {"stadium": "bet365 Stadium", "city": "Stoke-on-Trent", "country": "England", "lat": 52.9883, "lon": -2.1756},
    "Celta Vigo": {"stadium": "Balaidos", "city": "Vigo", "country": "Spain", "lat": 42.2119, "lon": -8.7397},
    "Espanyol": {"stadium": "RCDE Stadium", "city": "Cornella", "country": "Spain", "lat": 41.3478, "lon": 2.0756},
    "Hellas Verona": {"stadium": "Stadio Marcantonio Bentegodi", "city": "Verona", "country": "Italy", "lat": 45.4356, "lon": 10.9683},
    "AEK Larnaca": {"stadium": "AEK Arena", "city": "Larnaca", "country": "Cyprus", "lat": 34.9167, "lon": 33.6333},
    "APOEL": {"stadium": "GSP Stadium", "city": "Nicosia", "country": "Cyprus", "lat": 35.1147, "lon": 33.3628},
    "Gent": {"stadium": "Planet Group Arena", "city": "Ghent", "country": "Belgium", "lat": 51.0833, "lon": 3.7167},
    "Ferencvaros": {"stadium": "Groupama Arena", "city": "Budapest", "country": "Hungary", "lat": 47.4750, "lon": 19.0958},
    "Port": {"stadium": "Estadio do Dragao", "city": "Porto", "country": "Portugal", "lat": 41.1617, "lon": -8.5836},
    "Luton Town": {"stadium": "Kenilworth Road", "city": "Luton", "country": "England", "lat": 51.8839, "lon": -0.4306},
    "Nashville SC": {"stadium": "GEODIS Park", "city": "Nashville", "country": "United States", "lat": 36.1303, "lon": -86.7656},
    "AGF": {"stadium": "Ceres Park", "city": "Aarhus", "country": "Denmark", "lat": 56.1167, "lon": 10.2000},
    "Cercle Brugge": {"stadium": "Jan Breydel Stadium", "city": "Bruges", "country": "Belgium", "lat": 51.1932, "lon": 3.1808},
    "Sanfrecce Hiroshima": {"stadium": "Edion Stadium Hiroshima", "city": "Hiroshima", "country": "Japan", "lat": 34.3833, "lon": 132.4833},
    "Raja Casablanca": {"stadium": "Stade Mohammed V", "city": "Casablanca", "country": "Morocco", "lat": 33.5519, "lon": -7.6497},
    "Esperance de Tunis": {"stadium": "Stade Olympique de Rades", "city": "Rades", "country": "Tunisia", "lat": 36.7667, "lon": 10.2833},
    "Polokwane City": {"stadium": "Peter Mokaba Stadium", "city": "Polokwane", "country": "South Africa", "lat": -23.9000, "lon": 29.4500},
    "Siwelele": {"stadium": "Charles Mopeli Stadium", "city": "QwaQwa", "country": "South Africa", "lat": -28.5167, "lon": 28.8667},
    "Tondela": {"stadium": "Estadio Joao Cardoso", "city": "Tondela", "country": "Portugal", "lat": 40.5167, "lon": -8.0833},
    "Zhejiang": {"stadium": "Yellow Dragon Sports Center", "city": "Hangzhou", "country": "China", "lat": 30.2667, "lon": 120.1667},
    "Daejeon Hana Citizen": {"stadium": "Daejeon World Cup Stadium", "city": "Daejeon", "country": "South Korea", "lat": 36.3170, "lon": 127.4280},
    "Gangwon FC": {"stadium": "Chuncheon Songam Stadium", "city": "Chuncheon", "country": "South Korea", "lat": 37.8747, "lon": 127.7342},
    "Austria Wien": {"stadium": "Generali Arena", "city": "Vienna", "country": "Austria", "lat": 48.1986, "lon": 16.2650},
    "Lokomotiv Moscow": {"stadium": "RZD Arena", "city": "Moscow", "country": "Russia", "lat": 55.8142, "lon": 37.7303},
    "Hradec Kralove": {"stadium": "Viceberg Stadium", "city": "Hradec Kralove", "country": "Czechia", "lat": 50.2092, "lon": 15.8325},
    "Molde": {"stadium": "Aker Stadion", "city": "Molde", "country": "Norway", "lat": 62.7333, "lon": 7.1500},
    "Cerro Porteno": {"stadium": "Estadio General Pablo Rojas", "city": "Asuncion", "country": "Paraguay", "lat": -25.3197, "lon": -57.6125},
    "Sao Paulo": {"stadium": "Estadio do Morumbi", "city": "Sao Paulo", "country": "Brazil", "lat": -23.6006, "lon": -46.7197},
    "Santos Laguna": {"stadium": "Estadio Corona", "city": "Torreon", "country": "Mexico", "lat": 25.5428, "lon": -103.4069},
    "Santos": {"stadium": "Estadio Urbano Caldeira", "city": "Santos", "country": "Brazil", "lat": -23.9608, "lon": -46.3331},
    "Brest": {"stadium": "Stade Francis-Le Ble", "city": "Brest", "country": "France", "lat": 48.4036, "lon": -4.4667},
    "Angers": {"stadium": "Stade Raymond Kopa", "city": "Angers", "country": "France", "lat": 47.4608, "lon": -0.5306},
    "Montpellier": {"stadium": "Stade de la Mosson", "city": "Montpellier", "country": "France", "lat": 43.6222, "lon": 3.8119},
    "Lens": {"stadium": "Stade Bollaert-Delelis", "city": "Lens", "country": "France", "lat": 50.4328, "lon": 2.8147},
    "Nantes": {"stadium": "Stade de la Beaujoire", "city": "Nantes", "country": "France", "lat": 47.2558, "lon": -1.5247},
    "Reims": {"stadium": "Stade Auguste-Delaune", "city": "Reims", "country": "France", "lat": 49.2467, "lon": 4.0250},
    "Tunis": {"stadium": "Stade Olympique de Rades", "city": "Rades", "country": "Tunisia", "lat": 36.7667, "lon": 10.2833},
    # enrich_clubs gaps — no Wikidata home venue (P115) on club page; stadium coords from Wikipedia/OSM.
    "Cosmos Koblenz": {"stadium": "Stadion Oberwerth", "city": "Koblenz", "country": "Germany", "lat": 50.3305, "lon": 7.5866},
    "Puerto Cabello": {"stadium": "Complejo Deportivo Socialista", "city": "Puerto Cabello", "country": "Venezuela", "lat": 10.4680, "lon": -68.0098},
    "RS Berkane": {"stadium": "Stade Municipal de Berkane", "city": "Berkane", "country": "Morocco", "lat": 34.9170, "lon": -2.3170},
    "Surkhon Termiz": {"stadium": "Surkhon Arena", "city": "Termez", "country": "Uzbekistan", "lat": 37.2413, "lon": 67.3040},
}


def main() -> None:
    clubs_data = json.loads(CLUBS_JSON.read_text(encoding="utf-8"))
    clubs: dict[str, dict] = clubs_data["clubs"]

    added = 0
    for raw_name, info in SUPPLEMENT.items():
        key = CLUB_ALIASES.get(raw_name, raw_name)
        if key not in clubs:
            clubs[key] = info
            added += 1

    clubs_data["clubs"] = dict(sorted(clubs.items()))
    CLUBS_JSON.write_text(
        json.dumps(clubs_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    squads = json.loads(SQUADS_JSON.read_text(encoding="utf-8"))
    apply_aliases_to_squads(squads)
    SQUADS_JSON.write_text(
        json.dumps(squads, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Seeded {added} clubs into {CLUBS_JSON.name}")
    print(f"Total clubs: {len(clubs)}")


if __name__ == "__main__":
    main()
