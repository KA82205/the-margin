# Senate back-test (research)

Research towards a Senate forecast. Nothing here feeds the presidential forecast or appears on the site.

## Step 1: the 2018-2024 dataset

`python senate/build_data.py` rebuilds every table in `data/senate/` from the raw files in `data/senate/raw/`.

| Table | What it holds |
|---|---|
| `races.csv` | 137 Senate elections, 2018-2024, decided between a Democrat (or an independent the Democrats backed: Sanders, King, McMullin, Osborn) and a Republican. Both candidates, the two-party result from the round that decided it (Georgia's runoffs included), who held the seat on election day and whether they ran, money raised, and the state's lean |
| `excluded.csv` | The 3 left out, with the reason: California 2018 (two Democrats), Arkansas 2020 (no Democrat), Alaska 2022 (two Republicans) |
| `polls.csv` | 3,291 general-election poll questions naming both candidates, in 121 of the 137 races |
| `generic.csv` | 4,832 generic-ballot poll questions |
| `national.csv` | The national House vote each year, two-party, from contested districts |
| `benchmark_538.csv.gz` | FiveThirtyEight's published Senate forecasts of 2018, 2020 and 2022, every day, in its three versions |

**Incumbency** is worked out from who held each seat: its last elected winner, a special election held for it since, or a
senator appointed to a vacancy (`HELD_BY` in `build_data.py`, each a matter of record). It is not taken from the FEC's
candidate status, which the FEC updates after the election and so would let the result leak into the test.

**The state's lean** is read as The Margin reads it for the presidency: the state's Democratic two-party share against the
nation's in the last presidential election (three quarters) and the one before (one quarter).

## Limits of the dataset

- **Money is the total for the two-year cycle**, as the FEC's summary file gives it, so it includes money raised after the
  date a forecast would be made. Until it is replaced by money raised by each date (the FEC's filings by quarter), it can
  be tested only as a last-day input, and even there it is slightly flattered.
- **Four candidates have no FEC summary** (Kevin O'Conner 2020, Bob McDermott 2022, Chris Chaffee 2022, Lucas Kunce 2024).
- **Polls** are FiveThirtyEight's archive as it stood when the site closed; 16 races have none. The archive's own
  pollster grades are kept but not yet used.
- **FiveThirtyEight's benchmark** covers 2018-2022; it published no Senate forecast for 2024 in this archive.

## Sources

- MIT Election Data and Science Lab, "U.S. Senate 1976-2024", doi:10.7910/DVN/PEJ5QU (CC0)
- Federal Election Commission, "All candidates" summary files, 2018-2026 (public domain)
- FiveThirtyEight polls and forecasts (CC BY 4.0), from the archived copy in github.com/jcervas/data

## Step 2: the back-test, first pass

`python senate/backtest.py` forecasts every race at 365, 250, 120, 60, 30, 14, 7 and 1 days before the election, each
year from the other three, and writes `data/senate/backtest.json`. Poll averages use the presidential model's own weights.

What it shows (typical miss on the margin, in points; competitive races are those decided by under 20 points):

| Version | All races, last day | Competitive, last day | Competitive, 60 days out |
|---|---|---|---|
| State lean and generic ballot | 9.2 | 9.0 | 8.9 |
| + whether the seat's holder runs | 7.8 | 7.4 | 7.3 |
| + race polls | 6.6 | 5.3 | 5.0 |
| FiveThirtyEight deluxe (2018-2022 only) | | 5.0 | 5.7 |

- **Incumbency and polls both matter;** money adds a little on the last day (7.8 to 7.4 without polls), but its figures
  are cycle totals, so that is flattered.
- **On the margin, the model is about as accurate as FiveThirtyEight's** in competitive races (2018-2022): a little worse on
  the last day, better a month or two out.
- **Its chances are not yet as sharp:** log loss 0.33 against FiveThirtyEight's 0.23 to 0.27 on the last day. One size of
  error is used for every race, so close races get ranges that are too wide (84% of results inside the 80% interval).
  Sizing the error by race is the first refinement.
- **Polling misses are shared within a year:** the polls overstated the Democrats by about 5 points of margin across the
  board in 2020 and understated them in 2018. A seat-count forecast has to move the races together, as the presidential
  simulation moves the states.

Four years are four national environments: every figure here should be read as indicative, not settled.

## Step 3: weighting the polls by how much polling there is, and sizing the error by race

Two refinements, each fitted only on the other years, as before.

**The polls' weight now grows with the amount of polling.** Instead of one weight per distance, the race's polling
average gets a floor weight for any average, rising toward a cap as the polling grows (`poll_share` in `backtest.py`).
The cap matters: polls in a year miss together, and more polls do not remove that error. The floor matters too: in 2018,
thin and old averages in West Virginia, Montana and North Dakota still said more than the fundamentals did.

| Competitive races | Last day | 7 days | 30 days | 60 days |
|---|---|---|---|---|
| Miss on the margin, one weight | 5.3 | 5.2 | 5.0 | 5.0 |
| Miss on the margin, by volume | 4.9 | 4.7 | 5.0 | 5.0 |
| Log loss, one weight | 0.298 | 0.293 | 0.290 | 0.256 |
| Log loss, by volume | 0.250 | 0.242 | 0.276 | 0.256 |

Against FiveThirtyEight on the same competitive races (2018-2022), log loss on the last day and a week out:

| | Last day | 7 days |
|---|---|---|
| FiveThirtyEight deluxe | 0.232 | 0.244 |
| FiveThirtyEight classic | 0.263 | 0.272 |
| FiveThirtyEight lite | 0.265 | 0.278 |
| This model, by volume | 0.275 | 0.260 |

So in the final weeks the chances are now about as sharp as FiveThirtyEight's classic and lite versions, which, like this
model, use no expert ratings; its deluxe version, which adds them, stays ahead. A month or two out the gain is small and
the floor and cap move from year to year: four years cannot pin down three numbers at every distance.

**Sizing the error by race did not help, and is not adopted.** Fitting the size of the miss on how far a race is from
even and how much polling it has made close races' ranges too narrow: in competitive races only 42% of results fell
inside the 50% interval on the last day. Most of the error that matters is shared by a year's races (the 2020 polling
miss), not race by race; it belongs in the next step, which moves the races together. The version stays in the code so
the test can be rerun.

The working version is now **+polls by volume**, with one error size for races with polls and one for races without.

## Step 4: starting a presidential year's Senate races from the presidential forecast (tested, not adopted)

The idea: in a presidential year, start each Senate race from The Margin's own forecast of that state's presidential
vote, then model only how far the party's Senate candidate runs ahead of or behind the top of the ticket.
`senate/president_states.py` reruns the presidential back-test exactly as published and keeps its forecast of every state
at every distance for 2020 and 2024 (`president_forecast.csv`); `president_polls.csv` holds the raw presidential polls
for a second variant that uses the state's presidential polling average instead.

Three forms were tried (`backtest.py`): the presidential forecast in place of the state's lean and the generic ballot,
the presidential forecast's difference from those as an extra input, and the presidential forecast taken as it is plus a
ticket-splitting offset by incumbency. None beat the current version in 2020 and 2024:

| Presidential years, all races, miss on the margin | Last day | 7 days | 60 days | 365 days |
|---|---|---|---|---|
| Current (+polls by volume) | 6.5 | 6.6 | 6.4 | 6.8 |
| Starting from The Margin's presidential forecast | 6.7 | 7.0 | 5.9 | 6.7 |
| Starting from the presidential polls | 7.2 | 7.8 | 6.9 | 7.6 |
| Presidential forecast plus a ticket-splitting offset | 6.9 | 7.3 | 6.3 | 7.0 |

Log loss tells the same story. The reason is that the state lean and the generic ballot already carry most of what the
presidential forecast knows about a state; what decides a Senate race beyond that is its candidates. In 2020 and 2024 the
Senate result differed from the same state's presidential result by about 3.4 points of two-party share (about 7 of
margin), and a year out almost all of the error is of this race-by-race kind: removing what a year's races missed by in
common lowers the miss only from 7.0 to 6.8 at 365 days, though from 6.2 to 5.2 on the last day.

What the link is still good for is not accuracy but correlation: a joint simulation of president, Senate and House should
move a state's Senate race with its presidential vote, so that the chance of one party winning all three is right.

## What comes next

- Simulate the races together, with a shared national error, for the chance of each party controlling the Senate.
- Replace the cycle's money totals with money raised by each date (the FEC's quarterly filings).
- The Manifold race markets of 2022 and 2024, tested in the research section only, with no weight in the forecast.
