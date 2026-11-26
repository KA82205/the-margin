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
