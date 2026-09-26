# Car logbook generator

Builds an ATO-style motor vehicle logbook spreadsheet from what you earned.
Nothing to install, nothing to host.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Mr-Yash-01/car-logbook/blob/main/logbook.ipynb)
[![Open in Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Mr-Yash-01/car-logbook/main?labpath=logbook.ipynb)

Click **Open in Colab**, fill in the boxes, run the cells. The spreadsheet
downloads to your device. Binder is the same notebook without needing a Google
account — it takes a minute or two to start the first time.

> Replace `YOUR-NAME` in both badges with your GitHub username after you push
> this repository. Nothing else needs changing.

## What you fill in

| | |
| --- | --- |
| **Your car** | Make, model, engine size, plate — the four things the ATO asks for |
| **Period and odometer** | First day, how many weeks, and the reading on the dashboard at each end |
| **Income** | What you earn in a typical month, before expenses |
| **How you drive** | Which days you work, how much of a work day is for income, and your daily limits |

## What it does with that

Business distance comes from what you earned. There is nothing to set.

Days you say you work carry the business travel, and nothing else does. On a
work day, a share you choose says how much of that day was for income; the rest
of that day is private. Days off carry private travel only.

Before anything is built, the pattern is checked against the period and against
each month. If the days cannot hold the kilometres, you are shown what does not
fit and the closest pattern that does is used instead — one that adds work days
or lifts a daily limit, never one that records fewer business kilometres.

If your period crosses 30 June it covers two financial years, and you get a
sheet for each.

## Running it on your own machine

The notebook is the easy way in, but the same code runs as a command-line tool
where every question explains itself.

```bash
pip install -r requirements.txt

python cli.py                              # the questions
python cli.py --config inputs.json         # no questions
python audit_ato.py your_logbook.xlsx      # check a finished file
python run_tests.py                        # 307 checks
```

Opening the folder in VS Code gives you run buttons for the tool and the tests.
GitHub Codespaces works too — the devcontainer installs everything on first boot.

## Layout

```
logbook.ipynb       the notebook people open from the badges
logbook/            the engine
  errors.py         failures that carry a message a person can read
  text.py           reading and checking what people type
  dates.py          periods, real month lengths, Australian financial years
  wording.py        default reasons and areas, by city
  questions.py      the wording of every question
  config.py         every setting, and the checks that repair or refuse them
  allocate.py       spreading kilometres over days without losing one
  pattern.py        whether a travel pattern fits, and what would
  journeys.py       totals into a list of journeys
  workbook.py       the spreadsheet itself
  api.py            settings in, spreadsheet out
  notebook.py       the one call the notebook makes
cli.py              the question-by-question tool
audit_ato.py        checks a finished spreadsheet against the ATO's requirements
tests/              307 checks; run them with run_tests.py
```

## Before you rely on it

A logbook has to record journeys you actually made. This builds a draft from
your income, so check the rows against your platform statements, and keep
receipts for fuel, servicing, registration and insurance separately — the
logbook only sets the percentage you apply to them.

`python audit_ato.py your_logbook.xlsx` checks the shape of the record against
the requirements on the ATO's logbook method page. It cannot check whether the
travel happened.
