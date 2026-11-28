"""Each House candidate's money as it stood at each distance from election day, from their FEC reports
(tools/fetch_house_money.py): the money raised in the reports the FEC had received by that day, the latest version of
each report, each report put to its candidate through the FEC's candidate-committee links (ccl<yy>.txt). Written to
data/house/money_by_date.csv (year, fec, days, receipts), for testing money in the House forecast the fair way: a
forecast made on a day sees only the reports in by then.

    python house/money.py <folder with reports_<year>.csv>
"""
import glob, os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
DAYS = [365, 250, 120, 60, 30, 14, 7, 1]
ELECTION = {2012: '2012-11-06', 2014: '2014-11-04', 2016: '2016-11-08', 2018: '2018-11-06', 2020: '2020-11-03', 2022: '2022-11-08', 2024: '2024-11-05', 2026: '2026-11-03'}


def main(folder):
    out = []
    T = pd.read_csv(os.path.join(ROOT, 'data', 'house', 'training.csv'), dtype={'dem_fec': str, 'rep_fec': str})
    for f in sorted(glob.glob(os.path.join(folder, 'reports_*.csv'))):
        r = pd.read_csv(f, dtype={'candidate_id': str, 'committee_id': str})
        if r.empty: continue
        year = int(r.cycle.mode().iloc[0])
        # a report names its committee; the FEC's links name the committee's candidate (one of those asked for)
        want = set(T.loc[T.year == year, 'dem_fec'].dropna()) | set(T.loc[T.year == year, 'rep_fec'].dropna())
        link = pd.read_csv(os.path.join(folder, f'ccl{str(year)[2:]}.txt'), sep='|', header=None, dtype=str,
                           names=['cand', 'cand_year', 'fec_year', 'cmte', 'tp', 'dsgn', 'lid'])
        link = link[link.cand.isin(want)].drop_duplicates('cmte').set_index('cmte').cand
        r['candidate_id'] = r.candidate_id.where(r.candidate_id.notna() & (r.candidate_id != ''), r.committee_id.map(link))
        r = r[r.candidate_id.isin(want) & (r.most_recent.astype(str).str.lower() == 'true')].copy()
        r['received'] = pd.to_datetime(r.receipt_date, errors='coerce'); r['money'] = pd.to_numeric(r.total_receipts_period, errors='coerce').fillna(0)
        day = pd.Timestamp(ELECTION[year])
        for d in DAYS:
            cut = day - pd.Timedelta(days=d)
            s = r[r.received <= cut].groupby('candidate_id').money.sum()
            out += [{'year': year, 'fec': c, 'days': d, 'receipts': round(float(v), 2)} for c, v in s.items()]
        print(year, r.candidate_id.nunique(), 'candidates,', len(r), 'reports')
    pd.DataFrame(out).to_csv(os.path.join(ROOT, 'data', 'house', 'money_by_date.csv'), index=False)


if __name__ == '__main__':
    main(sys.argv[1])
