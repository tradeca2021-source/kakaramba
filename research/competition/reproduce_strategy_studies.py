"""Reproduce known development results without making a new holdout claim.

Writes only to a separate required output directory. Original frozen selection
and source manifests remain intact; this performs no candidate selection.
"""
import argparse
import hashlib
import json
from pathlib import Path

import channel_engine
import channel_study
import data
import engine
import regime_engine
import regime_study as common
from study import features, index, stamp


def reproduce(family, output):
    original = common.ROOT/'research/results'/family
    if output.resolve() == original.resolve():
        raise ValueError('Reproduction must use a separate output directory')
    report_path = original/'development.json'
    report = json.loads(report_path.read_text())
    module = channel_study if family == 'channel' else common
    if module.manifest() != report['sources_sha256']:
        raise ValueError('Frozen source differs; cannot claim exact reproduction')
    protocol = report['protocol']
    archives = (protocol['development_archives'] if family == 'channel'
                else [protocol['development_warmup_first_month'], protocol['development_last_month']])
    bars, lower, rates, hashes = data.load(*archives, canonical=True)
    if hashes != report['archives_sha256']:
        raise ValueError('Archive manifests differ')
    start, end = (index(bars, stamp(x)) for x in protocol['development'])
    output.mkdir(parents=True, exist_ok=True)
    common.OUTPUT = output
    base = engine.Rules(**protocol['baseline'])
    baseline_ready = features(bars, {base.pivot})[base.pivot]
    jobs = [(base.name, lambda: engine.replay(bars, lower, rates, base, start, end,
                                             prepared=baseline_ready), report['baseline'])]
    if family == 'channel':
        jobs.append((protocol['design']['name'], lambda: channel_engine.replay(bars, lower, rates, start, end), report['candidate']))
    else:
        ready = regime_engine.prepare(bars)
        for row in report['candidates']:
            rule = regime_engine.Rules(**row['rules'])
            jobs.append((rule.name, lambda rule=rule: regime_engine.replay(bars, lower, rates, rule, start, end,
                                                                         prepared=ready), row))
    checks = []
    for name, replay, expected in jobs:
        result = common.save_result(name, *replay(), protocol['development'])
        matched = all(result[key] == expected[key] for key in ('summary', 'half_years', 'branch_summaries', 'uncertainty'))
        csv_hashes = {}
        for suffix in ('trades', 'daily_equity', 'funding'):
            filename = f'{name}_{suffix}.csv'
            old, new = original/filename, output/filename
            if old.exists() != new.exists():
                matched = False
            elif old.exists():
                old_hash = hashlib.sha256(old.read_bytes()).hexdigest()
                new_hash = hashlib.sha256(new.read_bytes()).hexdigest()
                csv_hashes[filename] = new_hash
                matched = matched and old_hash == new_hash
        checks.append(dict(name=name, exact_match=matched, csv_sha256=csv_hashes))
        print(name, 'EXACT_MATCH', matched, flush=True)
    status = dict(family=family, historical_data_accessed=False,
                  selection_performed=False, fresh_validation_claim=False,
                  original_report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
                  source_manifest=report['sources_sha256'], checks=checks)
    (output/'reproduction.json').write_text(json.dumps(status, indent=2)+'\n')
    if not all(c['exact_match'] for c in checks):
        raise ValueError('Reproduction differs from published result')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('family', choices=['regime', 'channel'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reproduce(args.family, args.output)
