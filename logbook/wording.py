"""Default reasons and areas.

The ATO will not accept a bare "business" as a reason: an entry has to say enough
to show why the journey earned income and to suit the distance. These pools give
every row something specific even when a person accepts all the defaults, and
they are wide enough that a column of 120 journeys does not read as one line
repeated.

Areas are Australian capitals, so most drivers find their own; anyone can replace
a list with their own suburbs.
"""

from __future__ import annotations

RIDESHARE_REASONS = [
    "Rideshare fares - passenger trips",
    "Rideshare fares - morning peak",
    "Rideshare fares - evening shift",
    "Rideshare fares - late night runs",
    "Rideshare fares - airport transfers",
    "Rideshare fares - event and venue pickups",
    "Rideshare fares - suburban runs",
    "Rideshare fares - weekend shift",
]

DELIVERY_REASONS = [
    "Food delivery run",
    "Food delivery - dinner peak",
    "Food delivery - lunch peak",
    "Parcel delivery run",
    "Grocery delivery run",
    "Courier pickups and drop-offs",
    "Multi-drop delivery round",
    "Late night delivery run",
]

PRIVATE_REASONS = [
    "Private use - personal travel",
    "Private use - shopping trip",
    "Private use - family travel",
    "Private use - personal errands",
    "Private use - visiting friends",
    "Private use - weekend outing",
]

# Areas by city, so a driver can pick the set that matches where they work.
AREAS = {
    "brisbane": [
        "Brisbane CBD", "Fortitude Valley", "South Bank", "West End", "Newstead",
        "Chermside", "North Lakes", "Aspley", "Nundah", "Kedron", "Everton Park",
        "Indooroopilly", "Toowong", "Mount Gravatt", "Carindale", "Sunnybank",
        "Brisbane Airport", "Hamilton", "Springwood", "Logan Central",
    ],
    "sydney": [
        "Sydney CBD", "Surry Hills", "Newtown", "Bondi", "Randwick", "Parramatta",
        "Chatswood", "North Sydney", "Manly", "Burwood", "Strathfield", "Liverpool",
        "Bankstown", "Hurstville", "Ryde", "Blacktown", "Sydney Airport",
        "Marrickville", "Pyrmont", "Castle Hill",
    ],
    "melbourne": [
        "Melbourne CBD", "Fitzroy", "Carlton", "St Kilda", "South Yarra", "Richmond",
        "Brunswick", "Footscray", "Docklands", "Prahran", "Hawthorn", "Box Hill",
        "Preston", "Werribee", "Dandenong", "Frankston", "Melbourne Airport",
        "Southbank", "Northcote", "Glen Waverley",
    ],
    "perth": [
        "Perth CBD", "Northbridge", "Fremantle", "Subiaco", "Joondalup", "Cannington",
        "Morley", "Scarborough", "Victoria Park", "Claremont", "Midland", "Rockingham",
        "Mandurah", "Perth Airport", "Cottesloe", "Armadale",
    ],
    "adelaide": [
        "Adelaide CBD", "North Adelaide", "Glenelg", "Norwood", "Prospect", "Unley",
        "Port Adelaide", "Marion", "Modbury", "Elizabeth", "Adelaide Airport",
        "Henley Beach", "Salisbury", "Mawson Lakes",
    ],
    "canberra": [
        "Canberra City", "Belconnen", "Woden", "Tuggeranong", "Gungahlin", "Braddon",
        "Kingston", "Dickson", "Canberra Airport", "Queanbeyan",
    ],
    "hobart": [
        "Hobart CBD", "Sandy Bay", "Glenorchy", "Kingston", "Bellerive", "Moonah",
        "Hobart Airport", "New Town",
    ],
    "darwin": [
        "Darwin CBD", "Palmerston", "Casuarina", "Nightcliff", "Parap", "Berrimah",
        "Darwin Airport", "Humpty Doo",
    ],
}

DEFAULT_CITY = "brisbane"


def areas_for(city: str | None = None) -> list:
    """Areas for a named city, falling back to the default set."""
    key = str(city or DEFAULT_CITY).strip().lower()
    return list(AREAS.get(key, AREAS[DEFAULT_CITY]))


def city_names() -> list:
    return sorted(AREAS)


# Split for the two kinds of work: rideshare leans on the busy places, delivery
# on the residential ones. Both stay within the same city's list.
def rideshare_areas(city: str | None = None) -> list:
    pool = areas_for(city)
    return pool[:6] + pool[-4:]


def delivery_areas(city: str | None = None) -> list:
    pool = areas_for(city)
    return pool[4:16] or pool
