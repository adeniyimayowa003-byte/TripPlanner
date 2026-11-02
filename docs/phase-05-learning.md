# Phase 5 — Understand the daily itinerary

This guide explains the implemented itinerary feature and how to explore it in the app.
The [verification report](phase-05-implementation.md) records the 322 passing tests,
browser checks, and remaining travel-data limitations.

## What this feature adds

Recommendations answer **“Which ideas match me?”** The itinerary answers **“How could I
spread some of those ideas across my days?”** It assigns suggestions to simple slots,
avoids repeated places, and checks their combined costs.

The allowance still covers **activities and food per person in EUR**. It excludes flights,
accommodation, and transport. Catalog prices are illustrative, not live quotes.
An itinerary may leave gaps; it must not invent places or meals to look complete.

## Where the responsibilities live

| File | Its job |
| --- | --- |
| [recommendations.py](../recommendations.py) | Filter, score, sort, and explain eligible ideas. |
| [itinerary.py](../itinerary.py) | Choose unique ideas for slots and calculate exact scheduled totals. |
| [app.py](../app.py) | Read the validated draft, call the scheduler, and return the itinerary page. |
| [templates/itinerary.html](../templates/itinerary.html) | Display days, suggestions, costs, explanations, and navigation. |
| [tests/test_itinerary.py](../tests/test_itinerary.py) | Check the scheduling rules directly. |
| [tests/test_itinerary_flow.py](../tests/test_itinerary_flow.py) | Check requests, page content, sessions, and protected clearing. |

The separate scheduler is easier to test. `generate_itinerary(preferences, catalog=None)`
receives validated preferences and can receive a small catalog directly for a test.
It returns a dictionary containing days, slots, totals, unused ideas, counts, and notices.
Each filled slot contains a recommendation record; an empty slot contains `None`.

## Follow one request

**Preferences → trip ideas → GET /itinerary → scheduler → rendered daily plan.**

The route reuses the current validated draft and the current request's catalog snapshot.
It does not accept unchecked money or day values directly from a link. The scheduler
reuses the recommender, then adds allocation rules without changing its scores or order.
The template turns prepared data into HTML; it does not decide which idea wins a slot.

## How the scheduler chooses

A relaxed trip has **Morning and Evening** slots. No pace preference has **Morning,
Afternoon, and Evening**. Supported active pace also has three slots, but the current
Paris catalog does not support offering that option.

Allocation happens in passes: Morning across every day, then Afternoon across every day
when applicable, then Evening across every day. This is called **slot-major iteration**.
It spreads a small catalog across days instead of filling Day 1 completely first.
The page still displays each day's slots chronologically.

Morning and Afternoon consider attractions and activities. Evening tries restaurants first,
then attractions or activities if no unused restaurant fits. A restaurant is never put in
a daytime slot. An evening activity stays labeled as an activity, not as a meal.

Within the permitted category, choose the first unused idea in recommendation order that
fits the day's remaining allowance. If an idea is too expensive now, keep looking.
Do not discard it: it might fit another day's less-used allowance.

A **set** of used catalog IDs prevents repeats; add an ID only after scheduling succeeds.
Lists preserve order; dictionaries group each day's number, slots, and running cost.

This is a **greedy algorithm**: choose the first suitable idea now, without rearranging
earlier choices later. It is predictable, not an optimizer. Daytime choices can consume
money that would otherwise fit a restaurant. It does not promise equal costs on every day.

## Why combining costs needs another check

The recommender checks whether each idea can fit one day's allowance individually.
That does not prove two or three ideas can fit together. The scheduler checks the sum:

```text
(current day cost + candidate cost) × requested days <= total allowance
```

All costs remain `Decimal` values until display. With EUR 100.01 over 3 days, the preview
rounds to EUR 33.34, but that rounded preview is not permission to spend EUR 33.34 daily:

```text
(20.00 + 13.34) × 3 = 100.02 → cannot share this day
(20.00 + 13.33) × 3 =  99.99 → can share this day
```

Each day uses the same exact limit; unused money is not transferred to another day.
Day estimates sum only scheduled items. The trip estimate sums all day estimates.
**Unallocated allowance** is the original allowance minus the trip estimate. It is not
guaranteed savings: unscheduled meals and excluded travel expenses are not accounted for.
A real zero-cost catalog item can be labeled Free. An empty slot is not a free activity.

## Work through the sample

Choose Paris, 3 days, EUR 300, food and history, relaxed, and family-friendly.
The current illustrative catalog produces this expected allocation:

| Day | Morning | Evening | Estimated scheduled cost |
| --- | --- | --- | ---: |
| 1 | Luxembourg Gardens | Le Procope | EUR 50.00 |
| 2 | Seine Riverside Walk | Café de Flore | EUR 28.00 |
| 3 | Notre-Dame Cathedral | Louvre Museum | EUR 25.00 |

The trip estimate is **EUR 103.00** and the unallocated allowance is **EUR 197.00**.
Eiffel Tower remains an alternative on the ideas page. Day 3 has no restaurant suggestion;
the Louvre fallback is not dinner or a claim about evening opening hours.

Removing the pace preference creates nine slots. The seven matching ideas cost EUR 135.00
in total, leaving two gaps. Lowering the relaxed sample to EUR 60 leaves only the three
free history ideas in Morning slots, with no invented evening ideas or meals.

## What is stored, and what is not

Only the successful preference draft is stored in the browser session, not generated days
or HTML. Opening `/itinerary` recomputes the result. The same inputs and catalog give the
same result: this is **determinism**. Updated catalog data can change the next result.
The scheduler does not modify its inputs.

A valid edit replaces the draft; an invalid edit keeps the previous valid one. Clearing
the draft removes access to the computed itinerary too. This is not permanent database
saving. Another browser session does not automatically receive this draft.

Opening the itinerary is a read-only **GET**. Clearing is a state-changing **POST**, with
the existing session-bound CSRF token. Normal links and server-rendered forms provide the
core flow without JavaScript; the form's instant allowance preview is an enhancement.

## What the AI can and cannot claim

The recommender is rule-based personalization; the scheduler is rule-based allocation.
Neither trains a model, calls a language model, or acts as an autonomous agent.
Reasons use actual catalog tags. A selected family-friendly preference does not verify an
untagged venue, and a tagged unused alternative does not verify the scheduled itinerary.

Time slots are illustrative. There are no opening hours, durations, travel times, or live
availability checks. Travelers must check feasibility themselves. Honest gaps and notices
are useful results, not failures to hide.

## Six small practice tasks

1. Predict the sample's six assignments and EUR 103.00 total before generating it.
2. Remove the pace preference. Explain the nine-slot capacity and why two gaps remain.
3. Set EUR 60, then try food only with EUR 1. Explain why gaps beat repeated or invented ideas.
4. Calculate the EUR 100.01 boundary above. Explain individual versus combined affordability.
5. Edit, refresh, make an invalid edit, and clear a draft. Describe stored versus recomputed data.
6. Run pytest. Identify one scheduling unit test and one route integration test; explain why
   page-content tests do not establish mobile layout, keyboard behavior, or opening hours.

For focused checks, run this from the project folder:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_itinerary.py tests/test_itinerary_flow.py
```

If Windows blocks pytest's temporary directory, supply a fresh, specifically named folder
inside `.tmp` as `--basetemp`. Never target the project or a folder holding useful files.

## A short presentation explanation

“TripPlanner first ranks matching catalog ideas, then a separate greedy scheduler places
unique ideas into daily slots. It checks combined costs with exact decimal arithmetic,
tries restaurants in the evening, and explains gaps. The plan is recomputed from the
current draft, not permanently saved. It is explainable rule-based AI, not a language
model or a real-world feasibility guarantee. I followed approved specifications, planning,
tests defined first, and implementation.”
