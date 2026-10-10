"""Exactly four declared follow-ups on reused data; all outcomes retained."""
import argparse
import hashlib
import json
from pathlib import Path

import data
import daily_reversion_study as common
import reversion_exit_engine as exits
import intermediate_channel_engine as channel
import regime_study as metrics
from study import index, stamp

ROOT = common.ROOT
PROTOCOL = Path(__file__).with_name('exit_followup_protocol.json')
SOURCES = set(common.SOURCES) | {'research/competition/'+name for name in
                               ('exit_followup_study.py', 'exit_followup_protocol.json',
                                'reversion_exit_engine.py', 'intermediate_channel_engine.py')}
MODES = {'daily_rsi90_exit': 'rsi90', 'daily_sma5_exit': 'sma5', 'daily_three_day_exit': 'three_days'}


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
        prepared_exits, prepared_channel = exits.prepare(bars), channel.prepare(bars)
        for design in protocol['candidates']:
            name = design['name']
            model = exits if design['family'] == 'reversion' else channel
            ready = prepared_exits if model is exits else prepared_channel
            kwargs = dict(mode=MODES[name]) if model is exits else {}
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
                  caveats=['Post-hoc hypotheses and reused history: favorable results cannot be called independent validation.',
                           'Do not sum separate multi-year account returns into one continuous portfolio.',
                           'Binance data/actual funding with traded-open notional proxy; not exact Bitunix execution.',
                           'Five-minute closing drawdown understates possible intrabar excursions; risk can exceed intended sizing.'])
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print('SELECTED', selected, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'research/results/exit_followup')
    run(parser.parse_args().output)
