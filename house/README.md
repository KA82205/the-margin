# The House forecast

A forecast of every House race and of the seats each party wins, built the way the Senate forecast is (`senate/`), on
the 435 districts as they are drawn when the forecast is made.

## The data (step 1)

`python tools/fetch_house.py` (run on GitHub's servers by the samples workflow) fetches the raw sources, kept out of the
repository; `python house/build_data.py <folder>` makes `data/house/training.csv`, one row for every district in every
election 2012-2024:

| Column | From |
|---|---|
| The two parties' votes, the winner | FiveThirtyEight's results by candidate (CC BY 4.0). A candidate on several lines counts once; a ranked-choice race counts its last round; a runoff decides the winner |
| The district's lean on the lines in use | Wikipedia's page of each election (CC BY-SA): Cook's PVI as published before the election. Where the page notes the PVI predates the map (2024's redrawn states), it is marked stale |
| Members on the November ballot | The same pages: Wikipedia's account of each seat, and the members' names matched to the candidates |
| Money | The FEC's summary of each candidate's money (public domain), matched by name, state, district and party |

Checks: every year's seats won by each party match the official results (Democrats 201, 188, 194, 235, 222, 213, 215);
every member Wikipedia says ran again is on the ballot in the table, and none it says left.

Where Cook's published lean is missing or stale, and to test Cook's present method on 2018 and 2020,
`tools/house_leans.py` works out the lean from The Downballot's presidential results by district (free to use with
credit and a link; its spreadsheets are not copied into the repository, only the one number a district), into
`data/house/leans_alt.csv`.

## What the first back-tests found (step 2)

`python house/backtest.py`: each election placed from the others, given that year's national vote.

- The lean alone misses a typical contested race by 3.7 points; members on the ballot bring it to 3.2. A member is worth
  about 4 to 7 points to their party in 2012-2016 and about 2 to 3 since 2018: the House has become national, so the
  forecast is fitted on 2018 onward.
- A district's last result adds nothing once its lean and its member are in.
- Money over the whole cycle helps a little, mostly in close races; the fair test (money as it stood on each day, from
  each candidate's FEC reports: `tools/fetch_house_money.py`, `house/money.py`) is step 3.
- Even given the year's level, a map that moves evenly with the nation misses seats: 2018's Democrats won about 20 more
  than it gives them, their gains bunched in competitive seats.

`python house/simulate.py`: the back-test as a forecast, at each distance from election day, every seat simulated
together, the national level from the Senate model's national mood.

## Money, tested the fair way (step 3)

`tools/fetch_house_money.py` fetched every FEC report of both parties' candidates in each contested race, 2012-2024
(about 70,000 reports), and the FEC's links from committees to candidates; `house/money.py` adds up each candidate's money
in the reports the FEC had received by each distance from election day (`data/house/money_by_date.csv`).

`python house/simulate.py cook75 money`: with money as it stood on each day, the forecasts of 2018-2024 barely move: the
seat count's typical miss falls by half a seat at some distances and not at others, the races called and the chances
stay the same. Money is left out of the forecast, as in the Senate, and is to be shown beside the races.

The leans of 2018 and 2020 worked out the way Cook has since 2022 (three parts the last presidential election, one part
the one before) place the races better than the even split Cook published then (Brier 0.032 against 0.035, eight more
races called), and they are the leans the live forecast reads, so the fit uses them.

## The back-test as a forecast (step 4)

`python house/simulate.py cook75`, 2018-2024, each election from the other three:

| Distance | Seat count's typical miss | Races called | Seats inside the 80% range |
|---|---|---|---|
| 365 days | 9.3 | 1,533 of 1,599 | 4 of 4 |
| 120 days | 11.3 | 1,531 | 4 of 4 |
| 30 days | 8.3 | 1,534 | 4 of 4 |
| Last day | 10.8 | 1,531 | 4 of 4 |

The misses come from the national level (2020 too Democratic, 2022 too Republican) and from the seats' spread: given the
right level, the Democrats beat the forecast in toss-up races by half a point to a point in each of the four years, and
won 6 to 12 more seats than the forecast gave them in three of them. That is not built in; the range holds it.

## 2026, forecast without having seen it (step 5)

`python house/after_election.py --year 2026 --pages FILE --test --save` reads 2026 from Wikipedia (the overview, the
states' pages) and forecasts it from 2018-2024 alone, scored on the winners, since on November 28, 2026 Wikipedia had vote
shares for only 227 of the 417 contested districts. Democrats won 260 seats (two Louisiana runoffs to come); the forecast
expected 224 a year out and 236 on the last day, outside its 80% range at every distance. The districts did not miss:
given the national House vote (57.2% for the Democrats), the equation gives 259 seats. The national mood did, pointing to
54.1% on the last day. Its miss of 2026 is now part of the shared error (house/fit.py measures the mood's misses on every
year it was read), which widens the 2028 ranges.

## The live forecast (step 6)

`house/fit.py` writes `data/house/model.json` (the weights, the gap, the errors at each distance, the members' rates, the
redraw spreads) and `data/house/backtest.json`. `house/live.py`, run every hour after the Senate forecast by
`.github/workflows/house.yml`, reads Wikipedia's overview of the coming election and writes `data/house/<year>/` and
`docs/api/house.json`, which the site's House tab reads. Its docstring lists every case it handles on its own: members who
have not said whether they run, primaries, open and vacant seats, new maps and stale leans, and the link to the
presidential simulations. `house/after_election.py`, run every week by `.github/workflows/house-after.yml`, adds each
election to the training table once its results settle and Wikipedia has them all, then refits the model.

## District polls (step 7)

`house/polls.py` averages each district's polls of its two nominees at each distance from election day, as the
presidential model weighs polls, partisan ones left out (`data/house/polls_by_date.csv`): FiveThirtyEight's House polls
for 2018-2024 (`tools/fetch_house_polls.py` fetches the archived file), Wikipedia's pages from 2026 on. They are blended in
as the Senate's race polls are, with the share fitted at each distance (`house/fit.py`). In the back-test, 2018-2024, the
last day's Brier score fell from 0.032 to 0.029 and the seat count's typical miss from 10.8 to 9.8 seats; in 2026 the
last day's forecast moved from 236 to 238 seats and called two more races. The live forecast reads a district's polls
once the overview names its two nominees, and the nominees also settle whether the member is on the ballot.

Tests: `python tests/test_house.py`.
