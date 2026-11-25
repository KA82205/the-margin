# Keeping the three sites running

This covers The Margin, Fifty-Two Keys and Tipping Point. Nothing here needs a computer of yours to be on, and nothing in
the normal course needs anyone to run a script.

## What runs, and what starts it

| Site | Workflow | What it reads | What starts it |
|---|---|---|---|
| Tipping Point | `Update data and deploy site` | approval polls, national polls, the economy (FRED), state approval | the schedule (minute 17 of each hour), a push, a run started by hand |
| Fifty-Two Keys | `Update` | approval polls on every run; the economy (FRED) and the forecasters' survey when a release could be out and on the day's first run | the schedule (minute 7), a run started by hand |
| The Margin | `Forecast` | the Tipping Point Nowcast, the Fifty-Two Keys feed, betting odds, state polls | the schedule (minute 37), a notification from either of the other two, a run started by hand |

Each run reads its sources, compares them with what the last result was made from, and stops there if nothing differs. Only
a run that found something new recalculates, saves, archives and deploys. The first run of each day always goes through.

The order is one-way: Tipping Point and Fifty-Two Keys never read The Margin, and The Margin never notifies anyone. A
notification that arrives when nothing has changed ends as a run with nothing new.

**GitHub decides when a scheduled run starts.** A schedule is a request, not a promise: runs can start late or be skipped
when GitHub is busy. On November 25, 2026, in the four hours after the hourly schedules went in, none of the three
repositories had a scheduled run start. Read the real record at any time under each repository's Actions tab: runs marked
`schedule` are the ones GitHub started by itself.

## Secrets

Two secrets, both optional, both set under each repository's Settings, Secrets and variables, Actions. Never put either in
a file, a commit, a message or a chat.

**`FRED_API_KEY`** (Fifty-Two Keys; Tipping Point if it has one). A free key from fred.stlouisfed.org, My Account, API
Keys. Without it FRED's download links do not answer GitHub's servers and the economic figures are not refreshed; the run
says so and ends as failed.

**`DISPATCH_TOKEN`** (Fifty-Two Keys and Tipping Point). Lets a site tell The Margin the moment it has published something
new. It is in Fifty-Two Keys. **It is not in Tipping Point**: that site's log says "No DISPATCH_TOKEN secret" on each run.
To add it:

1. GitHub, your picture (top right), Settings, Developer settings, Personal access tokens, Fine-grained tokens, Generate
   new token.
2. Name: `the-margin dispatch`. Expiration: one year is the longest sensible choice; note the date.
3. Repository access: Only select repositories, and choose `the-margin` alone.
4. Permissions, Repository permissions: Contents, Read and write. Nothing else. (GitHub's notification endpoint asks for
   this permission; the token can do nothing outside `the-margin`.)
5. Generate, copy the token, and paste it once into `tipping-point`, Settings, Secrets and variables, Actions, New repository
   secret, named `DISPATCH_TOKEN`. The same token can be the secret in `fifty-two-keys`.

When it expires the two sites carry on and The Margin finds their changes at its own next run; the log line changes to a
warning that The Margin could not be told. To renew: make a new token the same way, replace the secret in both
repositories, delete the old token. To revoke at once: delete the token on the same GitHub page.

Without the token nothing breaks. The Margin's own scheduled run is the fallback.

## When a run ends as failed

A failed run means "somebody should look", not "the site is down". The page always shows the last good figures.

| The log says | What it means | What to do |
|---|---|---|
| A figure was held back | A new figure was outside its believable range or jumped too far. It was not used | Look at the series at its source. If it is real (a shock like spring 2020), start the workflow by hand with the series name in the `trust` box. If it is wrong, do nothing: the next good figure replaces it |
| Held: a key's evidence is late or in dispute | A key should have been callable by now and its evidence is missing, or an entry and the rule disagree | `KEYS.md` says what each key needs. The key keeps its chance and is never counted as no |
| Not read for N days | A source has not answered | Usually passes. If it lasts, check whether the source moved |
| A newer survey should be out and has not been read | The forecasters' survey was not reached, or its table changed shape | Find the line starting `The outlook:` in the log. If the table changed, `outlook.py` needs to learn the new layout; until then the older outlook is used and labelled with its date |
| Stale input (The Margin) | The Nowcast, the Keys feed, the odds or the state polls have not been read for a day or two | Check that the other site's page is up; the last copy is used meanwhile |
| The repository changed while this run was working | Two runs overlapped. The later one's result was dropped | Nothing: the next run starts from the new state |

To run any site again by hand: its repository, Actions, the workflow, Run workflow. Ticking `check` makes the run behave as
the hourly one does (stop if nothing is new); leaving it unticked runs everything.

## What is still done by hand, and when

| What | When | Where |
|---|---|---|
| House and Senate seats when a new Congress meets | Every two years; next in January 2029 | `fifty-two-keys/data/congress_seats.csv`, one line |
| The third-candidate, delegate and New Hampshire keys (E03 to E07) | Once each, in 2028, as each is settled | `fifty-two-keys/data/outlook.json`, the `settled` block, and `data/nh_primaries.csv`. `KEYS.md` says what evidence each needs |
| The parts of the outlook the forecasters' survey does not give: income, pay, spending, industrial production, factory jobs, oil, sentiment, population, the 30% recession share; and the odds for the approval and nomination keys | When you judge they have changed. They carry the date they were entered | `fifty-two-keys/data/outlook.json` |
| Who the nominees are | Once, when both are known | Tipping Point's candidate file; The Margin reads it from the Nowcast |
| State approval from Civiqs (Tipping Point) | When a new copy is taken | as now |
| A decision on any change to a published method | When you choose | see below |

Everything else is read by the workflows.

## Changing a published method

The published forecast is `model.SET` in `the-margin/model.py`. The versions under review are `CANDIDATE` and `HYBRID`
beside it; they are run on every forecast and written to the data file and the archive, not to the page.

To adopt the hybrid: copy its four settings into `SET`, run `python backtest.py` (this rewrites `data/backtest.csv`, which
is what `tests/test_model.py` guards), run `python checks.py`, `python review.py`, `python status.py`, then
`python update.py --force`. The archive keeps every forecast made before the change exactly as it was. Say in the commit
what changed and why: the commit history is the record of method changes.

To let the approval allowance shrink with the calendar: `drift_rule='calendar'` in `SET`. Today's forecast does not move.

Fifty-Two Keys' rules are locked (`locked_keys.csv`, `tests/test_model.py`) and are not changed by any of this.

## Checking that everything still works

    the-margin        python -m pytest tests && node tests/test_page.js && node tests/browser_hover.js
    fifty-two-keys    python -m pytest tests
    tipping-point     python pipeline/tests/test_runs.py

Each workflow runs its repository's tests before it reads anything, and stops if one fails.

Every forecast The Margin has kept is in `docs/archive/` with the versions of the other two sites it was made from; the
Nowcast file itself is in `docs/archive/upstream/`. Fifty-Two Keys keeps its runs in `archive/` and its calls in
`data/key_calls.csv`; Tipping Point keeps its runs in `docs/record/`. None of these is ever rewritten.
