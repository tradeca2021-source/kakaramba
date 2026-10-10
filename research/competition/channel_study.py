"""One channel candidate, unchanged control, and a separately frozen stress test."""
import argparse
import hashlib
import json
from pathlib import Path

import channel_engine as channel
import data
import engine
import regime_study as common
from study import features, index, stamp

ROOT = common.ROOT
PROTOCOL = Path(__file__).with_name('channel_protocol.json')
OUTPUT = ROOT/'research/results/channel'


def manifest():
    paths = set(common.SOURCES) | {'research/competition/channel_engine.py',
                                 'research/competition/channel_study.py',
                                 'research/competition/channel_protocol.json'}
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}


def verify_frozen(frozen):
    if manifest() != frozen['sources_sha256']:
        raise ValueError('Sources changed after selection')
    if hashlib.sha256((OUTPUT/'development.json').read_bytes()).hexdigest() != frozen['development_sha256']:
        raise ValueError('Development report changed after selection')


def development():
    protocol = json.loads(PROTOCOL.read_text())
    reserved = sorted(p.name for p in data.CACHE.glob('BTCUSDT-*.zip')
                      if any(f'-{year}-' in p.name for year in (2020, 2021, 2022)))
    if reserved:
        raise ValueError('Reserved archives preexist; prior-use audit required')
    source_hashes = manifest()
    bars, lower, rates, hashes = data.load(*protocol['development_archives'], canonical=True)
    start, end = (index(bars, stamp(x)) for x in protocol['development'])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    common.OUTPUT = OUTPUT
    rules = engine.Rules(**protocol['baseline'])
    ready = features(bars, {rules.pivot})[rules.pivot]
    summary, trades, curve, flows = engine.replay(bars, lower, rates, rules, start, end, prepared=ready)
    baseline = common.save_result('baseline_v3', summary, trades, curve, flows, protocol['development'])
    summary, trades, curve, flows = channel.replay(bars, lower, rates, start, end)
    candidate = common.save_result(protocol['design']['name'], summary, trades, curve, flows, protocol['development'])
    candidate['qualification_failures'] = common.development_failures(summary, candidate['half_years'], baseline['summary']['net'])
    candidate['eligible'] = not candidate['qualification_failures']
    if manifest() != source_hashes:
        raise ValueError('Sources changed during research')
    report = dict(protocol=protocol, sources_sha256=source_hashes, archives_sha256=hashes,
                  reserved_data_preexistence_audit=reserved,
                  quality=json.loads((data.CACHE/f"quality-{protocol['development_archives'][0]}-{protocol['development_archives'][1]}.json").read_text()),
                  baseline=baseline, candidate=candidate,
                  selected=protocol['design'] if candidate['eligible'] else None,
                  caveats=['All development periods were previously inspected; this is exploratory evidence.',
                           'No preset target means no ex-ante reward/risk claim; realized expectancy determines qualification.',
                           'Binance proxy; actual funding rate with opening-price notional proxy.',
                           'Native Pine and Bitunix execution unverified. Five-minute closes miss intrabar drawdown.'])
    path = OUTPUT/'development.json'
    path.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    frozen = dict(selected=report['selected'], sources_sha256=source_hashes,
                  development_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  reserved_data_preexistence_audit=reserved,
                  historical_status='ready; not yet accessed' if report['selected'] else 'not accessed; no eligible candidate')
    (OUTPUT/'frozen_selection.json').write_text(json.dumps(frozen, indent=2)+'\n')
    print('CHANNEL', json.dumps(candidate), flush=True)
    print('SELECTED', bool(frozen['selected']), flush=True)


def historical():
    frozen = json.loads((OUTPUT/'frozen_selection.json').read_text())
    if not frozen['selected']:
        raise ValueError('No eligible candidate; reserved history remains unopened')
    verify_frozen(frozen)
    protocol = json.loads(PROTOCOL.read_text())
    bars, lower, rates, hashes = data.load(*protocol['historical_archives'], canonical=True)
    start, end = (index(bars, stamp(x)) for x in protocol['historical_test'])
    common.OUTPUT = OUTPUT
    ready = channel.prepare(bars)
    rules = engine.Rules(**protocol['baseline'])
    control_ready = features(bars, {rules.pivot})[rules.pivot]
    results, stresses = [], []
    for name in ('baseline', 'selected'):
        args = (bars, lower, rates, start, end)
        output = (channel.replay(*args, prepared=ready) if name == 'selected'
                  else engine.replay(bars, lower, rates, rules, start, end, prepared=control_ready))
        row = common.save_result('historical_'+name, *output, protocol['historical_test'])
        results.append(row)
        print('HISTORICAL', name, json.dumps(row['summary']), flush=True)
    for raw in protocol['stresses']:
        for name in ('baseline', 'selected'):
            kwargs = dict(fee=raw['fee'], slippage_ticks=raw['slippage_ticks'])
            output = (channel.replay(bars, lower, rates, start, end, prepared=ready, **kwargs)
                      if name == 'selected' else engine.replay(bars, lower, rates, rules, start, end,
                                                               prepared=control_ready, **kwargs))
            row = common.save_result('historical_'+name+'_'+raw['name'], *output, protocol['historical_test'])
            row.update(design=name, stress=raw)
            stresses.append(row)
            print('STRESS', name, raw['name'], row['summary']['net'], flush=True)
    selected = results[1]
    s = selected['summary']
    failures = []
    if s['trades'] < 50: failures.append('fewer_than_50_positions')
    if s['net'] <= 0: failures.append('nonpositive_net')
    if sum(b['net'] > 0 for b in selected['half_years']) < 3: failures.append('fewer_than_three_positive_half_years')
    if (s['profit_factor'] is not None and s['profit_factor'] < 1.2) or s['gross_wins'] <= 0: failures.append('profit_factor_below_1.2')
    if s['net_without_best'] <= 0: failures.append('nonpositive_net_without_best')
    if max(s['max_drawdown_fraction'], s['max_drawdown_5m_fraction']) > .05: failures.append('drawdown_exceeds_five_percent')
    if any(r['summary']['net'] <= 0 for r in stresses if r['design'] == 'selected'): failures.append('nonpositive_cost_stress')
    report = dict(frozen=frozen, archives_sha256=hashes,
                  quality=json.loads((data.CACHE/f"quality-{protocol['historical_archives'][0]}-{protocol['historical_archives'][1]}.json").read_text()),
                  results=results, stresses=stresses, qualification_failures=failures,
                  qualifies_for_pine=not failures,
                  caveat='Older-history test after freeze; not prospective evidence. Native verification outstanding.')
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
