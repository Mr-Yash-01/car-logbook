# Car logbook generator

Makes a car logbook spreadsheet for an Australian tax return — the kind the ATO
expects if you claim car expenses using the logbook method.

Nothing to install and nothing to pay for. It runs in your browser, on a phone or
a computer, and takes about three minutes.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Mr-Yash-01/car-logbook/blob/main/logbook.ipynb)
[![Open in Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Mr-Yash-01/car-logbook/main?labpath=logbook.ipynb)

## Start here

1. Click **Open in Colab** above. You will need a free Google account.
2. Run each cell in order with the play button at its top-left corner. On a phone,
   tap the cell first, then tap the play button.
3. Fill in the boxes as you reach them. Every box already has something in it, so
   you only change what is different for you.
4. The last step builds the spreadsheet and downloads it.

**No Google account?** Use **Open in Binder** instead. It is the same notebook and
needs no sign-in, but takes a minute or two to start, and the questions appear as
lines of code rather than boxes — you type your answers between the quote marks.

## Have these ready

- The **odometer reading** on the first day of the period, and on the last day
- What you **earned in a typical month** from driving, before expenses
- Your **number plate** and **engine size** — both are on your registration papers
- Which **days of the week** you normally drive for income

## What it asks, step by step

| Step | What it wants |
| --- | --- |
| 1 · Set up | Nothing. Press play and wait for `Ready.` |
| 2 · Your car | Make, model, engine size, plate — the four things the ATO asks for |
| 3 · Period and odometer | First day, how many weeks, and the reading at each end |
| 4 · What you earn | A typical month's driving income, before expenses |
| 5 · How you drive | Days you work, how much of a work day is for income, daily limits |
| 6 · Build it | Press play. The spreadsheet downloads to your device. |

Every box is explained in the notebook itself, with its starting value shown in
square brackets.

## What it does with your answers

**Business distance comes from what you earned.** There is no factor to set and
nothing to work out yourself.

**Days you say you work carry the business travel, and no other day does.** On a
work day, the share you choose says how much of that day was for income; the rest
of the same day is private. Days off carry private travel only.

**Your answers are checked before anything is built** — against the whole period,
and against each month on its own. If the days cannot hold the kilometres, you are
shown exactly what does not fit, and the closest pattern that does work is used
instead: one that adds a work day or lifts a daily limit, never one that records
fewer business kilometres.

**A period crossing 30 June covers two financial years**, and each one gets its own
tab.

## Running it on your own computer

The notebook is the easy way in. The same code also runs as a command-line tool,
where every question explains itself as you go.

```bash
pip install -r requirements.txt

python cli.py                              # answer the questions
python cli.py --config inputs.json         # no questions, answers from a file
python audit_ato.py your_logbook.xlsx      # check a finished file
python run_tests.py                        # the test suite
```

Opening the folder in VS Code gives you run buttons for the tool and the tests.
GitHub Codespaces works too — the devcontainer installs everything on first boot.

## Layout

```
logbook.ipynb       the notebook the badges open
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
tests/              the checks; run them with run_tests.py
```

## Before you rely on it

A logbook has to record journeys you actually made. This builds a draft from your
income, so check the rows against your platform statements before you lodge
anything, and keep receipts for fuel, servicing, registration and insurance
separately — the logbook only sets the percentage you apply to them.

`python audit_ato.py your_logbook.xlsx` measures the file against the requirements
on the ATO's logbook method page. It checks the shape of the record. It cannot
check whether the travel happened.

This is not tax advice.
