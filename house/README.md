# The House forecast (in progress)

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
