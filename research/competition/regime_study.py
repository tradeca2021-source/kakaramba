"""Finite regime experiment. Freeze a winner before accessing older history."""
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random

import data
import engine
import regime_engine as regime
from study import features, index, stamp, write_rows

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = Path(__file__).with_name('regime_protocol.json')
OUTPUT = ROOT/'research/results/regime'
SOURCES = ('research/competition/regime_engine.py',
           'research/competition/regime_study.py',
           'research/competition/regime_protocol.json',
           'research/competition/engine.py', 'research/competition/data.py',
           'research/competition/study.py', 'research/fibonacci_backtest.py',
           'research/breakout_pullback_backtest.py')


def manifest():
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}


def daily_curve(curve):
    days = {}
    for row in curve:
        # An equity mark exactly at midnight ends the preceding calendar day.
        days[(row['time']-1)//86400] = row
    return list(days.values())


def half_years(curve, start, end, initial=100000):
    points = {row['time']: row['equity'] for row in curve}
    start_time, end_time = stamp(start), stamp(end)
    current = start_time
    rows = []
    previous_equity = initial
    while current < end_time:
        dt = datetime.fromtimestamp(current, timezone.utc)
        following = stamp(f'{dt.year}-07-01') if dt.month <= 6 else stamp(f'{dt.year+1}-01-01')
        following = min(following, end_time)
        if following not in points:
            raise ValueError('Missing equity mark at block boundary')
        equity = points[following]
        rows.append(dict(start=datetime.fromtimestamp(current, timezone.utc).isoformat(),
                         end=datetime.fromtimestamp(following, timezone.utc).isoformat(),
                         partial_half_year=following == end_time and datetime.fromtimestamp(following, timezone.utc).month not in (1, 7),
                         opening_equity=previous_equity, closing_equity=equity,
                         net=equity-previous_equity))
        previous_equity = equity
        current = following
    return rows


def uncertainty(daily, initial=100000, samples=2000, seed=20261010):
    logs = []
    previous = initial
    for row in daily:
        if row['equity'] <= 0 or previous <= 0:
            return dict(status='Unavailable: nonpositive equity')
        logs.append(math.log(row['equity']/previous))
        previous = row['equity']
    rng = random.Random(seed)
    results = []
    n = len(logs)
    for _ in range(samples):
        total = 0
        used = 0
        while used < n:
            begin = rng.randrange(n)
            length = min(7, n-used)
            total += sum(logs[(begin+j)%n] for j in range(length))
            used += length
        results.append(100*math.expm1(total))
    results.sort()
    return dict(method='circular seven-day blocks of daily log account returns',
                seed=seed, replicates=samples, days=n,
                period_return_percent_interval_95=[results[int(.025*samples)], results[int(.975*samples)-1]],
                caveat='Exploratory uncertainty only; reused data, multiple comparisons and regime dependence remain.')


def development_failures(summary, blocks, baseline_net):
    failures = []
    if summary['trades'] < 100:
        failures.append('fewer_than_100_positions')
    if summary['net'] <= baseline_net:
        failures.append('net_does_not_exceed_baseline')
    if sum(b['net'] > 0 for b in blocks) < 4:
        failures.append('fewer_than_four_positive_half_year_blocks')
    if summary['net_without_best'] <= 0:
        failures.append('nonpositive_net_without_best_trade')
    if max(summary['max_drawdown_fraction'], summary['max_drawdown_5m_fraction']) > .05:
        failures.append('drawdown_exceeds_five_percent')
    return failures


def save_result(name, summary, trades, curve, flows, period):
    daily = daily_curve(curve)
    blocks = half_years(curve, *period)
    branches = {}
    for t in trades:
        branch = t.get('branch', 'baseline')
        row = branches.setdefault(branch, dict(trades=0, wins=0, net=0., fees=0., funding=0.))
        row['trades'] += 1
        row['wins'] += t['net'] > 0
        for key in ('net', 'fees', 'funding'):
            row[key] += t[key]
    write_rows(OUTPUT/f'{name}_trades.csv', trades)
    write_rows(OUTPUT/f'{name}_daily_equity.csv', daily)
    write_rows(OUTPUT/f'{name}_funding.csv', flows)
    return dict(name=name, summary=summary, half_years=blocks,
                branch_summaries=branches, uncertainty=uncertainty(daily))


def development():
    protocol = json.loads(PROTOCOL.read_text())
    # Metadata-only prior-use audit; never read reserved candle values here.
    reserved = sorted(p.name for p in data.CACHE.glob('BTCUSDT-*.zip')
                      if any(f'-{year}-' in p.name for year in (2020, 2021, 2022)))
    if reserved:
        raise ValueError('Reserved archives already exist; prior-use audit required before claiming untouched validation')
    hashes_before = manifest()
    bars, lower, rates, hashes = data.load(protocol['development_warmup_first_month'],
                                          protocol['development_last_month'], canonical=True)
    start, end = (index(bars, stamp(x)) for x in protocol['development'])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    base = engine.Rules(**protocol['baseline'])
    prepared_control = features(bars, {base.pivot})[base.pivot]
    summary, trades, curve, flows = engine.replay(bars, lower, rates, base,
                                                start, end, prepared=prepared_control)
    baseline = save_result(base.name, summary, trades, curve, flows, protocol['development'])
    print('BASELINE', json.dumps(summary), flush=True)
    prepared = regime.prepare(bars)
    candidates = []
    for raw in protocol['candidates']:
        rules = regime.Rules(**raw)
        summary, trades, curve, flows = regime.replay(bars, lower, rates, rules,
                                                     start, end, prepared=prepared)
        row = save_result(rules.name, summary, trades, curve, flows, protocol['development'])
        row['rules'] = asdict(rules)
        row['qualification_failures'] = development_failures(summary, row['half_years'], baseline['summary']['net'])
        row['eligible'] = not row['qualification_failures']
        candidates.append(row)
        print('CANDIDATE', rules.name, json.dumps(summary), 'failures', row['qualification_failures'], flush=True)
    eligible = [x for x in candidates if x['eligible']]
    selected = max(eligible, key=lambda x: (min(b['net'] for b in x['half_years']), x['summary']['net'])) if eligible else None
    if manifest() != hashes_before:
        raise ValueError('Sources changed during development; do not freeze these results')
    report = dict(protocol=protocol, sources_sha256=hashes_before, archives_sha256=hashes,
                  reserved_data_preexistence_audit=reserved,
                  quality=json.loads((data.CACHE/f"quality-{protocol['development_warmup_first_month']}-{protocol['development_last_month']}.json").read_text()),
                  regime_bar_counts=dict(Counter(str(x) for x in prepared[1][start:end])),
                  baseline=baseline, candidates=candidates,
                  selected=selected['rules'] if selected else None,
                  limitations=['All development outcomes are on repeatedly inspected Binance data.',
                               'Continuous single account; no capital resets at half-year boundaries.',
                               '5m stop-first execution cannot establish native TradingView parity.',
                               'Funding uses candle-open notional proxy; Bitunix candles/fills differ.',
                               'Five-minute closing equity can miss intrabar drawdown.',
                               'Baseline engine unchanged; its drawdown metrics are in account currency.'])
    report_path = OUTPUT/'development.json'
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    frozen = dict(selected=report['selected'], sources_sha256=hashes_before,
                  development_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
                  historical_test=protocol['historical_test'],
                  reserved_data_preexistence_audit=reserved,
                  historical_status='not accessed; no eligible candidate' if selected is None else 'ready for frozen historical test',
                  pine_status='No new Pine promotion before historical qualification')
    (OUTPUT/'frozen_selection.json').write_text(json.dumps(frozen, indent=2)+'\n')
    print('SELECTED', frozen['selected'], flush=True)


def historical():
    frozen = json.loads((OUTPUT/'frozen_selection.json').read_text())
    if not frozen['selected']:
        raise ValueError('No eligible development candidate; reserved history must remain unopened')
    if manifest() != frozen['sources_sha256']:
        raise ValueError('Frozen candidate sources changed')
    if hashlib.sha256((OUTPUT/'development.json').read_bytes()).hexdigest() != frozen['development_sha256']:
        raise ValueError('Frozen development report changed')
    protocol = json.loads(PROTOCOL.read_text())
    bars, lower, rates, hashes = data.load(protocol['historical_warmup_first_month'],
                                          protocol['historical_test_last_month'], canonical=True)
    start, end = (index(bars, stamp(x)) for x in protocol['historical_test'])
    prepared = regime.prepare(bars)
    control_rules = engine.Rules(**protocol['baseline'])
    control_prepared = features(bars, {control_rules.pivot})[control_rules.pivot]
    rules = regime.Rules(**frozen['selected'])
    results, stresses = [], []
    for name, callable_engine, rule, ready in [('historical_baseline', engine, control_rules, control_prepared),
                                              ('historical_selected', regime, rules, prepared)]:
        summary, trades, curve, flows = callable_engine.replay(bars, lower, rates, rule,
                                                              start, end, prepared=ready)
        results.append(save_result(name, summary, trades, curve, flows, protocol['historical_test']))
        print(name, json.dumps(summary), flush=True)
    for raw in protocol['stresses']:
        for name, callable_engine, rule, ready in [('baseline', engine, control_rules, control_prepared),
                                                  ('selected', regime, rules, prepared)]:
            summary, trades, curve, flows = callable_engine.replay(bars, lower, rates, rule, start, end,
                                                                  fee=raw['fee'], slippage_ticks=raw['slippage_ticks'], prepared=ready)
            row = save_result('historical_'+name+'_'+raw['name'], summary, trades, curve, flows, protocol['historical_test'])
            row.update(design=name, stress=raw)
            stresses.append(row)
            print('STRESS', name, raw['name'], summary['net'], flush=True)
    selected = results[1]
    s = selected['summary']
    failures = []
    if s['trades'] < 50: failures.append('fewer_than_50_positions')
    if s['net'] <= 0: failures.append('nonpositive_net')
    if sum(b['net'] > 0 for b in selected['half_years']) < 3: failures.append('fewer_than_three_positive_half_years')
    if s['profit_factor'] is not None and s['profit_factor'] < 1.2 or s['gross_wins'] <= 0: failures.append('profit_factor_below_1.2')
    if s['net_without_best'] <= 0: failures.append('nonpositive_net_without_best')
    if max(s['max_drawdown_fraction'], s['max_drawdown_5m_fraction']) > .05: failures.append('drawdown_exceeds_five_percent')
    if any(x['summary']['net'] <= 0 for x in stresses if x['design'] == 'selected'): failures.append('nonpositive_cost_stress')
    report = dict(frozen=frozen, archives_sha256=hashes,
                  quality=json.loads((data.CACHE/f"quality-{protocol['historical_warmup_first_month']}-{protocol['historical_test_last_month']}.json").read_text()),
                  results=results, stresses=stresses, qualification_failures=failures,
                  qualifies_for_pine=not failures,
                  caveat='Unopened older-history stress, not forward evaluation. Native and prospective verification still outstanding.')
    (OUTPUT/'historical.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print('QUALIFIES_FOR_PINE', not failures, failures, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['development', 'historical'])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        OUTPUT = args.output
    (development if args.phase == 'development' else historical)()
