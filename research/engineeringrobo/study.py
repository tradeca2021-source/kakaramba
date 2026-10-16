"""Run the frozen EngineeringRobo comparison on audited local candles or archives."""
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

from replay import Candle, Costs, features, replay, event_study

HERE = Path(__file__).resolve().parent


def timestamp(value):
    try:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Non-finite time')
        seconds = number / 1000 if number >= 1e12 else number
        if seconds != int(seconds):
            raise ValueError('Candle/funding time must resolve to whole seconds')
        return int(seconds)
    except ValueError:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            raise ValueError('Timestamp requires a timezone')
        return int(dt.timestamp())


def load_csv(path, interval, as_of):
    out = []
    with Path(path).open(newline='') as stream:
        reader = csv.DictReader(stream)
        time_name = next((n for n in ('time', 'timestamp', 'open_time') if n in (reader.fieldnames or [])), None)
        if not time_name or not {'open', 'high', 'low', 'close'} <= set(reader.fieldnames):
            raise ValueError('Need time, open, high, low, close candle columns')
        for row in reader:
            t = timestamp(row[time_name])
            o, h, l, c = (float(row[n]) for n in ('open', 'high', 'low', 'close'))
            if not all(math.isfinite(x) for x in (o, h, l, c)) or not 0 < l <= min(o, c) <= max(o, c) <= h:
                raise ValueError('Malformed OHLC geometry')
            if t % interval or t + interval > as_of:
                raise ValueError('Unaligned or unclosed/future candle')
            if out and t - out[-1].time != interval:
                raise ValueError('Gap, duplicate or unordered candle')
            out.append(Candle(t, o, h, l, c))
    if not out:
        raise ValueError('Empty candle file')
    return out


def check_aggregation(bars, lower):
    for bar in bars:
        sub = [lower.get(bar.time + j * 300) for j in range(3)]
        if any(b is None for b in sub):
            raise ValueError('Missing 5m candle')
        aggregate = (sub[0].open, max(b.high for b in sub), min(b.low for b in sub), sub[-1].close)
        native = (bar.open, bar.high, bar.low, bar.close)
        if any(abs(x - y) > 1e-6 for x, y in zip(aggregate, native)):
            raise ValueError(f'Native 15m/5m aggregation conflict at {bar.time}; quarantined')


def load_funding(path):
    rows = []
    with Path(path).open(newline='') as f:
        for row in csv.DictReader(f):
            t, rate = timestamp(row['time']), float(row['funding_rate'])
            if not math.isfinite(rate) or (rows and t <= rows[-1][0]):
                raise ValueError('Invalid, duplicated or unordered funding settlement')
            rows.append((t, rate))
    if not rows:
        raise ValueError('Empty funding history')
    return rows


def write_rows(path, rows):
    if not rows:
        return
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({k: json.dumps(v, sort_keys=True) if isinstance(v, dict) else v for k, v in r.items()} for r in rows)


def choose(development, minimum=30):
    baseline = development['current_bracket']['maximum_drawdown_5m_close']
    eligible = []
    for name, row in development.items():
        if name in ('reverse_only', 'current_bracket'):
            continue
        pf = row['profit_factor']
        good_pf = pf >= 1.1 if pf is not None else row['wins'] > 0
        if row['trades'] >= minimum and row['net'] > 0 and good_pf and row['maximum_drawdown_5m_close'] <= baseline:
            eligible.append((name, row))
    return max(eligible, key=lambda item: item[1]['net'] / max(1., item[1]['maximum_drawdown_5m_close']))[0] if eligible else None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--csv-15m', type=Path)
    p.add_argument('--csv-5m', type=Path)
    p.add_argument('--funding-csv', type=Path)
    p.add_argument('--venue', help='Required attribution for supplied local data')
    p.add_argument('--download-binance', action='store_true', help='Explicitly use an exploratory Binance proxy, not Bitunix validation')
    p.add_argument('--allow-no-funding', action='store_true', help='Exploratory diagnostics only; cannot qualify a candidate')
    p.add_argument('--output', type=Path, default=Path('/workspace/engineeringrobo-study-results'))
    args = p.parse_args()
    protocol_path = HERE / 'trading_study_protocol.json'
    protocol = json.loads(protocol_path.read_text())
    as_of = int(datetime.now(timezone.utc).timestamp())
    if args.download_binance:
        if args.csv_15m or args.csv_5m or args.funding_csv or args.venue:
            p.error('Choose archives or attributed local data, not both')
        sys.path.insert(0, str(HERE.parent / 'competition'))
        import data as archives
        bars, lower, funding, hashes = archives.load(protocol['data']['warmup_month'], protocol['data']['last_month'])
        venue = 'Binance USD-M BTCUSDT proxy; not Bitunix performance'
    else:
        if not args.csv_15m or not args.csv_5m or not args.venue:
            p.error('Supply --csv-15m, --csv-5m and --venue, or explicitly --download-binance')
        bars = load_csv(args.csv_15m, 900, as_of)
        lower = {b.time: b for b in load_csv(args.csv_5m, 300, as_of)}
        funding = load_funding(args.funding_csv) if args.funding_csv else []
        files = [args.csv_15m, args.csv_5m] + ([args.funding_csv] if args.funding_csv else [])
        hashes = {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
        venue = args.venue
    if not funding and not args.allow_no_funding:
        p.error('Historical funding is required; --allow-no-funding explicitly permits diagnostics only')
    check_aggregation(bars, lower)
    prepared = features(bars)
    periods = {k: (timestamp(v[0]), timestamp(v[1])) for k, v in protocol['periods'].items() if isinstance(v, list)}
    boundaries = {}
    for name, (start, end) in periods.items():
        indices = [i for i, bar in enumerate(bars) if start <= bar.time < end]
        if not indices or bars[indices[0]].time != start or bars[indices[-1]].time + 900 != end:
            raise ValueError(f'Incomplete declared period: {name}')
        if indices[0] < 300:
            raise ValueError('At least 300 prior candles required for indicator warm-up')
        boundaries[name] = (indices[0], indices[-1] + 1)
    first, last = periods['development'][0], periods['historical_review'][1]
    if funding:
        relevant = [(t, r) for t, r in funding if first <= t < last]
        if not relevant or relevant[0][0] - first > 43200 or last - relevant[-1][0] > 43200 or any(relevant[i][0] - relevant[i - 1][0] > 43200 for i in range(1, len(relevant))):
            raise ValueError('Funding coverage has unexplained >12-hour gaps; cannot treat missing history as zero')
    run = args.output / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True, exist_ok=False)
    model = protocol['costs']
    if model['maximum_exposure_multiple'] != 1:
        raise ValueError('Only 1x exposure is implemented')
    costs = Costs(fee=model['fee_per_side'], tick=model['tick'], slippage_ticks=model['slippage_ticks'], quantity=model['quantity_btc'], capital=model['initial_equity'])
    settings = [('base', costs)] + [(f'stress_{i+1}', replace(costs, fee=v['fee_per_side'], slippage_ticks=v['slippage_ticks'])) for i, v in enumerate(protocol['stresses'])]
    results = {}
    selected = None
    # Development selection is finalized before evaluating comparison/review accounts.
    for period, (a, b) in boundaries.items():
        results[period] = {}
        for label, cfg in settings:
            results[period][label] = {}
            for rule in protocol['comparisons']:
                summary, trades, curve = replay(bars, lower, funding, rule, a, b, cfg, prepared)
                results[period][label][rule['name']] = summary
                write_rows(run / f'{period}_{label}_{rule["name"]}_trades.csv', trades)
                # Retain daily closing equity, not millions of redundant intrabar CSV rows.
                daily = {}
                for row in curve:
                    daily[(row['time'] - 1) // 86400] = row
                write_rows(run / f'{period}_{label}_{rule["name"]}_daily_equity.csv', list(daily.values()))
        if period == 'development':
            selected = choose(results[period]['base']) if funding else None
        events = event_study(bars, lower, a, b, costs, prepared)
        write_rows(run / f'{period}_signal_events.csv', events)
        by_horizon = {}
        for h in protocol['event_study']['horizons_bars']:
            subset = [r for r in events if r['horizon_bars'] == h]
            positive = [r for r in subset if r['net_before_funding'] > 0]
            by_horizon[str(h)] = dict(events=len(subset), positive_before_funding=len(positive),
                mean_mae_atr_positive=sum(r['mae_atr'] for r in positive) / len(positive) if positive else None,
                note='Overlapping forward labels, not independent trades; funding excluded from these descriptive labels')
        results[period]['event_summary'] = by_horizon
    report = dict(status='exploratory_replay_completed', venue=venue, protocol_sha256=hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
                  source_sha256={name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in ('replay.py', 'study.py')},
                  input_hashes=hashes, costs=asdict(costs), selected_on_development=selected,
                  funding_supplied=bool(funding), fresh_validation=False, native_pine_parity=False,
                  results=results, limitations=['Previously inspected BTC periods; not untouched validation',
                  'Funding uses supplied rates and 5m opening last-price mark proxies',
                  'Conservative stop-first 5m execution; not native Pine parity',
                  'Margin closure approximates full liquidation rather than Pine partial liquidation',
                  'Event-label returns exclude funding and overlap; no significance claim'])
    (run / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps(dict(output=str(run), selected=selected, fresh_validation=False, venue=venue)))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, AssertionError) as exc:
        print(json.dumps(dict(status='blocked_or_invalid_input', error=str(exc))), file=sys.stderr)
        raise SystemExit(2)
