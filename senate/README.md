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

- Wikipedia, each Senate race's page, the second Trump presidency's opinion-polling page and the 2026 House
  elections page, with their histories (CC BY-SA 4.0); the tables derived from them carry the same licence

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

## Step 5: each candidate's track record (adopted)

`build_data.past_races()` scores every Senate general election of 1978-2024 for how far the Democratic side ran ahead of
what the state's lean and the year's national mood would give, with whether each candidate had won a Senate race in the
state before taken out (the slope on lean and those terms are fitted on 1978-2016 only). `track_records()` gives each
2018-2024 candidate the average of their own last two such races in the state, if they have any: 61 Democrats and 50
Republicans do. The input is the Democrat's record less the Republican's, 0 for a candidate without one.

FiveThirtyEight used a cruder form of this (an incumbent's previous margin, and whether a candidate had held office);
this is a measured figure for each candidate, against what their state and year would have given anyone.

| Competitive races | Last day | 7 days | 60 days | 365 days |
|---|---|---|---|---|
| Log loss, +polls by volume | 0.250 | 0.242 | 0.256 | 0.381 |
| Log loss, + track record | 0.237 | 0.226 | 0.226 | 0.367 |
| Miss on the margin, +polls by volume | 4.9 | 4.7 | 5.0 | 6.3 |
| Miss on the margin, + track record | 4.9 | 4.7 | 5.1 | 6.2 |

- **The chances get sharper at every distance,** in 30 of the 32 year-and-distance cells (all races), and the Brier score
  improves at every distance. The typical miss on the margin barely moves: the record helps most in deciding close races,
  not in the size of misses in lopsided ones.
- **Against FiveThirtyEight (competitive races, 2018-2022),** log loss a week out is now 0.247 against its deluxe 0.244,
  classic 0.272 and lite 0.278; on the last day 0.264 against 0.232, 0.263 and 0.265.
- **The fitted weight is small and steady:** 0.15 to 0.26 of a candidate's past over- or under-performance carries into the
  next race, rising as more recent years are in the fit.
- **The ranges are now slightly narrow across all races** (41% of results inside the 50% interval on the last day, 77%
  inside the 80%), mostly in lopsided ones; in competitive races they are about right (48% and 82%). The joint
  simulation, with its shared national error, will set the ranges again.
- **What it does not yet cover:** House members, governors and other statewide officeholders running for the Senate have
  no record here, because only Senate races are in the data. Two people with the same name, initial and state are taken
  as one (Connie Mack III and IV, Florida).

The working version is now **+track, +polls by volume**.

## Step 6: the races simulated together (adopted)

`python senate/simulate.py` simulates each year's races 40,000 times from the working version and writes
`data/senate/simulation.json`: the Democratic side's seats among the races up, their 80% and 50% ranges, and the chance of
control (seats not up, plus the races left out of the test, which all went one way; a 50-50 tie goes to the party of the
vice president the new Congress had, which a 2028 forecast would take from the presidential simulation instead).

Each race's error is split into a part shared by every race in the year and a part of its own, keeping each race's own
spread as it was. The shared part is drawn from a t distribution with 5 degrees of freedom, as in the presidential
simulation. Its size:

- **is measured on misses made out of sample,** the other years' forecasts from when each was the year left out (the
  test year's own miss is never used). Measured inside the fit it comes out at about half the size (0.5 to 1.3 points of
  two-party share), because the fit bends toward each training year's national mood. Measured by forecasting each
  training year from only the two others it comes out absurdly large (8 to 16), because two years cannot fit the generic
  ballot's weight.
- **never shrinks with distance:** the national mood is no easier to call a year out than a week out, so the shared part
  at a distance is at least what it is nearer. It comes to about 1.6 to 1.7 points of two-party share, about 3.3 to 3.5
  points of margin, close to what the races' misses had in common in 2018-2024 (the 2020 polling miss, the 2018 wave).

| Democratic side's seats among the races up | A year out | 60 days | Last day | Result |
|---|---|---|---|---|
| 2018 | 21 (18 to 23) | 22 (19 to 24) | 21 (19 to 24) | 23 |
| 2020 | 13 (12 to 15) | 16 (14 to 18) | 16 (14 to 18) | 15 |
| 2022 | 14 (13 to 16) | 15 (13 to 17) | 13 (11 to 16) | 15 |
| 2024 | 21 (18 to 23) | 20 (18 to 22) | 20 (17 to 22) | 20 |

(average and 80% range). The result fell inside the 80% range in all four years at every distance but 250 days, where
2018's 23 was just outside. The chance of Democratic control on the last day: 2018 2%, 2020 84%, 2022 51%, 2024 3%;
the Democrats won control in 2020 and 2022.

- **Four elections cannot show that moving the races together is better.** Simulated independently, the seat ranges
  are narrower and, in these four years, scored slightly better (log score of the exact seat count 1.63 against 1.77 on
  the last day), because no year's shared miss was big enough to break them. Moving them together is adopted anyway, as
  in the presidential simulation, because a shared miss like 2020's is a matter of record and an independent simulation
  treats it as impossible to repeat across many races at once.
- Each race's own chance barely changes (log loss 0.145 either way on the last day); a year out it improves slightly
  (0.217 to 0.198), from the t distribution's wider tails.
- **Not yet in the simulation:** a link to the presidential vote in a presidential year, and closer ties between
  similar states. Both need the 2028 presidential simulation's draws; they would widen the seat ranges further in a
  year with a presidential polling miss.

## Step 7: 2026, a year the model never saw

`python senate/test_2026.py` forecasts the 2026 elections with the working version fitted on 2018-2024 only, and writes
`data/senate/2026/test_2026.json`. The 32 races between a Democrat (or Osborn, the Democrats' choice in Nebraska) and a
Republican are in `data/senate/2026/races_2026.csv`, with the vote counts reported after the election (state election
offices via Fox News's results pages, November 26, 2026; not all certified). Idaho, Montana and South Dakota are left
out: no Democrat-side candidate was among the top two, and all three went Republican.

The race polls and the generic-ballot average are RealClearPolling's (kept out of the repository in
`data/senate/2026_rcp/`, which is RealClearPolling's compilation, not ours to republish). Its list is narrower than the
FiveThirtyEight archive the model was fitted on, and its generic-ballot average stands in for the model's own.

| 2026 | A year out | 60 days | 30 days | Last day |
|---|---|---|---|---|
| Races called right (of 32) | 24 | 25 | 25 | 26 |
| Miss on the margin | 12.1 | 10.0 | 8.6 | 7.8 |
| Average miss (negative: Democrats understated) | -10.9 | -8.7 | -7.2 | -6.6 |
| Democratic seats among the 32 (80% range) | 14 (11-16) | 15 (13-18) | 16 (13-20) | 17 (14-21) |
| Chance of Democratic control | 8% | 28% | 46% | 60% |

The Democrats won 22 of the 32 and control of the Senate (56 seats). The six races called wrong on the last day were all
Democratic wins the model had narrowly against them: Iowa, Alaska, South Carolina, Ohio, Kansas and Mississippi.

- **The polls missed together, by a lot.** In the 21 races with polls in RealClearPolling's list, a plain average of each
  race's polls in the last 30 days understated the Democrats by 5.3 points of margin on average. A shared miss of that
  size is about twice the shared error the simulation allows (about 3.4 points of margin), so the result fell outside
  the 80% range for seats, and only 56% of races fell inside their own 80% ranges on the last day.
- **The fundamentals made it worse, not better.** On the same 21 races the model's average miss was 6.3, against the
  polls' 5.3. The generic ballot (Democrats ahead by about 9 on election eve, by 3 a year before) understated the year,
  and the model takes only about two thirds to four fifths of any generic-ballot lead, because 2018-2024 had no wave
  larger than 2018's. 2026's (the Democratic side's average share less each state's lean) was larger than 2018's.
- **A year out the model had no way to see it coming:** it knows nothing of the regular swing against the president's
  party in a midterm, only the generic ballot of the day.

What this does and does not say. One year is one national environment, and the polls' miss was shared, so 2026 is one
draw, not 32. It argues for a larger shared error (2026 can now join the years it is measured on) and for testing a
midterm term on the long record of Senate results since 1978. A presidential year such as 2028 has no midterm swing, so
for 2028 the first lesson is the one that applies.

## Step 8: the national fundamentals (adopted)

Quinn, Brush and Smith's update of the Lewis-Beck and Rice model ("Updating the Fundamentals: Forecasting the 2026
Midterm Election Post-Gallup", *PS: Political Science & Politics*, 2026) forecast, from June 2026's approval, income
growth and the midterm, that the Republicans would lose 8.9 Senate seats; they lost 9. Its forecast was the same a year
out, when this model saw almost nothing coming.

`senate/national.py` rebuilds its inputs for 1948-2026 from public sources (Gallup approval from the American
Presidency Project, real disposable income from the BEA via FRED, and each election's seats and national House vote;
`tools/fetch_fundamentals.py` fetches them through the "Source samples" workflow) and refits its equations
(`national_check.json`). They come out close to the paper's: House seat change = -38.9 + 0.77 approval + 1.39 income
- 28.9 midterm (paper: -38.6, 0.78, 1.39, -29.7); Senate = 2.6 + 0.14 approval + 0.26 income - 2.1 midterm
- 0.65 seats up (paper: 3.7, 0.14, 0.23, -2.9, -0.72); the 2026 Senate forecast -8.8 (paper -8.9).

For the race model the same inputs forecast the national House vote instead of seats, from what was known on each date
(the latest approval; the latest income growth then published, in revised figures; the equation fitted only on the
elections before). `senate/national_test.py` tried it in place of the generic ballot, and averaged half and half with
it:

| All five years (2018-2024 left out in turn, 2026 fitted on 2018-2024) | A year out | 120 days | 30 days | Last day |
|---|---|---|---|---|
| Miss on the margin, generic ballot (before) | 8.2 | 7.9 | 6.7 | 6.5 |
| Fundamentals with income, alone | 8.8 | 7.9 | 7.2 | 6.9 |
| Half generic ballot, half fundamentals with income | 8.4 | 7.8 | 6.5 | 5.9 |
| Approval and midterm only, alone | 7.8 | 7.4 | 6.6 | 6.3 |
| **Half generic ballot, half approval and midterm** | 7.9 | 7.6 | 6.6 | 6.4 |
| Log loss, before | 0.333 | 0.253 | 0.196 | 0.177 |
| **Log loss, half generic ballot, half approval and midterm** | 0.309 | 0.244 | 0.194 | 0.174 |

- **Income is the weak part:** the 2020 stimulus (income up 22% a year) and 2022's inflation (down 7%) threw the
  fundamentals off by about 5 points of the House vote. Approval and the midterm alone hold up better.
- **Half and half, approval and midterm, is adopted** (`+national` in `backtest.py`, now the working version in
  `simulate.py` and `test_2026.py`): it is better than before at every distance across the five years, on both the
  margin and log loss, and it is the plainest choice, with no weight fitted. Choosing it after seeing 2026 is itself
  a choice made on the data; the other forms tried are kept in `national_test.json`.
- **Against FiveThirtyEight (competitive races, 2018-2022),** log loss a week out is now 0.240, against its deluxe
  0.244; on the last day 0.260, against 0.232 (deluxe), 0.263 (classic) and 0.265 (lite).
- **2026:** the miss on the margin on the last day falls from 7.8 to 7.5 and a year out from 12.1 to 10.6; the
  expected Democratic seats among the 32 rise from 17.2 to 17.4 on the last day (14.5 a year out), against the 22 they
  won, and the chance of Democratic control from 61% to 64% (13% a year out). Most of 2026's miss was the polls'.
- **The chance of control in 2018-2024 got slightly worse** (log loss 0.27 against 0.22 on the last day), from 2020
  (78% for the Democrats, who won) and 2022 (45%, who won). Four outcomes; read it as noise either way.
- **The paper's own seat forecast is worth showing beside ours,** as a separate benchmark, as Tipping Point shows its
  academic models: its national seat count was nearer the 2026 result than the total of this model's race forecasts.
- **Approval after Gallup:** for 2026 the inputs use RealClearPolling's average turned into a Gallup equivalent by the
  paper's proxy (in `data/senate/2026_rcp/`, kept out of the repository). Running this in 2028 needs an approval
  average the pipeline can collect itself; Fifty-Two Keys' own list of approval polls is too thin for it so far.

## Step 9: three more ideas from the 2026 papers (none adopted)

`senate/national_ideas.py` tests them on the long national record: every election from 1978 to 2026 forecast from a fit
on 1948 up to the election before it only, in June of the election year and a year out, for the president's party's
share of the House vote (and, as a check, its House and Senate seat changes). The candidates were set before any was
scored (`national_ideas.json`).

| Typical miss, president's party's House vote, points | June, 1978-2026 | June, 2002-2026 | Year out, 1978-2026 | Year out, 2002-2026 |
|---|---|---|---|---|
| **Approval and the midterm (in use)** | **2.7** | **2.1** | **2.7** | **2.1** |
| + income growth (Quinn, Brush and Smith) | 3.5 | 3.2 | 2.9 | 2.4 |
| + inflation (Fair's point) | 3.0 | 2.1 | 3.4 | 2.5 |
| + GDP growth | 3.4 | 3.1 | 2.8 | 2.4 |
| + years in power (Tien and Lewis-Beck's cost of ruling) | 3.4 | 2.1 | 3.1 | 2.1 |
| + inflation + years in power | 3.5 | 2.2 | 3.4 | 2.6 |

- **Nothing beats approval and the midterm alone.** Every economic measure swings wildly in some year (income +22% in
  2020, -7% in 2022; GDP -8 points of vote error in 2020 in June), and the cost of ruling adds nothing a fit can use.
  The seat-change checks agree. Inflation undoes the income model's 2020 and 2022 misses, but approval alone
  never made them, and inflation costs elsewhere.
- **Trusting approval more when it and the generic ballot disagree (Algara et al.)** cannot help here: the national
  error of a blend is about the same at a third, half or two thirds on the fundamentals (1.84, 1.74, 1.72 points across
  2018-2026, all distances), and in 2026 the two agreed (within a point) and were both short. Half and half stays.
- **Tien and Lewis-Beck's own variables** ("Political Economy Forecasts: The 2026 Midterms"), tested afterwards with
  their definitions: their cost of ruling is a count of midterms in a row under the same president or party, not years
  in power, and "seats exposed" is the president's party's House seats above its average. On the vote, the midterm
  count ties approval and the midterm (2.7 points) and seats exposed is worse (3.5); their full equation 5 is worse
  everywhere out of sample (3.8 on the vote, 17.7 House seats against 17.0). Seats exposed does help forecast House
  seat change (16.0 against 17.0 seats, 1978-2026): it is about how votes turn into seats, so it belongs in a House
  seat-count benchmark, not in the race model's national vote.
- **Why the papers find the economy significant and this test does not:** they fit every year at once and report how
  well the equation fits those same years; here each year is forecast only from the years before it. With 39 elections
  and four or five inputs, a term can fit the past and still not help forecast. Income is also fragile to measure:
  for the same months Quinn, Brush and Smith used -0.3% and Tien and Lewis-Beck +2.4%, and Tien and Lewis-Beck's own
  2022 forecast (made out of sample) missed by 35 seats.
- The national input stays as step 8 left it. The one idea left with a real chance is the special elections (Hunt):
  they read the national mood from votes, not from polls or approval.

## Step 10: pulling the seat total toward the national seat model (adopted, a quarter of the way)

`senate/combine_test.py` takes the national seat-change model (Quinn, Brush and Smith's Senate equation without income:
approval, the midterm and seats up, fitted on 1948 up to the election before) and moves every race by one shared
amount so that the simulation's expected seats land part of the way from its own total to the national model's. The
races still decide which seats. Weights of 0, a quarter, a half, three quarters and all were set before scoring.

| | Race model alone | A quarter of the way | Half way |
|---|---|---|---|
| Seat total, typical miss, all five years: a year out / last day | 3.7 / 2.3 | 3.0 / 2.0 | 2.4 / 1.9 |
| Same, 2018-2024 only | 1.6 / 1.2 | 1.1 / 1.3 | 1.2 / 1.6 |
| Race log loss, all five years: a year out / last day | 0.296 / 0.174 | 0.256 / 0.166 | 0.237 / 0.165 |
| Control log loss, all five years: a year out / last day | 0.77 / 0.30 | 0.50 / 0.33 | 0.39 / 0.38 |

- **It helps where the polls and the race model lagged the national mood:** 2018 and 2026. It hurts in 2022, when the
  national model expected the usual midterm loss for the president's party and the Democrats beat it; 2020 and 2024
  hardly change.
- **A quarter of the way is adopted** (`COMBINE` in `simulate.py`, used by `test_2026.py`): over the five years it is
  better than the race model alone at every distance on the seat total, the margins and the races' chances, and costs
  little in 2022. Half way gains more, but mostly from 2026, one year. The chance of control near the election gets
  slightly worse (0.33 against 0.30 on the last day), from 2022.
- **2026 now:** the last day gives the Democrats 18.3 seats of the 32 (80% range 15-22, against the 22 they won), 30 of
  32 races called right and a 77% chance of control; a year out, 15.8 seats and 33%.
- The simulation and 2026 figures in steps 6 and 7 were made before this step; `simulation.json` and `test_2026.json`
  now hold the combined version.

## Step 11: Wikipedia as the poll feed (adopted)

FiveThirtyEight's archive has closed and RealClearPolling's data can be read here but not by the automated runs, so
the forecast needs a source it can collect itself. Wikipedia's pages serve, under CC BY-SA 4.0:

- **Race polls:** each race page's tables of general-election polls (`senate/wiki_polls.py`; built into
  `polls_wikipedia.csv` for 2018-2024 and `2026/wiki_polls_2026.csv` by `senate/wiki_build.py`). A table is read when
  its heading names both nominees (surname, given name or a common nickname, and party, so that Lindsey Graham is not
  taken for Darline Graham); tables of averages are skipped; a poll asked several ways keeps the version with the most
  voters choosing between the two nominees; polls Wikipedia marks with a party are left out, as in training.
- **Approval and the generic ballot:** the median of the aggregators the pages list (`senate/wiki_national.py`), read
  from the pages' history for past dates. Approval becomes a Gallup equivalent by Gallup's 2025 offset from that median:
  3.35 points below (spread 2.0, 22 half-monthly readings); for June 2026 that gives 34.95, against the paper's 34.5.
  The generic-ballot median tracks RealClearPolling's within about 0.3 points.

| Coverage | Wikipedia | FiveThirtyEight / RealClearPolling |
|---|---|---|
| 2018-2024 polls of the nominees (one per poll and population) | 634, 919, 685, 997 | 821, 925, 706, 1,001 questions |
| 2026 polls / races with polls in the last 30 days | 651, 346 without a party mark / 22 | 471 / 19 (RealClearPolling) |

| Back-test, leave one year out, miss on the margin (log loss) | A year out | 60 days | Last day |
|---|---|---|---|
| Trained on FiveThirtyEight's polls | 7.09 (0.229) | 6.19 (0.135) | 6.11 (0.144) |
| Trained on Wikipedia's polls | 7.03 (0.224) | 6.23 (0.134) | 5.98 (0.146) |

| 2026, out of sample, last day | Races called | Miss on the margin | Log loss | Democratic seats (80% range) | Control |
|---|---|---|---|---|---|
| FiveThirtyEight training, RealClearPolling inputs | 30 | 6.46 | 0.252 | 18.3 (15-22) | 77% |
| Wikipedia training and inputs | 30 | 6.31 | 0.235 | 18.7 (15-22) | 82% |

Wikipedia is now the default everywhere (`backtest.py`, `simulate.py`, `test_2026.py`; `SENATE_TRAIN_POLLS=538` and
`SENATE_POLLS=rcp` bring back the earlier sources, whose 2026 run is kept in `2026/test_2026_rcp.json`). Figures in
steps 2-10 were made with FiveThirtyEight's polls. Gaps that remain: California's 2024 pages were not fetched under
the name used, and the 2018 count is lower mostly because FiveThirtyEight counted each version of a poll.

## Step 12: candidates and results from Wikipedia

`senate/wiki_candidates.py` reads each race page's summary box: the nominees and their parties, their votes once
counted, and who held the seat. The Democratic side is the Democrat, or an independent the Democrats back
(`DEM_ALIGNED` in `build_data.py`, by hand) when one is running, as King in Maine. Checked against the 167 races of
2018-2026 already in the data, it names the same two nominees and the same incumbency in 165; the other two are
California pages filed under a name the fetch now also tries. The check also found an error in `races_2026.csv`:
South Carolina's Darline Graham, appointed after Lindsey Graham's death, ran as the incumbent; the 2026 figures above
are rerun with that corrected (last day: 30 of 32 called, log loss 0.240, 18.7 seats, 82% control).

## Step 13: money raised by each date (tested, not adopted)

`tools/fetch_fec_reports.py` (run by the "Source samples" workflow with the free FEC key kept as a repository secret)
fetched every report filed by the 334 nominees' campaign committees for 2018-2026: 4,179 reports, each dated by the
day the FEC received it. `senate/fec_money.py` turns them into `data/senate/money_reports.csv` and gives what each side
had raised by any date, so a forecast sees only the reports filed by then. On election day a side's total by that
measure is a median 87% of the cycle total used before. The feature is the log of the ratio of the two sides' money
(each with $100,000 added); a side with no committee found counts as even (2026: Hinson in Iowa and Graham Nordone in
South Carolina were not found in the FEC's candidate search).

Added to the working version, its weight is positive and steady in every left-out year (about 0.2 a year out, 0.6 to
1.0 in the last two months). Against the working version:

| | margin miss, all races | log loss, all races | margin miss, within 10 points |
|---|---|---|---|
| 2018-2024 left-out years, 120 days | 7.13 to 6.72 | 0.200 to 0.206 | 6.10 to 5.83 |
| 2018-2024, 60 days | 6.24 to 5.93 | 0.142 to 0.140 | 4.98 to 4.78 |
| 2018-2024, last day | 5.96 to 5.91 | 0.145 to 0.146 | 4.86 to 4.84 |
| 2026, 60 days | 7.49 to 7.81 | 0.368 to 0.388 | 7.40 to 8.16 |
| 2026, last day | 6.32 to 6.49 | 0.240 to 0.240 | 5.97 to 6.35 |

Money narrows the margin misses in the years it was fitted on, most in the summer, but the chances it gives are no
better (log loss worse at 120, 30, 14, 7 and 1 days), and in 2026, the year it never saw, its margin misses are wider at
every distance but a year out. Not adopted. The table and the code stay, and the test is run again once 2026 is a fitting year.

## Step 14: appointed incumbents (tested, not adopted)

A senator appointed to a seat and running for it for the first time is counted as an incumbent like any other. Nine
such races are entered by hand in `APPOINTED` in `backtest.py`: Smith and Hyde-Smith (2018), McSally and Loeffler
(2020), Padilla's two races (2022), Ricketts (2024), and Moody, Husted and Darline Graham (2026). Added as one term
(+1 for an appointed Democrat, -1 for an appointed Republican), its weight comes out at 1 to 2.7 points of the
two-party vote against the appointed incumbent in every left-out year, so they did do worse than elected ones.

But nine races are too few for it to change much. In 2018-2024 the margin miss and log loss are within 0.05 of the
working version's at every distance, slightly worse at most; it helps Padilla's races and hurts Smith's and Ricketts'.
In 2026 on the last day it moves the three appointed Republicans 1 to 1.2 points toward the Democrats (South Carolina
from R+3.5 to R+2.3, against a Democratic win by 4.6), leaves the calls unchanged at 30 of 32 and the average miss at
5.3. Not adopted. South Carolina's miss comes mostly from the step back from its polls (R+0.7 on their own) toward the
state's lean, not from incumbency.

## Step 15: 2026 as a fitting year (adopted for the live forecast)

`senate/with_2026.py` adds 2026's 32 races to the four earlier years and asks two things.

What the fit learns: the weight on the national environment rises from about 0.65 to about 1.0 at every distance (a
point of national swing moves every race a full point, where the four years had damped it), and the incumbency terms
shrink. The error the races share, measured on every year's out-of-sample misses, grows from 1.6 points of two-party
share to 2.0 on the last day and 2.4 a year out: 2026's races missed together by more than any earlier year's.

What it does to the other years, each left out and forecast from the rest with and without 2026:

| | margin miss, 2018-2024 races | log loss | chance of control, log loss |
|---|---|---|---|
| a year out | 7.04 to 7.49 | 0.223 to 0.179 | 0.40 to 0.37 |
| 60 days | 6.24 to 6.77 | 0.142 to 0.137 | 0.17 to 0.23 |
| last day | 5.96 to 6.11 | 0.145 to 0.137 | 0.30 to 0.34 |

The margins are a little worse (most in 2020, a year the polls overstated the Democrats, the opposite of 2026), the
race chances better at every distance, and the chance of control less sure in years whose outcome the narrower range
already covered. With 2026 in the fit, every 2018-2024 seat count stays inside its 80% range. Fitted on 2018-2024
only, 2026's actual count fell outside the range until the last week.

One year cannot settle it either way. A forecast that leaves out the latest and largest shared miss would be too sure
of itself in 2028, so the live forecast is fitted on all five years (`LIVE_YEARS` in `simulate.py`), with the shared
error from all five. The back-tests keep leaving each year out.

## Step 16: the link to the presidential forecast (adopted for 2028)

In a presidential year a state's Senate race and its presidential vote miss together. Measured on 2020 and 2024 (the
Senate forecast of each race, each year left out, against The Margin's own presidential forecast of the same state at
the same distance): within a year, a state's Senate miss moves 0.34 to 0.63 points with each point of its presidential
miss, around 0.5 at every distance (correlation 0.12 to 0.45). Both years' Senate and presidential misses leaned the same
way (2020: Senate 3.2 points too Democratic on the last day, presidential 1.6; 2024: 1.5 and 1.0).

So in 2028 the Senate races are simulated inside the presidential forecast's own simulated elections: each race moves
half a point with each point its state's presidential vote moves in that election, and the rest of its error (the part
the races share and its own) is drawn as before, sized so that each race's whole spread is what the fit gives it. A 50-50
Senate goes to the party of the vice president elected in the same simulated election; an Electoral College tie counts
as half.

## The live 2028 forecast (backend only)

`senate/live.py`, run every hour by `.github/workflows/senate.yml` after the presidential forecast's run, writes
`data/senate/2028/forecast.json` (the chance of control, the caucus range, each race), `history.csv` (a line a day)
and `sources.json` (the page versions read). Nothing is on the site. Each run:

1. reads Wikipedia's 2028 Senate page: the 35 seats up (34 of Class 3 and Tennessee's special), who holds each, whether
   they are running, the declared candidates, and the chamber as it stands (56 in the Democratic caucus, 40 of them not
   up); each race's own page for its nominees and polls once chosen; the approval polls; the generic ballot once Wikipedia
   has a page for it;
2. builds each race's inputs as the back-test did; polls count once the race's page names both nominees, and until then
   the race runs on its fundamentals. A senator whose plans are not known counts as running with the share of
   incumbents who ran again in 2018-2026 (79%);
3. applies the fitted pieces in `data/senate/2028/model.json`, made by `senate/live_fit.py` from 2018-2026 (step 15),
   at the nearest distance tested at or beyond the day. More than a year out, the shared error keeps growing at the rate
   it grows within the year;
4. pulls the expected caucus a quarter of the way to the national seat-change model;
5. simulates the races inside the presidential forecast's 40,000 elections, drawn again from its published states with
   its own seed (step 16); the draw reproduces the published presidential chance to within rounding.

The fit needs the raw sources kept out of the repository, so `live_fit.py` is run by hand when the training data change,
and its output committed; the hourly run only applies it. `data/senate/past_races.csv` (1978-2026, from the MIT
Election Lab's returns and the 2026 results) gives the candidates' records.

First run, November 27, 2026, 711 days out: Democrats 99% to control the Senate, a caucus of about 58 (80% range 54-62),
with the national environment from Trump's approval alone (about 36% approve, a Democratic House vote of 52.2%). The
Democrats hold 56 seats and only 16 of them are up, so losing control would take a net loss of six.

## The 2026 academic forecasts, for reference

`data/senate/2026/academic_forecasts_2026.csv` holds the forecasts in the *PS: Political Science & Politics* special
issue on the 2026 midterms (Kenny and Leiter's introduction, Tables 1-3), turned into Democratic seats where a paper
gave Republican ones. Against the result as reported on November 26 (Democrats 259 House seats with three undecided,
a 56-seat Senate caucus, about 57 percent of the two-party House vote): Quinn, Brush and Smith were closest on both
chambers (258 and 56); Tien and Lewis-Beck next (Senate 54 and 53; House 249 with Cost of Ruling); the other House forecasts were 18 to
29 seats short, except Jonaitis et al., 33 over. Of those giving chances for both chambers, Quinlan and Lewis-Beck (78% House, 66% Senate) and Kalshi
(90%, 59%) scored best. The models built on approval and the midterm did best; those leaning on the generic ballot or
polls understated the Democrats, as this model's race polls did. One election cannot rank models: Quinn, Brush and
Smith's own record misses the Senate by about 3 seats in a typical year.

For comparison, this model (working version, Wikipedia polls, South Carolina corrected) gave the Democrats about 51
Senate seats and a 63% chance of control 60 days out, and about 53 seats and 82% on the last day.

## What comes next

- Special-election swings as an early national signal (Hunt), tested on 2018-2026 and the record since 2013.
- An approval average the pipeline collects itself, to replace Gallup in the national fundamentals.
- The national seat-change model as a benchmark beside the Senate and House forecasts.
- Records from House and statewide races, for candidates who have run for those offices.
- Money by date again once 2026 is a fitting year (step 13), and the reports of the two 2026 nominees not yet found.
- The Manifold race markets of 2022 and 2024, tested in the research section only, with no weight in the forecast.
