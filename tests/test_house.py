"""The House forecast's readers and checks (house/): each district's row and candidates as the overview writes them, a
runoff and an all-party first round, the states' map changes, the overview's seat count, what a member has said about
running and the chance it leaves the others, a redraw whose leans are not yet updated, and the checks that stop a run.
    python tests/test_house.py
"""
import os, sys
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, os.path.join(ROOT, 'house'))
import wiki_house as WH, live as LV, after_election as AE

PAGE = """{{Infobox election
| party1 = Democratic Party (United States)
| seats1 = '''259–262'''{{efn|name=x|Two runoffs.}}
| party2 = Republican Party (United States)
| seats2 = 173
}}
=== Summary district map changes ===
{|class="wikitable sortable"
!rowspan=2 |State
!rowspan=2 |Status
!rowspan=2 class="unsortable" |Notes
!colspan=3 |Change in partisanship
|-
![[#Alabama|Alabama]]
|data-sort-value=0 {{ya|text=New districts enacted}}
|A note.
|{{steady}}
|-
![[#Maryland|Maryland]]
|data-sort-value=3 {{pending|Pending legislative action}}
|A note.
|colspan=3 {{TBA}}
|-
![[#Missouri|Missouri]]
|data-sort-value=3 {{no2|[[2026 Missouri Proposition A|Districts left in place]]}}
|A note.
|{{Same}}
|}

==Alabama==
{| class="wikitable"
|-
!{{ushr|AL|1|X}}
|{{shading PVI|R|17}}
|{{sortname|Barry|Moore}}
|style="background-color:#FFB6B6" |Republican
|[[2020 United States House of Representatives elections in Alabama|2020]]
|{{Party shading/Republican/Hold}} |Incumbent retired to run for U.S. Senate.<br/>Republican hold.
|{{plainlist}}
*{{Party stripe|Republican Party (US)}}{{Aye}} '''[[Jerry Carl]]''' (Republican) 58.9%
*{{Party stripe|Democratic Party (US)}}Clyde Jones Jr. (Democratic) 41.0%
{{endplainlist}}
|-
!{{ushr|AL|2|X}}
|{{shading PVI|R|7}}
|{{sortname|Shomari|Figures}}
|style="color:black;background-color:#B0CEFF" |Democratic
|[[2024 United States House of Representatives elections in Alabama|2024]]
|Incumbent re-elected.
|{{plainlist}}
*{{Party stripe|Democratic Party (US)}}{{Aye}} '''[[Shomari Figures]]''' (Democratic) 53.7%
*{{Party stripe|Republican Party (US)}}[[Rhett Marques]] (Republican/Cons.) 46.1%
{{endplainlist}}
|}
"""
LA = """{{plainlist}}
{{collapsible list|title={{small|General election:}}
{{Party stripe|Democratic Party (US)}}{{mby}} Chauna Banks (Democratic) 19.4%
{{Party stripe|Republican Party (US)}}{{mby}} [[Blake Miguez]] (Republican) 19.2%
{{Party stripe|Republican Party (US)}}[[Rick Edmonds]] (Republican) 18.8%
{{Party stripe|Democratic Party (US)}}Rubia Garcia (Democratic) 12.8%}}
*{{small|'''Runoff:'''}}
*{{Party stripe|Democratic Party (US)}}{{aye}} '''Chauna Banks''' (Democratic)
*{{Party stripe|Republican Party (US)}}[[Blake Miguez]] (Republican)
{{endplainlist}}"""
BOX = """==District 4==
{{Election box begin no change | title = Republican primary results }}
{{Election box winning candidate with party link no change | candidate = Jeanine Driscoll | party = Republican Party (United States) | votes = 13,063 | percentage = 90.8 }}
{{Election box end}}
===General election===
{{Election box begin|title=2026 New York's 4th congressional district election}}
{{Election box winning candidate with party link |party = Democratic Party (United States) |candidate = [[Laura Gillen]] (incumbent) |votes = 160,000 |percentage = 55.0 }}
{{Election box candidate with party link |party = Republican Party (United States) |candidate = ''Jeanine Driscoll'' |votes = 120,000 |percentage = 41.2 }}
{{Election box candidate with party link |party = Conservative Party of New York State |candidate = ''Jeanine Driscoll'' |votes = 11,000 |percentage = 3.8 }}
{{Election box total no change |votes = 291,000 |percentage = 100 }}
{{Election box end}}
==District 5==
"""


def main():
    bad = []; check = lambda ok, msg: ok or bad.append(msg)
    R = WH.rows(PAGE, 2026)
    check([(r['state'], r['district'], r['pvi']) for r in R] == [('AL', 1, -17.0), ('AL', 2, -7.0)], f'the districts and their leans: {[(r["state"], r["district"], r["pvi"]) for r in R]}')
    c = WH.candidates(R[0]['candidates_raw'])
    check([(x['name'], x['party'], x['share'], x['won']) for x in c] == [('Jerry Carl', 'R', 58.9, True), ('Clyde Jones Jr.', 'D', 41.0, False)], f'candidates and shares: {c}')
    c2 = WH.candidates(R[1]['candidates_raw'])
    check(c2[1]['party'] == 'R', f'a fusion line ("Republican/Cons.") is the Republican: {c2}')
    la = WH.candidates(LA)
    gen = [x for x in la if x['round'] == 'general']; run = [x for x in la if x['round'] == 'runoff']
    check(len(gen) == 4 and sum(x['share'] for x in gen if x['party'] == 'D') == 32.2 and gen[0]['runoff'] and len(run) == 2 and run[0]['won'] and not run[1]['won'],
          f'an all-party first round and its runoff: {la}')
    check(WH.candidates('TBD') == [], 'a seat still to be decided gives no candidates')
    check(WH.map_changes(PAGE) == {'AL': 'enacted', 'MD': 'pending', 'MO': 'in place'}, f'map changes: {WH.map_changes(PAGE)}')
    check(AE.seats_box(PAGE) == {'D': (259, 262), 'R': 173}, f'the overview\'s seats, a range while undecided: {AE.seats_box(PAGE)}')
    g, r = WH.general_box(BOX.split('==District 5==')[0])
    dv = sum(x['votes'] for x in g['candidates'] if x['party'] == 'D'); rv = sum(x['votes'] for x in g['candidates'] if x['party'] == 'R')
    check(r is None and dv == 160000 and rv == 131000 and len(g['candidates']) == 2, f'the general box, a candidate on two lines once: {g}')
    secs = WH.district_sections('intro\n' + BOX, 'NY')
    check(sorted(secs) == [4, 5], f'district sections: {sorted(secs)}')
    # what members have said
    cases = {"Incumbent's intent unknown": 'unknown', 'Incumbent’s intent unknown': 'unknown', '2020 2024 (lost renomination) 2026 Incumbent\'s intent unknown': 'unknown',
             'Incumbent retiring to run for Senate': 'out', 'Incumbent running for re-election.': 'running', 'Incumbent running for Governor of Ohio.': 'out',
             'Incumbent renominated.': 'renominated', 'Incumbent lost renomination.': 'out', 'Incumbent resigned.': 'out', 'Incumbent died.': 'out', '': 'unknown'}
    for s, want in cases.items():
        check(LV.plan(s) == want, f'"{s}" reads as {LV.plan(s)}, not {want}')
    # the chance a member who has not said runs: the past rate less those who have said they are running
    LV.YEAR = 2028
    model = {'members': {'run_share': 0.87, 'primary_loss': 0.02}, 'redraw_sd': 0.8}
    text = PAGE.replace('Incumbent retired to run for U.S. Senate.<br/>Republican hold.', "Incumbent's intent unknown").replace('Incumbent re-elected.', 'Incumbent running for re-election.')
    W, ch, pu, nu = LV.districts(text, model, None)
    check(nu == 1 and abs(pu - min(0.97, max(0.5, (0.87 * 2 - 0.98) / 1))) < 1e-9 and W.p_inc_d[1] == 0.98 and W.p_inc_r[1] == 0 and W.p_inc_r[0] == pu,
          f'members\' chances of running: {pu}, {W[["p_inc_d", "p_inc_r"]].values.tolist()}')
    # Alabama enacted a new map; while its leans equal the last election's, the redraw's spread is added
    latest = pd.DataFrame({'state': ['AL', 'AL'], 'district': [1, 2], 'pvi': [-17.0, -7.0]})
    W2, _, _, _ = LV.districts(text, model, latest)
    check((W2.extra_sd == LV.REDRAW_MOVE_SD).all(), f'a new map with the old leans: {W2.extra_sd.tolist()}')
    W3, _, _, _ = LV.districts(text, model, latest.assign(pvi=[-18.0, -7.0]))
    check((W3.extra_sd == 0).all(), f'a new map with new leans: {W3.extra_sd.tolist()}')
    # the checks that stop a run
    try:
        LV.validate(W, {'blend': 52.0}, 230.0); bad.append('two districts passed the checks')
    except RuntimeError as e:
        check('2 districts' in str(e), f'the checks: {e}')
    print('\n'.join(bad) if bad else 'all House checks pass'); return not bad


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
