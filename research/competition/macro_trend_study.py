"""One declared daily strategy, fixed diagnostic horizons, no parameter search."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import breakout_horizon_study as horizons
import data
import engine
import macro_trend_engine as macro
import regime_study as metrics
from study import index, stamp, write_rows

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = Path(__file__).with_name('macro_trend_protocol.json')
SOURCES = ['research/competition/'+name for name in
           ('macro_trend_protocol.json', 'macro_trend_engine.py', 'macro_trend_study.py',
            'breakout_horizon_study.py', 'channel_engine.py', 'data.py', 'engine.py',
            'regime_engine.py', 'regime_study.py', 'study.py')]+['research/fibonacci_backtest.py', 'research/breakout_pullback_backtest.py']


def manifest():
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}


def failures(row, period, gate):
    s = row['summary']
    out = []
    if s['trades'] < gate['minimum_positions_each_period']: out.append('too_few_positions')
    if s['net'] <= 0: out.append('nonpositive_net')
    if s['net'] <= period['baseline_net']: out.append('does_not_beat_baseline')
    if not s['gross_wins'] or (s['profit_factor'] is not None and s['profit_factor'] < gate['profit_factor_each_period']):
        out.append('profit_factor_below_gate')
    if s['net_without_best'] <= 0: out.append('nonpositive_net_without_best')
    if s['max_drawdown_5m_fraction'] > gate['maximum_5m_close_drawdown_fraction']: out.append('drawdown_above_gate')
    if sum(b['net'] > 0 for b in row['half_years']) < period['minimum_positive_half_years']: out.append('too_few_positive_half_years')
    return out


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    before = manifest()
    protocol = json.loads(PROTOCOL.read_text())
    metrics.OUTPUT = output
    cfg = replace(engine.f.Config(), fee=protocol['execution']['fee_per_side'],
                  slippage_ticks=protocol['execution']['slippage_ticks'])
    results, diagnostics, hashes = [], [], {}
    for period in protocol['periods']:
        print('LOAD', period['name'], flush=True)
        bars, lower, rates, archive_hashes = data.load(*period['archives'], canonical=True)
        hashes.update(archive_hashes)
        start, end = (index(bars, stamp(t)) for t in period['evaluation'])
        print('DIAGNOSTICS', period['name'], flush=True)
        for summary, events in horizons.study(bars, lower, rates, *map(stamp, period['evaluation']),
                                              protocol['event_study']['horizons_seconds'], cfg):
            summary['period'] = period['name']
            diagnostics.append(summary)
            write_rows(output/f"{period['name']}_events_{summary['horizon_seconds']}.csv", events)
            print('HORIZON', period['name'], summary['horizon_seconds'], summary['events'], summary['mean_net_r'], summary['mean_excess_r'], flush=True)
        ready = macro.prepare(bars)
        summary, trades, curve, flows = macro.replay(bars, lower, rates, start, end, prepared=ready)
        row = metrics.save_result(period['name'], summary, trades, curve, flows, period['evaluation'])
        row['baseline_net'] = period['baseline_net']
        row['failures'] = failures(row, period, protocol['gates'])
        row['stresses'] = []
        for stress in protocol['stresses']:
            run = macro.replay(bars, lower, rates, start, end, fee=stress['fee'],
                               slippage_ticks=stress['slippage_ticks'], prepared=ready)
            stressed = metrics.save_result(period['name']+'_'+stress['name'], *run, period['evaluation'])
            stressed['assumptions'] = stress
            row['stresses'].append(stressed)
            if stressed['summary']['net'] <= 0:
                row['failures'].append('nonpositive_'+stress['name'])
        results.append(row)
        print('STRATEGY', period['name'], json.dumps(summary), 'FAILURES', row['failures'], flush=True)
        print('BLOCKS', [(b['start'][:10], round(b['net'], 2)) for b in row['half_years']], flush=True)
    if manifest() != before:
        raise ValueError('Sources changed during experiment')
    total = sum(r['summary']['trades'] for r in results)
    passed = all(not r['failures'] for r in results) and total >= protocol['gates']['minimum_positions_total']
    report = dict(protocol=protocol, sources_sha256=before, archives_sha256=hashes,
                  diagnostics=diagnostics, results=results, total_positions=total,
                  passes_exploratory_gate=passed,
                  prospective_validation=False, native_pine_verification=False,
                  caveats=['Every evaluation year was already inspected; source predeclaration limits this experiment but cannot undo prior selection bias.',
                           'Independent continuous accounts for older/recent periods; do not add their profits as one continuous return.',
                           'Binance proxy with actual funding and traded-open notional; not venue-exact Bitunix costs or execution.',
                           '5m close drawdown misses intrabar excursions; gap losses can exceed intended risk.'])
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print('PASSES_EXPLORATORY_GATE', passed, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'research/results/macro_trend')
    run(parser.parse_args().output)
