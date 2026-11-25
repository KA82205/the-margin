# The Margin

A forecast of the 2028 presidential election built the traditional way: polling averages, a fundamentals prior, state
leans and betting markets, run through a simulation of the Electoral College. It is
back-tested on 2008 to 2024. The logo is a plus-or-minus sign: `docs/logo.svg`.

The Senate and the House are planned next, on the same design.

## Where it stands (November 23, 2026)

| | |
|---|---|
| Democrats win the Electoral College | 60% (model alone 58%; betting markets 67%) |
| Electoral votes, average | 283 to 255; four runs in five give Democrats 211 to 360 |
| National vote | Democrats 51.4% of the two-party vote, give or take 2.9 |
| Democrats win the most votes | 71% |
| Tipping-point state | Pennsylvania |

The election is 715 days away and neither party has a nominee. Read it as a lean. The page carries the current
numbers; this table is the first day's.

## The site

One self-contained page, `docs/index.html`, with five tabs: **Forecast** (the map, the forecast day by day, the national
margin, the closest states), **States** (a profile of every state and district: how it has voted since 1976, its lean
against the nation, how its projection is built, its polls, and how often it decides the election; `#states/PA` opens
one directly), **Model** (what goes in, why each weight, how the range narrows, sources and limits),
**Back-tests** (2008-2024 against the results, calibration, every distance from the election) and **Research** (a
notebook of questions about elections that stands apart from the forecast: how good expert ratings are, how far off the
polls have been, whether they miss everywhere at once, the Electoral College's tilt, approval and the vote, which states
are moving, and the primaries). Section headings share one device: a dark band across the
whole screen with a blue-to-red stripe under it, each color as wide as its share of the 538 electoral votes on the map. To add a contact link, set `CONTACT` at the top of `make_page.py`.

## The daily update

`.github/workflows/update.yml` runs `python update.py` twice a morning, after the Tipping Point Nowcast's own runs. It

1. fetches the Nowcast's file (head-to-head polls, state forecasts, presidential approval among adults),
2. reads the party odds from electionbettingodds.com (`PresidentialParty2028.html`: the Democratic and Republican
   percentages, taken as a two-way chance),
3. sets today's date, approval and odds in `data/inputs.json`,
4. reruns the forecast, adds the day to `data/history.csv` (one row a day) and rebuilds the page,
5. commits the changed files, which republishes the site.

On a new day the previous day's inputs are kept as `data/prev_inputs.json` and `data/prev_nowcast.js`. The page's "What
moved since yesterday" box comes from them: yesterday's inputs are swapped for today's one at a time (polls, approval,
markets, then the state models and the date) and the chance is recomputed at each step. A poll in the Nowcast's feed that
names a state is filed under that state; so far the feed has national polls only.

Units: the scripts work in points of the two-party vote share. The page shows every miss in points of margin, which is
twice that (a typical state miss of 1.9 points of share is 3.8 points of margin).

The Fifty-Two Keys count (`keys`, `keys_sd` in `data/inputs.json`) is read each day from that site's own feed,
`https://ka82205.github.io/fifty-two-keys/keys.json`, which is rebuilt every week: the share of keys in the Republicans'
favor if every open key lands the way it leans, and the spread of its run ahead. If the feed cannot be read the last
count is kept and the run only warns. The daily change is split five ways, the keys among them. If the Nowcast cannot be fetched the forecast is still rerun for the day on the previous copy and the run is
marked failed. If the odds cannot be read the last price is kept, with the date it was read, and the run only warns.

## Run it

```
python prep.py         # builds data/ from the downloaded sources in raw/
python backtest.py     # the back-test, 2008-2024; writes data/backtest.csv
python checks.py       # ratings test, every setting changed in turn, calibration (a few minutes)
python research.py     # polling error by distance from the election, for the Research tab
python run_2028.py     # the forecast for the date in data/inputs.json; writes data/forecast_2028.json, data/history.csv
python update.py       # the daily update: fetch, run_2028, make_page (--offline to skip the fetch)
python make_page.py    # docs/index.html
```

Needs numpy and pandas. `prep.py` expects the source files listed below in `raw/`; the cleaned copies it writes to
`data/` are included, so everything after `prep.py` runs as is. (`prep.py` also reads the Fifty-Two Keys and Tipping Point folders for results.)

## The model

Every number is the Democratic share of the two-party vote. All settings are at the top of `model.py`. They were written
down before the back-test was scored and none is fitted to the five elections it is tested on.

1. **National polling average.** A poll's weight halves every (days to the election / 5) days, held between 7 and 30;
   grows with the square root of its sample; is halved for each newer poll from the same pollster; and is 1.0, 0.9 or 0.7
   for likely voters, registered voters or adults.
2. **Fundamentals** (`fundamentals.py`). The average of two equations, each fitted only on earlier elections: the
   president's June net approval with a first-term term (after Abramowitz; second-quarter growth is left out because of
   2020), and the Fifty-Two Keys count turned into a vote share.
3. **National number.** Polls and fundamentals are averaged by how reliable each has been: the polling average's error at
   that many days out against the fundamentals' error. On the last day polls carry about 70%.
4. **States.** A state starts at the national number plus its lean (three quarters of how it voted relative to the nation
   last time, one quarter the time before). Its own polls, each moved by the change in the national average since it was
   taken, pull it away from that start as if the start were 1.5 fresh polls.
5. **Uncertainty.** A national error with fat tails, a regional error and a state error. Their sizes come from how far
   FiveThirtyEight's published polling averages of 1972-2016 stood from the result at each distance from the election,
   and from how far states have landed from their leans, using only elections before the one being forecast.
6. **Simulation.** 40,000 elections; Maine and Nebraska split by district; a 269-269 tie counts as half a win.
7. **Betting markets.** The market's chance is pooled with the model's at 25%, on the log-odds scale. The markets are one
   of four sources (polls, fundamentals, state models, markets), so they get one share in four; not more, because prices
   already lean on the same polls, the 2028 markets are thinly traded, and this weight is not back-tested yet. At 0% the
   Democrats are at 55%, at 70% they are at 64%.
8. **Expert ratings are left out.** They were tested (see below) and did not help.

For 2028 two more things apply. Half of each state's starting point is the Tipping Point Nowcast's forecast for that state
(two published state-level models). And the fundamentals carry extra error for two years of drift: ten points of net
approval and the spread of the Fifty-Two Keys run ahead.

## Back-test, 2008-2024

Run as of 120, 90, 60, 30, 14, 7 and 1 days before each election, with only the polls that had finished.

| Election | Favored on the last day | Won | National margin: forecast, result, off by | Democratic electoral votes: forecast, range, result |
|---|---|---|---|---|
| 2008 | Democrats, 98 in 100 | Democrats | D+9.1, D+7.5, 1.6 | 358, 300 to 410, 365 |
| 2012 | Democrats, 79 in 100 | Democrats | D+3.9, D+3.8, 0.0 | 301, 250 to 352, 332 |
| 2016 | Democrats, 77 in 100 | Republicans (missed) | D+4.4, D+2.3, 2.1 | 303, 245 to 357, 232 (outside) |
| 2020 | Democrats, 93 in 100 | Democrats | D+6.8, D+4.5, 2.2 | 336, 275 to 394, 306 |
| 2024 | Republicans, 51 in 100 | Republicans | D+1.2, R+1.5, 2.7 | 268, 225 to 323, 226 |

- Last day: favored the winner in 4 of 5; typical state miss 1.9 points; 264 of 280 states and districts called; 91% of
  state results inside ranges meant to hold 80%, so the ranges are a little wide.
- The national margin was off by 1.7 points on average, every time in the Democrats' favor, as the polls were.
- The electoral-vote forecast is the middle simulation and the range holds four in five. The result was inside the range
  in every year but 2016.
- 2024 was a coin flip: the middle simulation had the Democrats on 268, two short, so the Republicans won 51 in 100. The
  close states fell together and the Democrats finished on 226, at the bottom of the range.

### Checks on the choices (`checks.py`)

- **Expert ratings.** Cook Political Report's final ratings (2008-2020) and Sabato's Crystal Ball (2008-2024) were added to
  the last-day forecasts, each rating pointing to a share three points a step from a toss-up. At 15% the model called 264
  of 280 states and districts, the same as without them; the typical miss in close states went from 1.39 to 1.45 points.
  Heavier weights were worse (at 100%: 263 called, 2.26). In the closest states the raters mostly say toss-up. So ratings
  are not used for the presidency. The date of the Sabato ratings is not given in the file they come from.
- **Every other setting, changed one at a time** (the weight of a state's starting point, the half-life, the cut for repeat
  polls, the lean, the regional share, the tails): the typical state miss on the last day stayed between 1.84 and 1.96
  points and the count of calls between 264 and 266 of 280. Nothing here was tuned.
- **Are the chances honest?** Last-day state forecasts grouped by the chance given to the favorite: said 56%, won 47% (17
  forecasts); said 67%, won 85% (20); said 83%, won 88% (34); said 96%, won 100% (64); said 99.8%, won 100% (145). The
  model is a little less sure than it needs to be.

- **The state-level models' share of a state's starting point** (`state_model_check.py`). For 2028 half of each
  state's starting point is the Tipping Point Nowcast's forecast of that state, which averages two state-level models
  (state approval and economy, after Enns and colleagues; long-range polls, after DeSart). Tipping Point's record of
  those models for 2008 to 2024 is in `data/state_models.csv`: the forecasts the authors published for 2020 and 2024,
  and for 2008 to 2016 each model refitted on the elections before. With every state poll taken away, the starting
  point missed the final margin by 4.67 points with no state model, 4.00 at half, 3.98 at 60%, 4.00 at 80% and 4.12
  with the state models alone (close states: 3.90, 3.32, 3.33, 3.40, 3.56). Half to four fifths is flat, so half stays.
  The approval model alone was best near 40% (4.20) and worse past half (5.18 alone; its 2020 forecast was too
  Democratic), so the average of the two is used. Using only where the models place a state against the nation, not
  their national level, was worse (4.41 at best). With polls in, the gain shrinks (last day: 3.75 to 3.66), because
  polls make up 55% of a close state's projection at 120 days and 80% on the last day. At 60% today's 2028 chance
  would be 62.1% and not 62.3%.
- **A primary equation.** Helmut Norpoth's Primary Model reads November from the early primaries. A third fundamentals
  equation was tried in that spirit: the party in office's candidate's share in New Hampshire less the challenger's, with
  first term, fitted on earlier elections and averaged with the other two (`fundamentals.PRIMARY`). In the back-test the
  national miss fell at every distance (last day: 1.72 to 1.47 points of margin; 120 days: 2.04 to 1.68), with no change
  in state calls or in the calibration score. But that rests on five elections, was better in three of them and worse in
  two (2012, 2024), and the gain is mostly 2008. Over the 13 elections since 1976 the fundamentals alone were worse with
  the primary equation than without it (a typical miss of 2.7 points of share against 2.0, better in 3 of 13; in 2020 it
  put Trump four points too high). So it is not used. The Research tab has the study.

### What the back-test does not cover

- **Betting odds.** They are in the 2028 forecast and not in the back-test yet. Election-eve odds for 2008-2024 still have
  to be collected from sources that can be checked.
- **The Fifty-Two Keys count** for a past year uses that year's final data. Most of it is known by late summer, so the
  early snapshots see slightly more than they could have.
- **The Tipping Point state forecasts** are in the 2028 forecast and not in the main back-test above, which still runs
  on the national number and each state's lean alone. They were tested on their own (`state_model_check.py`, below).
- **Pollster quality and house effects** are not modelled. Every pollster counts the same apart from sample and recency.

## Sources

| Input | Source |
|---|---|
| Polls, 2008, 2012, 2016 | The Economist, `us-potus-model` (`data/all_polls_2008.csv`, `all_polls_2012.csv`, `all_polls.csv`) |
| Polls, 2020, 2024 | FiveThirtyEight `president_polls_historical.csv`, from the archive copy in `jcervas/Data` |
| Polling averages, 1972-2016 | FiveThirtyEight `data/polls/pres_pollaverages_1968-2016.csv` |
| Results and electoral votes | The Fifty-Two Keys data (state results 1952-2020) and official 2024 counts |
| June approval, 1948-2016 | The Economist, `abramowitz_data.csv`; 2020 and 2024 from Gallup |
| Regions | The Economist, `state_region_crosswalk.csv` |
| Expert ratings | Cook Political Report ratings 1988-2020 and Sabato's Crystal Ball ratings 2004-2024, from public course data (`cpr_ratings.csv`, `sabato_crystal_ball_ratings.csv`) |
| 2028 head-to-head polls, state forecasts and approval | Tipping Point Nowcast, fetched daily (approval is its pooled average among adults over the last 30 days) |
| Betting odds | electionbettingodds.com, party to win the presidency, read daily |
| Map | us-atlas 3.0.1 (ISC), Census cartographic boundaries |

Polls sponsored by a party are left out of 2020 and 2024. For 2024, Biden-Trump polls are used until July 20 and
Harris-Trump polls from July 21. The source's 2020 figure for Maine's 2nd district is on the wrong side and is corrected.
