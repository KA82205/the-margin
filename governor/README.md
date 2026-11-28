# The governor forecast

A forecast of every governor race from today through the next even-year election (the odd-year races before it
included), built as the Senate and House forecasts are, on the national mood the Senate model reads.

| Step | Code | What it does |
|---|---|---|
| The training data | `gov_data.py` | every governor race 2006-2024: FiveThirtyEight's results by candidate (CC BY 4.0), the state's lean as the presidential and Senate forecasts read it, the governor and whether they were on the November ballot (Wikipedia's overview of each year, CC BY-SA 4.0), the national House vote |
| Race polls | `gov_polls.py` | each race's polls of its two nominees, averaged at each distance from election day as the presidential model weighs polls, partisan ones left out: FiveThirtyEight's governor polls for 2018-2024 (from the archived copy in `jcervas/data`), Wikipedia's race pages after |
| The back-test | `gov_simulate.py` | each year with a national mood (2018 on) forecast from the other years at each distance, every race simulated together |
| The fit | `gov_fit.py` | `data/governor/model.json` and `data/governor/backtest.json` |
| The live forecast | `gov_live.py` | every hour after the Senate forecast (`.github/workflows/governor.yml`): Wikipedia's overviews and race pages, the simulation, `docs/api/governor.json` for the Governors tab |
| After each year's races | `gov_after.py` | every week (`.github/workflows/governor-after.yml`): once the results settle and Wikipedia has them all, the races and their polls join the training data and the model is refitted |

What the fit found (2006-2024): a governor's race follows the state's lean far less than a House or Senate race does
(0.37 of a point for each point of lean), and a sitting governor on the ballot is worth about 7 points of share to a
Democrat and 9 to a Republican. A year's level moves about 0.73 of a point for each point of the national House vote. The
race polls matter more than for any other office here: in the back-test of 2018-2024, they took the last day's races
called from 84 to 88 of 94 and the typical miss from 11.4 points of margin to 7.6.

2026, forecast from 2006-2024 alone (`python governor/gov_after.py --year 2026 --pages FILE --test --save`): on the last
day 33 of 36 races called, a typical miss of 6.6 points, and 22.6 Democratic wins expected against the 24 they won, inside
the 80% range. A year out the range missed, as the House's did: 2026's national mood fell short of the result.

Tests: `python tests/test_governor.py`.
