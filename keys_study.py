"""Does the Fifty-Two Keys count earn its place in The Margin? Writes data/keys_study.json.

The hybrid (model.HYBRID) is run on 2008 to 2024 at ten distances from the election, five ways that differ only in what is
done with the Keys:

    hybrid         the Keys line as one of the equal parts of the national prior
    no keys        the same prior without it
    half           the Keys line counted at half the weight of the other parts
    recent line    the Keys line fitted on the last ten elections only, not on every election since 1952
    as a signal    no Keys in the national number; instead the count's call (above or under one half) is used as a sign of who
                   wins, and every simulated election is weighted by how well that sign has done before (below)

and beside them the published forecast and two plain baselines: the national polling average alone and the approval equation
alone.

The signal. The count's call is right or wrong about who wins the Electoral College. For election y its record is taken from
the elections before y only, with one right and one wrong call added (so a short record is not trusted), and then moved
halfway back to a coin toss, because the keys were chosen with the results in view and share approval and the economy with the
rest of the prior. Simulated elections in which the called party wins are weighted by record / (1 - record). That changes the
chance, the electoral-vote spread and every state's chance together, not the headline alone; here only the chance is scored.

Every score is given two ways: for who wins (the chance given to the winner, Brier score, log loss) and for the vote (the
national miss, with its sign, and the state miss). Five elections; ten distances from the same election are not ten elections.

    python keys_study.py
"""
import json
import numpy as np, pandas as pd
import backtest as B, fundamentals as F, model as M

NEAR = [250, 200, 150] + B.DAYS
WAYS = {'published': {}, 'hybrid': M.HYBRID, 'no keys': dict(M.HYBRID, national_prior='no_keys'), 'half': dict(M.HYBRID, national_prior='keys_half'), 'recent line': dict(M.HYBRID, national_prior='keys_recent')}


def signal(t, year):
    """(the party the count calls: True for the Democrats, how often the call has been right before `year`, shrunk)."""
    row = t[t.year == year].iloc[0]; past = t[(t.year < year)].dropna(subset=['keys'])
    won = past.inc_won_ec if 'inc_won_ec' in past else past.incvote > 50
    right = int(((past['keys'] > 0.5) == won).sum()); rec = (right + 1) / (len(past) + 2)
    inc_called = bool(row['keys'] > 0.5)
    return (inc_called == bool(row.deminc)), 0.5 + 0.5 * (rec - 0.5), right, len(past)


def scores(R):
    out = {}
    for d, g in R.groupby('days'):
        pw = g.p_winner.clip(1e-4, 1 - 1e-4)
        out[int(d)] = {'national': round(float(2 * g.national_error.abs().mean()), 2), 'signed': round(float(2 * g.national_error.mean()), 2), 'state': round(float(2 * g.state_mae.mean()), 2),
                       'favored': int((g.p_winner > 0.5).sum()), 'p_winner': round(float(g.p_winner.mean()), 3), 'brier': round(float(((1 - g.p_winner) ** 2).mean()), 4), 'log_loss': round(float((-np.log(pw)).mean()), 3),
                       'state_brier': round(float(g.brier.mean()), 4), 'called': int(g.states_called.sum()), 'cover80': round(float(g.cover80.mean()), 3),
                       'by_year': {int(y): {'miss': round(float(2 * e), 2), 'p_winner': round(float(p), 3)} for y, e, p in zip(g.year, g.national_error, g.p_winner)}}
    return out


def main():
    res, polls, errs = B.load(); t = F.table(); out = {'days': NEAR, 'ways': {}}
    ec = {}
    for y in sorted(t.year):
        r = res[res.year == y]
        if len(r): ec[int(y)] = bool(r.ev[r.dem2 > 50].sum() > r.ev.sum() / 2)
    t = t.assign(inc_won_ec=[(ec[y] == bool(d)) if y in ec else (v > 50) for y, d, v in zip(t.year, t.deminc, t.incvote)])
    runs = {}
    for name, sets in WAYS.items():
        B.VERSIONS['x'] = sets; runs[name] = B.run(days=NEAR, version='x'); B.VERSIONS.pop('x')
        out['ways'][name] = scores(runs[name]); print(name, 'done', flush=True)
    # the count as a sign of the winner, laid over the forecast that has no Keys in it
    R = runs['no keys'].copy(); sig = {}
    for y in B.YEARS:
        dem_called, rec, right, n = signal(t, y); sig[y] = {'calls_democrats': bool(dem_called), 'record_used': round(rec, 3), 'right_before': right, 'elections_before': n, 'call_was_right': bool(dem_called == ec[y])}
    def lay(p, y):
        L = sig[y]['record_used'] / (1 - sig[y]['record_used']); L = L if sig[y]['calls_democrats'] else 1 / L
        return p * L / (p * L + 1 - p)
    R['p_dem'] = [lay(p, y) for p, y in zip(R.p_dem, R.year)]; R['p_winner'] = [p if ec[y] else 1 - p for p, y in zip(R.p_dem, R.year)]
    out['ways']['as a signal'] = scores(R); out['signal'] = sig
    # the count on its own, 1952 on: its call against the Electoral College and against the national vote
    k = t.dropna(subset=['keys'])
    out['count_alone'] = {'elections': int(len(k)), 'right_college': int(((k['keys'] > 0.5) == k.inc_won_ec).sum()), 'right_vote': int(((k['keys'] > 0.5) == (k.incvote > 50)).sum()),
                          'since_2008': {int(y): {'count': round(float(c), 3), 'called_right': bool((c > 0.5) == w)} for y, c, w in zip(k.year, k['keys'], k.inc_won_ec) if y >= 2008}}
    # each part of the prior alone, and the two plain baselines: signed national miss by election, in points of margin
    parts = {}
    for y in B.YEARS:
        fd, fsd, pr = F.forecast(y, t); two = B.state_models(y)[1]['US']; act = float(res[res.year == y].nat2.iloc[0])
        parts[y] = {'keys line': 2 * (pr['keys_model'] - act), 'keys line, last ten elections': 2 * (F.keys_line(t, y, 10) - act), 'approval equation': 2 * (pr['approval_model'] - act),
                    'approval-and-economy model': 2 * (two[0] - act), 'long-range model': 2 * (two[1] - act)}
    out['parts'] = {k: {'by_year': {int(y): round(parts[y][k], 2) for y in B.YEARS}, 'size': round(float(np.mean([abs(parts[y][k]) for y in B.YEARS])), 2), 'signed': round(float(np.mean([parts[y][k] for y in B.YEARS])), 2)} for k in parts[B.YEARS[0]]}
    tl = pd.read_csv('data/timeline.csv'); n = tl[(tl.st == 'US') & (tl.cycle.isin(B.YEARS))]
    out['polls_alone'] = {int(d): {'national': round(float(2 * (g.avg - g.res).abs().mean()), 2), 'signed': round(float(2 * (g.avg - g.res).mean()), 2), 'favored_vote': int(((g.avg > 50) == (g.res > 50)).sum())} for d, g in n.groupby('days') if int(d) in NEAR}
    json.dump(out, open('data/keys_study.json', 'w'), indent=1)
    for name, s in out['ways'].items():
        print(f"{name:12s} national " + ' '.join(f"{s[d]['national']:.2f}" for d in NEAR) + ' | p_winner ' + ' '.join(f"{s[d]['p_winner']:.2f}" for d in NEAR) + ' | log loss ' + ' '.join(f"{s[d]['log_loss']:.2f}" for d in NEAR))
    print(out['signal']); print(out['count_alone']); print(out['parts'])


if __name__ == '__main__':
    main()
