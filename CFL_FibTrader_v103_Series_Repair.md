# CFL v103 series repair

Use the complete `CFL_FibTrader_v103_Series_Repair.pine` file, replacing the prior strategy instance. Start with reset inputs on the same symbol, timeframe and loaded history. v102 remains available for comparison. This is a screenshot-based reconstruction, not a verified clone of the original signal.

## What changed

- A nested series requires at least scaled `MinMove` between its old terminal and new extreme. Previously even a one-tick break of a frozen terminal could create a new origin family. Candidate selection independently enforces the same minimum Fib range, including origin-flip branches.
- Tracker reversals and Fib retracement confirmation require the greater of `MinMove` and the fractional `ReversalLevel` distance. An origin break still invalidates immediately on close. Applying MinMove to reversal distance is an explicit reconstruction choice: screenshots do not identify its original scope.
- A frozen series retires when a subsequent directional extreme reaches its configured `ExtensionLevel`. Any eligible continuation/nested branches are created before retirement. This gives the extension input an actual expiry role; its original hidden semantics remain unverified. Open positions retain their original bracket even after their series retires.
- Opposing-midpoint clearance now checks every live opposing midpoint for collision with the entry-to-target path, including its endpoints. Midpoints behind entry or beyond target do not obstruct that path. The prior loop overwrote its result on each iteration; changing array order could change eligibility. Path-based interpretation of the original input remains a hypothesis.
- Zone steps start at the current observation bar. The previous segment stops there; the new geometry is never extended backward to the terminal's earlier bar or used to rewrite an earlier segment. Meaningful historical steps retain the existing bounded archive.
- Candidate stop validation explicitly requires the stop on the loss side of entry. This matters when users change target/stop ratios.

The working 50% entry, 38.2% target, 61.8% stop, tick offsets, one-fill-per-origin-family rule, both trading directions and fixed filled brackets remain. Default BTC price scaling is inherited; turn scaling off for literal original instrument units. No added trend, volume or profit filters are used to conceal lifecycle defects.

## Verification and remaining work

Run `python -m unittest discover -s tests -p test_cfl_v103_series_contract.py -v` from the repository root. Thirteen source/model checks cover mirrored reversal behavior, minimum-distance boundaries, origin breaks, opposing-level permutations and path boundaries, non-retroactive zone construction, extension retirement, family usage and fixed-bracket wiring. These checks do not execute Pine.

The adjacent verification JSON records the third-party Pine parser result and file hashes. A parser pass does not establish native TradingView compilation, broker-emulator behavior, profitability or original signal parity. No higher profit factor or trade-count result is claimed.

Original anchor selection, which series wins when several valid families coexist, exact reversal/reset timing, sizing, and the two distinct original PT-offset inputs remain unresolved from the supplied screenshots. This repair addresses identifiable defects without presenting those missing rules as recovered facts.
