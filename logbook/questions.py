"""The wording of every question, in one place.

The command line and the bot ask the same things in the same words, so a person
who has used one recognises the other, and a change to an explanation only has to
be made once.

Each entry carries:
    ask     the question itself, short enough for a chat bubble
    why     what it is for, in plain words - shown under the question
    example what a good answer looks like, shown in brackets
"""

from __future__ import annotations

QUESTIONS = {
    # --- period -------------------------------------------------------------
    "start_date": {
        "ask": "What date does the logbook start?",
        "why": "The first day you want recorded. Most people start at the beginning "
               "of a financial year or the week they started driving.",
        "example": "01/07/2025",
    },
    "weeks": {
        "ask": "How many weeks should it cover?",
        "why": "The ATO wants at least 12 continuous weeks the first time you keep a "
               "logbook, and that stretch should look like your normal driving.",
        "example": "12",
    },
    "sheet_mode": {
        "ask": "Your period covers two financial years. How do you want it laid out?",
        "why": "A financial year runs 1 July to 30 June. Separate sheets keep each "
               "year's totals and percentage on their own tab, which is easier at tax "
               "time. One combined sheet keeps everything in a single table.",
        "example": "separate sheets",
    },

    # --- income -------------------------------------------------------------
    "income_month": {
        "ask": "What did you earn?",
        "why": "Your driving income for that stretch, before expenses. This is what "
               "the business kilometres are worked out from, so use the figure from "
               "your platform statement.",
        "example": "5000",
    },
    "income_same": {
        "ask": "Did you earn about the same each month?",
        "why": "If it was steady, give one figure and it is spread across the months, "
               "scaled down for any part month. Otherwise you will be asked month by "
               "month.",
        "example": "same each month",
    },

    # --- vehicle and owner ---------------------------------------------------
    "owner_name": {
        "ask": "What is your full name?",
        "why": "It goes at the top of the logbook as the driver. Leave it out if you "
               "would rather not have it in the file.",
        "example": "Yash Vadukiya",
    },
    "abn": {
        "ask": "What is your ABN?",
        "why": "Your Australian Business Number, if you drive under one. Eleven "
               "digits, and it is checked. Leave it blank if you do not have one.",
        "example": "51 824 753 556",
    },
    "make": {
        "ask": "Who makes your car?",
        "why": "The manufacturer. The ATO asks for make, model, engine size and plate "
               "so the logbook clearly belongs to one particular car.",
        "example": "Toyota",
    },
    "model": {
        "ask": "What model is it?",
        "why": "The model name as it appears on your registration papers.",
        "example": "Corolla Hybrid",
    },
    "year_of_manufacture": {
        "ask": "What year was it built?",
        "why": "Not required by the ATO, but it helps identify the car. Leave it out "
               "if you are unsure.",
        "example": "2021",
    },
    "engine_capacity": {
        "ask": "What is the engine size?",
        "why": "The ATO asks for engine capacity. It is on your registration papers, "
               "written either in litres or cubic centimetres.",
        "example": "1.8L, or 1798cc",
    },
    "registration": {
        "ask": "What is the registration number?",
        "why": "The number plate, up to seven letters and numbers. Spaces and dashes "
               "do not matter.",
        "example": "ABC123",
    },

    # --- odometer -------------------------------------------------------------
    "start_odometer": {
        "ask": "What did the odometer read on the first day?",
        "why": "The number on your dashboard at the start of the period, in whole "
               "kilometres.",
        "example": "45230",
    },
    "end_odometer": {
        "ask": "And on the last day?",
        "why": "The reading at the end of the period. The difference between the two "
               "is every kilometre the car travelled, business and private together.",
        "example": "55230",
    },

    # --- what the driving is for ---------------------------------------------
    "work_type": {
        "ask": "What is the driving for?",
        "why": "This sets the wording on each row and the areas they mention. Pick "
               "both if you do rideshare and delivery in the same period.",
        "example": "rideshare",
    },

    # --- travel pattern --------------------------------------------------------
    "work_days": {
        "ask": "Which days do you work?",
        "why": "Business travel is recorded on these days and no others. A day you "
               "do not name here carries private travel only, so choose every day you "
               "normally drive for income.",
        "example": "Fri,Sat,Sun or Mon-Fri",
    },
    "business_share_on_work_days": {
        "ask": "On a day you work, how much of your driving is for income?",
        "why": "The rest of that day counts as private - the shopping on the way "
               "home, the detour to pick someone up. Most drivers sit between 70% "
               "and 95%.",
        "example": "85",
    },
    "max_km_per_day": {
        "ask": "What is the most you would drive in one day, all up?",
        "why": "Business and private together. Nothing in the logbook will go above "
               "this, so it keeps every day believable.",
        "example": "420",
    },
    "max_business_km_per_day": {
        "ask": "And the most business kilometres in one day?",
        "why": "Your longest realistic shift. A day above this would stand out if "
               "anyone looked closely.",
        "example": "350",
    },
    "max_private_km_per_day": {
        "ask": "The most private kilometres in one day?",
        "why": "Your longest personal trip - a weekend drive, a trip to see family.",
        "example": "150",
    },
    "seed": {
        "ask": "Pick a shuffle number.",
        "why": "The daily distances are varied so the logbook does not read as a "
               "pattern. This number decides that variation: the same number always "
               "gives you the same logbook, a different one reshuffles the days. Keep "
               "it if you might need to produce the same file again.",
        "example": "42",
    },

    # --- wording ---------------------------------------------------------------
    "city": {
        "ask": "Which city do you drive in?",
        "why": "Picks a starting list of suburbs for the Destination column. You can "
               "replace them with your own next.",
        "example": "brisbane",
    },
    "rideshare_reasons": {
        "ask": "How would you describe your rideshare trips?",
        "why": "The ATO will not accept a bare \"business\". Each entry should say why "
               "the trip earned income and suit its distance. Give a few, separated "
               "by a vertical bar, and they are used across the rows.",
        "example": "Airport transfers | Evening fares | Event pickups",
    },
    "delivery_reasons": {
        "ask": "And your delivery runs?",
        "why": "Same idea - a few different wordings so the column does not read as "
               "one line repeated.",
        "example": "Food delivery run | Parcel round | Grocery drop",
    },
    "private_reasons": {
        "ask": "How would you describe your private trips?",
        "why": "These rows are the travel you cannot claim, so a short honest "
               "description is all that is needed.",
        "example": "Personal errands | Family travel",
    },
    "destinations": {
        "ask": "Which areas do you drive to?",
        "why": "One is picked for each work journey, and a long day names two, since "
               "one suburb would not match the distance. Leave it as the default list "
               "if it fits your city.",
        "example": "Brisbane CBD | Chermside | North Lakes",
    },

    # --- output ------------------------------------------------------------------
    "sheet_name": {
        "ask": "What should the sheet be called?",
        "why": "The tab name inside the spreadsheet.",
        "example": "Logbook",
    },
    "output": {
        "ask": "What should the file be called?",
        "why": "Where it is saved. It gets a .xlsx ending if you leave one off.",
        "example": "car_logbook.xlsx",
    },
}


def ask_text(key: str) -> str:
    return QUESTIONS[key]["ask"]


def why(key: str) -> str:
    return QUESTIONS[key]["why"]


def example(key: str) -> str:
    return QUESTIONS[key]["example"]


def prompt_line(key: str) -> str:
    """The question with its example in brackets, for a one-line prompt."""
    entry = QUESTIONS[key]
    return f"{entry['ask']} (e.g. {entry['example']})"


def full_prompt(key: str, indent: str = "  ") -> str:
    """Question, the reason for it, and an example - for a chat message."""
    entry = QUESTIONS[key]
    return f"{entry['ask']}\n{indent}{entry['why']}\n{indent}Example: {entry['example']}"
