"""Two fixed NY Fibonacci confirmation routes; explicit post-hoc exploration."""
import argparse
import hashlib
import json
from pathlib import Path

import data
import daily_reversion_study as common
import session_fib_engine as session
import regime_study as metrics
from study import index, stamp

ROOT = common.ROOT
PROTOCOL = Path(__file__).with_name('session_fib_protocol.json')
SOURCES = set(common.SOURCES) | {'research/competition/'+name for name in
                               ('session_fib_study.py', 'session_fib_protocol.json', 'session_fib_engine.py', 'session_breakout_engine.py', 'session_breakout_protocol.json')}
MODES = {'ny_fib_same_candle': 'same_candle', 'ny_fib_two_candle': 'two_candle'}


def manifest():
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(SOURCES)}


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    metrics.OUTPUT = output
    before = manifest()
    protocol = json.loads(PROTOCOL.read_text())
    results = {r['name']: dict(design=r, periods=[]) for r in protocol['candidates']}
    hashes, qualities = {}, {}
    for period in protocol['periods']:
        print('LOAD', period['name'], flush=True)
        bars, lower, rates, raw = data.load(*period['archives'], canonical=True)
        hashes.update(raw)
        qualities[period['name']] = json.loads((data.CACHE/f"quality-{period['archives'][0]}-{period['archives'][1]}.json").read_text())
        start, end = (index(bars, stamp(t)) for t in period['evaluation'])
        ready = session.prepare(bars)
        for design in protocol['candidates']:
            name = design['name']
            model = session
            kwargs = dict(mode=MODES[name])
            replay = model.replay(bars, lower, rates, start, end, prepared=ready, **kwargs)
            row = metrics.save_result(name+'_'+period['name'], *replay, period['evaluation'])
            row['failures'] = common.failures(row, period, protocol['gates'])
            row['stresses'] = []
            for stress in protocol['stresses']:
                replay = model.replay(bars, lower, rates, start, end, prepared=ready,
                                     fee=stress['fee'], slippage_ticks=stress['slippage_ticks'], **kwargs)
                stressed = metrics.save_result(name+'_'+period['name']+'_'+stress['name'], *replay, period['evaluation'])
                stressed['assumptions'] = stress
                row['stresses'].append(stressed)
                if stressed['summary']['net'] <= 0:
                    row['failures'].append('nonpositive_'+stress['name'])
            results[name]['periods'].append(row)
            print('CANDIDATE', name, period['name'], json.dumps(row['summary']), 'FAILURES', row['failures'], flush=True)
            print('BLOCKS', [(b['start'][:10], round(b['net'], 2)) for b in row['half_years']], flush=True)
    if manifest() != before:
        raise ValueError('Sources changed during experiment')
    for row in results.values():
        row['total_positions'] = sum(p['summary']['trades'] for p in row['periods'])
        row['passes_exploratory_gate'] = (all(not p['failures'] for p in row['periods'])
                                         and row['total_positions'] >= protocol['gates']['minimum_positions_total'])
    eligible = [row for row in results.values() if row['passes_exploratory_gate']]
    selected = max(eligible, key=lambda row: min(p['summary']['net']/max(1, p['summary']['max_drawdown_5m_close'])
                                                for p in row['periods']))['design'] if eligible else None
    report = dict(protocol=protocol, sources_sha256=before, archives_sha256=hashes,
                  quality=qualities, results=list(results.values()), selected=selected,
                  prospective_validation=False, native_pine_verification=False,
                  caveats=['Post-hoc session Fibonacci follow-up on reused years: favorable results cannot be called independent validation.',
                           'Do not sum separate multi-year account returns into one continuous portfolio.',
                           'Binance data/actual funding with traded-open notional proxy; not exact Bitunix execution.',
                           'Five-minute closing drawdown understates possible intrabar excursions; risk can exceed intended sizing.'])
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print('SELECTED', selected, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'research/results/session_fib')
    run(parser.parse_args().output)
