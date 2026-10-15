# CFL v102 lifecycle and historical-zone corrections

This is a repair of observable defects in v101, not proof that the screenshot-only model is the original algorithm. It remains separate from the RBO and other research strategies.

## Why the supplied v101 screenshot differs

v101 defaults allowed unlimited trades per Fib. A continuation clone also received a new ID, so an ID-only usage counter could not enforce one attempt per original series. Native trade markers accumulated around repeated touches. The updater fed both candle extremes into the same price-point transition routine, allowing multiple tracker reversals inside one completed bar under an assumed wick ordering. Finally, hiding/retiring a Fib called wipe(), which deleted its complete zone history: a long chart retained mostly current levels at the far right instead of earlier step zones.

## Changes

1. Actual fills consume an origin family identified by direction, origin bar and tick-formatted origin price. Continuation clones inherit the parent's used state; nested Fibs with a genuinely new origin are separate families. Both open records and same-bar roundtrip closed records are attributed before advancing/deleting series. A canceled unfilled quote does not consume its family. Filled-family cache is bounded4096; active Fib objects retain their used flag and propagate it to continuations. Quote-to-family entries are cleaned after canceled/closed orders. Max trades per individual Fib additionally defaults1; setting that input0 does not bypass the family rule.
2. One stepClosed() call per completed chart/engine candle replaces low→high/high→low price-point replay. The tracked wick extreme can update first, then the final close confirms at most one tracker reversal. A new opposite leg starts at that known close, not at an earlier opposite wick. Live-Fib origin invalidation is close-based. Independent older series may still create nested/origin-flip branches; that does not mean the tracker reversed twice. This changes the reconstruction's assumptions and is not verified original tick behavior.
3. Completed zone segments are detached into a retained drawing archive before their Fib drawings are wiped. Last120 historical segments are kept by default, configurable0–180; each visible live Fib keeps at most30 active segments. Live drawing count is capped to6 plus quoted/open series. Old archived segments are deleted FIFO, not all history on each Fib retirement. Historical zones describe the reconstruction's own calculations, not original reference matches.

The working50% entry,38.2% target,61.8% stop, tick offsets and one-fill OCA group remain. Filled stop/target stay fixed. Both directions remain available, without restoring RBO/SMC/volume/news/trend filters. Source-like tick-budget sizing and default BTC distance scaling are inherited; neither is recovered original sizing.

## Validation

22 local source/model regression checks cover opposite-wick handling, a wide candle's single tracker reversal, mirrored directions, prior-state stability, clone/fresh-origin eligibility, canceled vs filled consumption, same-bar completion and archived-zone retention/capping. These are not execution of Pine. Third-party parser status is in the adjacent verification file; native TradingView execution and exact screenshot parity remain unavailable. No trade count reduction or profitability is claimed from a native run.

Replace the old v101 instance with the complete CFL_FibTrader_v102_Lifecycle_Fix.pine file. Retain the price scale, dates and same Fib's origin/terminal values in comparisons. Screenshots alone still do not establish a unique original state machine.
