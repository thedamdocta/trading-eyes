# Venue mechanics (OANDA v20) — the quirks that cost real time

Learned live; each of these produced a confused agent or a real loss once.

- **Trailing stop minimum distance**: 0.05 (5 pips) on JPY pairs, 0.0005 on
  most others. A trail below the minimum is REJECTED with the order.
- **A trailing stop on a SHORT tracks the ASK** (long tracks the bid). The
  live trail level is `trailingStopLossOrder.trailingStopValue` on the
  trade object — `triggerPrice`/`price` are absent.
- **Candles endpoint rejects a future `to=`** (400 "Time is in the
  future"). Use `from=` + `count=` and filter locally.
- **FIFO netting trap**: a plain market order against your position closes
  the OLDEST trade first. If you ever have two trades in one instrument
  (e.g. an accidental add) and want to close a SPECIFIC one, use
  `PUT /v3/accounts/{acct}/trades/{tradeID}/close` — a market order would
  eat your protected trade and leave the naked one open.
- **A closed position ORPHANS its resting partial** — with no position
  behind it, that reduce order becomes a fresh ENTRY if it fills. The
  watcher cancels all pending on close; if the watcher is down, do it
  yourself immediately.
- **If the watcher is down when your entry fills**, the `.fx_plan` partial
  never gets placed. Place it by hand (`limitbuy`/`limitsell`) and verify
  `orders` shows it. After EVERY fill: `positions` size correct, stop AND
  trail non-None on the trade.
- **Cancel races the fill**: a limit at a nearly-touched level can fill in
  the seconds before your cancel arrives. The cancel reject reads like an
  error; it means "already filled." Check `positions` before reacting.
