# Process topology — who runs, who writes, who reads

Four processes, brought up in order by `./desk-up.sh`:

```
fx_desk.py FOCUS_PAIR run/   (detached)  → writes run/desk.log  "FX <PAIR> ..." focus bars
fx_scan.py run/desk.log      (detached)  → appends "FX SCAN ..." basket + "FX !!" alerts
trade_watch.sh               (Monitor)   → reads desk.log + venue; 5-min flat / 1-min in-trade
                                           reports, places .fx_plan partials on fill, cancels
                                           orphans on close, MANFORD zone lane alerts
coil_log.py loop             (Monitor)   → appends coils.jsonl; prints new breaks
```

- The two FEEDS are detached (`nohup`/`&`) — they survive agent restarts.
- The two WATCHERS run under the agent harness's Monitor so their stdout
  reaches the agent as events. They die with the session — **restart them at
  session start** (`./desk-up.sh` is idempotent; it skips what's alive).
- Do not edit `trade_watch.sh` while it runs. Stop → edit → restart.
- Liveness checks (doctor.sh runs these): `ps` for fx_desk/fx_scan;
  desk.log mtime < 2 min; venue reachable via `fx_execute.py balance`.

## Line contract (run/desk.log)
`FX <PAIR> ...` focus bars · `FX SCAN ...` basket · `FX !! ...` alerts ·
`MANFORD ...` zone lanes. The watcher greps by prefix; new emitters must
pick a new prefix.
