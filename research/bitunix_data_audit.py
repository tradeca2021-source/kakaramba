"""Audit public Bitunix candles; reject invalid, incomplete or conflicting data.

This tool reads saved JSON responses. It never authenticates, places orders,
repairs bars, infers missing volume, or backtests a trading strategy.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

INTERVALS = {'1m': 60, '5m': 300, '15m': 900, '30m': 1800,
             '1h': 3600, '4h': 14400, '1d': 86400}
FIELDS = ('open', 'high', 'low', 'close', 'baseVol', 'quoteVol')


def milliseconds(text):
    dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Dates require an explicit timezone')
    return int(dt.timestamp()*1000)


def decode(row):
    if not isinstance(row, dict):
        raise ValueError('Candle must be an object')
    try:
        time = int(row['time'])
        # Reject fractional numeric timestamps instead of silently truncating.
        if Decimal(str(row['time'])) != time:
            raise ValueError('Fractional timestamp')
        values = {name: Decimal(str(row[name])) for name in FIELDS}
    except (KeyError, TypeError, ValueError, OverflowError, InvalidOperation) as exc:
        raise ValueError('Missing or invalid candle fields') from exc
    if not all(x.is_finite() for x in values.values()):
        raise ValueError('Non-finite candle value')
    o, h, l, c = (values[name] for name in ('open', 'high', 'low', 'close'))
    if not (0 < l <= min(o, c) <= max(o, c) <= h):
        raise ValueError('Invalid OHLC geometry')
    if values['baseVol'] < 0 or values['quoteVol'] < 0:
        raise ValueError('Negative volume')
    return dict(time=time, **values)


def audit(payload, interval, start_ms, end_ms, as_of_ms):
    step = INTERVALS[interval]*1000
    if not 0 <= start_ms < end_ms or start_ms % step or end_ms % step:
        raise ValueError('Window must have aligned start and exclusive end')
    if (end_ms-start_ms)//step > 200:
        raise ValueError('Audit one complete window of at most 200 candles')
    issues = []
    rows = payload.get('data') if isinstance(payload, dict) else None
    if not isinstance(payload, dict) or payload.get('code') != 0:
        issues.append(dict(kind='api_error', detail=payload.get('msg') if isinstance(payload, dict) else 'Invalid response'))
    if not isinstance(rows, list):
        issues.append(dict(kind='invalid_schema'))
        rows = []
    seen, usable = set(), {}
    for i, raw in enumerate(rows):
        try:
            row = decode(raw)
        except ValueError as exc:
            issues.append(dict(kind='invalid_candle', row=i, detail=str(exc), time=raw.get('time') if isinstance(raw, dict) else None))
            continue
        t = row['time']
        valid = True
        if t in seen:
            issues.append(dict(kind='duplicate_timestamp', time=t))
            valid = False
        seen.add(t)
        if t % step:
            issues.append(dict(kind='misaligned_timestamp', time=t))
            valid = False
        if not start_ms <= t < end_ms:
            issues.append(dict(kind='outside_requested_window', time=t))
            valid = False
        if t+step > as_of_ms:
            issues.append(dict(kind='unfinished_or_future_candle', time=t))
            valid = False
        if valid:
            usable[t] = row
    expected = list(range(start_ms, end_ms, step))
    missing = [t for t in expected if t not in usable]
    if missing:
        issues.append(dict(kind='missing_candles', timestamps=missing))
    return dict(accepted=not issues, action='usable' if not issues else 'quarantine',
                interval=interval, start_ms=start_ms, end_ms_exclusive=end_ms,
                as_of_ms=as_of_ms, expected_rows=len(expected), response_rows=len(rows),
                valid_in_window_rows=len(usable), issues=issues,
                caveat='Acceptance checks one response only; overlapping-page consistency, funding history and execution parity need separate checks.')


def overlap_conflicts(named_payloads):
    """Compare fields exactly, including malformed rows, without choosing a winner."""
    seen, conflicts = {}, []
    for name, payload in named_payloads:
        rows = payload.get('data', []) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            continue
        for raw in rows:
            try:
                t = int(raw['time'])
                values = {field: Decimal(str(raw[field])) for field in FIELDS}
                if not all(x.is_finite() for x in values.values()):
                    continue
            except (KeyError, TypeError, ValueError, OverflowError, InvalidOperation):
                continue
            if t in seen:
                old_name, old_values = seen[t]
                different = [field for field in FIELDS if old_values[field] != values[field]]
                if different:
                    conflicts.append(dict(time=t, earlier_response=old_name,
                                          later_response=name, different_fields=different,
                                          earlier_values={field: str(old_values[field]) for field in different},
                                          later_values={field: str(values[field]) for field in different}))
            else:
                seen[t] = (name, values)
    return conflicts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('response', type=Path)
    parser.add_argument('--interval', choices=list(INTERVALS), required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True, help='Exclusive end, with timezone')
    parser.add_argument('--as-of', help='Observation cutoff with timezone; default current UTC')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    cutoff = milliseconds(args.as_of) if args.as_of else int(datetime.now(timezone.utc).timestamp()*1000)
    result = audit(json.loads(args.response.read_text()), args.interval,
                   milliseconds(args.start), milliseconds(args.end), cutoff)
    text = json.dumps(result, indent=2)+'\n'
    if args.output:
        args.output.write_text(text)
    print(text, end='')
    raise SystemExit(0 if result['accepted'] else 1)
