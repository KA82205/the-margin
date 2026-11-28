"""data/desart.csv, from Jay DeSart's replication data for his long-range state-level forecasts (CC0, Harvard Dataverse:
doi:10.7910/DVN/HZGLY9 and doi:10.7910/DVN/6GWHQB), for the Research tab's study of forecasting the states a year out.
tools/fetch_desart.py fetches the data into a folder (through the samples workflow); then:

    python tools/make_desart.py <that folder>/desart

One row for each state in each election, 1996-2024, as in his data:
    result     the Democratic share of the two-party vote (blank for 2024: his data end with his forecast). New York is
               the Democratic line alone, as he counts it, so it sits one to two points below the candidate's whole vote
    previous   the same in the election before
    polls      the Democratic share of the two-party vote in national head-to-head polls of the October before the election
               year: the two eventual nominees through 2020, the average over every pairing polled for 2024
    home       home states, + for a Democrat and - for a Republican, less the previous election's; for 2024 spread over
               the candidates by how often each was polled
    terms      the consecutive terms of the party in the White House, + Democratic and - Republican
    turnout    each state's share of the vote, for adding the states up
    ev         electoral votes
    published  the forecast he published: 2020 (Joe Biden against Donald Trump, one of the five pairings he ran) and 2024
The District of Columbia, which he leaves out of the fit, is left out.
"""
import json, os, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(folder):
    read = lambda p: pd.read_csv(os.path.join(folder, p), sep='\t')
    names = json.load(open(os.path.join(ROOT, 'data', 'results_2024.json')))
    ab = {v['name']: k for k, v in names.items() if len(k) == 2}
    d = read('2024/DeSart PS 2024 Long-Range Forecast Data.tab')
    p20 = read('2020/PS - DeSart 2020 Predictions.tab')
    f24 = read('2024/DeSart PS 2024 Forecast 11-5-23.tab')
    f24 = f24[f24.State.map(ab).notna()]                         # the District of Columbia, listed as DC, is left out
    a = pd.DataFrame({'year': d.Year, 'state': d.State.map(ab), 'result': d.Result, 'previous': d.Previous, 'polls': d.NatlPoll, 'home': d.Home,
                      'terms': d.RegimeAge, 'turnout': d.TOweight, 'ev': d.ecvotes})
    a['published'] = None
    a.loc[a.year == 2020, 'published'] = a.loc[a.year == 2020, 'state'].map(p20.set_index(p20.State.map(ab)).forecast)
    b = pd.DataFrame({'year': 2024, 'state': f24.State.map(ab), 'result': None, 'previous': f24.Previous, 'polls': f24.Polls, 'home': f24.Home,
                      'terms': f24.Terms, 'turnout': f24.Turnout, 'ev': f24.ecvotes, 'published': f24.Forecast})
    out = pd.concat([a, b], ignore_index=True).sort_values(['year', 'state'])
    assert out.state.notna().all() and out.groupby('year').size().eq(50).all(), 'every election should have the 50 states'
    out.round(6).to_csv(os.path.join(ROOT, 'data', 'desart.csv'), index=False)
    print(out.groupby('year').agg(states=('state', 'size'), polls=('polls', 'first'), terms=('terms', 'first')).to_string())


if __name__ == '__main__':
    main(sys.argv[1])
