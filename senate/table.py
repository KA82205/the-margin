"""The Senate model's training data, kept in the repository so the model can be refitted, and its back-test rerun, by
the scheduled jobs, without the raw sources (data/senate/raw/, kept out of the repository).

    data/senate/training_rows.csv       every race of every year in the fit, at each distance from the election the
                                        model is fitted at: its result and its inputs as they stood that day
    data/senate/chamber_by_year.json    each year's chamber: the Democratic caucus before and after the election, the
                                        races left out of the table that the Democratic side won, and the party that broke
                                        a 50-50 tie in the new Congress
    data/senate/seat_model_by_year.csv  the national seat-change model's Democratic caucus for each year at each distance

Made once from the raw sources (python senate/table.py --export); after that, after_election.py adds each election.
"""
import json, os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
D = os.path.join(ROOT, 'data', 'senate')
TRAIN, CHAMBER, SEATS = os.path.join(D, 'training_rows.csv'), os.path.join(D, 'chamber_by_year.json'), os.path.join(D, 'seat_model_by_year.csv')
COLS = ['year', 'state', 'special', 'days', 'dem2', 'lean', 'generic', 'fund_approval', 'blend_approval', 'inc_d', 'inc_r', 'track', 'poll', 'poll_w', 'money_t', 'appointed']


def load():
    X = pd.read_csv(TRAIN)
    X['special'] = X.special.astype(str).str.lower().eq('true'); X['year'] = X.year.astype(int); X['days'] = X.days.astype(int)
    return X


def chamber():
    return {int(y): v for y, v in json.load(open(CHAMBER)).items()}


def seat_models():
    s = pd.read_csv(SEATS)
    return {(int(r.year), int(r.days)): float(r.seat_model) for r in s.itertuples()}


def export():
    """From the raw sources: the rows of 2018-2026 as the back-tests built them, each year's chamber and the national
    seat model's forecast of it."""
    import backtest as B, national as NA, simulate as S, test_2026 as T, with_2026 as W
    X4, X5 = W.data()
    X5 = X5.assign(appointed=X5.appointed.fillna(0) if 'appointed' in X5 else 0)
    X5[COLS].sort_values(['year', 'state', 'special', 'days'], ascending=[True, True, True, False]).to_csv(TRAIN, index=False)
    last26 = X5[(X5.year == 2026) & (X5.days == 1)]
    ch = {y: {'before': S.CAUCUS_BEFORE[y], 'after': S.CAUCUS_AFTER.get(y, None), 'left_out_dem': {2018: 1, 2020: 0, 2022: 0, 2024: 0}.get(y), 'tie': S.TIE_GOES_TO.get(y)} for y in (2018, 2020, 2022, 2024)}
    ch[2026] = {'before': S.CAUCUS_BEFORE[2026], 'after': T.HOLDOVER_DEM + T.LEFT_OUT_DEM + int((last26.dem2 > 50).sum()), 'left_out_dem': T.LEFT_OUT_DEM, 'tie': T.TIE_GOES_TO}
    json.dump({str(k): v for k, v in ch.items()}, open(CHAMBER, 'w'), indent=1)
    nat = NA.National()
    pd.DataFrame([{'year': y, 'days': d, 'seat_model': round(S.national_seats(nat, y, d), 4)} for y in sorted(X5.year.unique()) for d in B.DAYS]).to_csv(SEATS, index=False)
    print(len(X5), 'rows;', ch)


if __name__ == '__main__':
    if '--export' in sys.argv: export()
