#!/bin/bash
# Reporting cadence (the operator, 2026-08-31): FLAT -> one report every 5 MINUTES.
# IN A TRADE -> every 1-min bar, so price action / structure / volume drive
# the exit. Fills and closes announced the moment they happen.
DESK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN="$DESK/../run"; mkdir -p "$RUN"
FE="$DESK/fx_execute.py"
LOG="$RUN/desk.log"
CB="$DESK/execute.py"
BTCPLAN="$DESK/.btc_plan"
PB="$DESK/pos_bar.py"
FXPLAN="$DESK/.fx_plan"
prev="FLAT"; lastline=""; lastalert=""; flat_tick=0
MF="$DESK/manford.py"
# Paper desk (the operator, 2026-09-01 23:05: "reproduce the fees ... build a paper
# trade so you have more opportunities to trade something on Coinbase while
# you wait on forex"). `tick` processes simulated fills against closed 1-min
# bars and prints only events; a paper position gets the 1-min cadence.
PP="$DESK/paper.py"
mf_tick=0
# mf_lane INST OPEN_HHMM START_HHMM END_HHMM — one Manford session lane.
# Emits only NEW state-machine lines (diffed against a per-lane snapshot).
mf_lane() {
  local inst="$1" open="$2" start="$3" end="$4"
  local snap="/tmp/.manford_watch_snap_${inst}"
  if [ "$et_now" -ge "$start" ] && [ "$et_now" -le "$end" ]; then
    if [ $((mf_tick % 4)) -eq 0 ]; then
      mfout=$(python3 "$MF" "$inst" "$open" 2>/dev/null | grep -E "ZONE|BREAKOUT|RETEST|FAILED|COMPLETE|entry |secondary")
      if [ -n "$mfout" ]; then
        # grep -v exits 1 when it filters everything out — that is "nothing
        # new", not an error. Only a missing snapshot means "all lines are new".
        if [ -f "$snap" ]; then
          newlines=$(echo "$mfout" | grep -Fxv -f "$snap" 2>/dev/null || true)
        else
          newlines="$mfout"
        fi
        if [ -n "$newlines" ]; then
          echo "MANFORD $inst $open !!"
          echo "$newlines"
        fi
        echo "$mfout" > "$snap"
      fi
    fi
  fi
}

while true; do
  # MANFORD lane (the operator approved 2026-09-01): faithful session-open detector,
  # BTC at the 09:30 ET equities open (backtest: +1.14R/signal, n=5; FX NY
  # opens tested NEGATIVE and are excluded). Poll ~2min inside 09:30-13:30 ET
  # weekdays; emit only NEW state-machine events. Signals are advisory —
  # the agent hand-verifies and executes through the futures machinery.
  # London lane added 15:58 ET 2026-09-01 (alerts only, the operator at work): USD_JPY
  # at the 03:00 ET London open. 15-day backtest +0.56R/signal (n=6) on real
  # 4-20p stops. EUR_GBP looked best (+1.86R) but on 1-3p stops the spread eats
  # ~65% of R — excluded. BTC 03:00 (+0.18R) and NY FX (negative) excluded.
  # Bull signals above 160 are vetoed by the MoF intervention rule at hand-check.
  et_now=$((10#$(TZ=America/New_York date +%H%M)))
  et_dow=$(TZ=America/New_York date +%u)
  if [ "$et_dow" -le 5 ]; then
    mf_lane BTC 09:30 930 1330
    mf_lane USD_JPY 03:00 300 700
    mf_tick=$((mf_tick+1))
  fi
  pos=$(python3 "$FE" positions 2>/dev/null)
  # FLAT requires the explicit "no open positions" string. Absence of output
  # (an API hiccup) previously read as FLAT and printed a false POSITION CLOSED
  # while openTrades=1 (2026-09-01 00:29). Unknown -> keep previous state.
  if echo "$pos" | grep -q "units"; then state="OPEN"
  elif echo "$pos" | grep -q "no open positions"; then state="FLAT"
  else state="$prev"; fi
  if [ "$state" != "$prev" ]; then
    # BTC: the moment a buy fills, place the SERVER-SIDE bracket. Coinbase has no
  # trailing stop, so an unbracketed position depends on this session staying
  # alive — auto-arming closes the window between fill and protection.
  if [ -f "$BTCPLAN" ]; then
    held=$(python3 "$CB" balance 2>/dev/null | sed -n 's/.*BTC \([0-9.]*\) .*/\1/p')
    if [ -n "$held" ] && [ "$(echo "$held > 0.00000001" | bc -l 2>/dev/null)" = "1" ]; then
      read -r btgt bstop < "$BTCPLAN"
      echo "!! BTC FILLED — arming server-side bracket target $btgt stop $bstop"
      python3 "$CB" bracket all "$btgt" "$bstop" 2>&1 | head -2
      rm -f "$BTCPLAN"
    fi
  fi

  # IMMEDIATE alerts, any cadence: new qualifying-pair or blindness lines
  na=$(grep -nE "FX !!|BLIND|STALE" "$LOG" | tail -1)
  if [ -n "$na" ] && [ "$na" != "$lastalert" ]; then
    echo "ALERT ${na#*:}"
    lastalert="$na"
  fi
  if [ "$state" = "OPEN" ]; then echo "!! FILLED — position open: $pos"
      if [ -f "$FXPLAN" ]; then
        read -r ppair pside phalf ptp < "$FXPLAN"
        echo "!! placing partial TP: $pside $phalf $ppair @ $ptp"
        if [ "$pside" = "buy" ]; then
          python3 "$FE" limitbuy "$ppair" "$phalf" "$ptp" 2>&1 | head -1
        else
          python3 "$FE" limitsell "$ppair" "$phalf" "$ptp" 2>&1 | head -1
        fi
        rm -f "$FXPLAN"
      fi
    else echo "!! POSITION CLOSED — $(python3 "$FE" balance 2>/dev/null)"
      # A closed position ORPHANS its partial-TP order — with nothing behind it,
      # that reduce order becomes a fresh ENTRY if it fills (found 2026-09-01
      # 01:06: trail closed the short, the 256u partial buy kept resting). One
      # position at a time on this desk, so cancel all pending on close.
      python3 "$FE" cancel all 2>/dev/null | head -2
      rm -f "$FXPLAN"
    fi
    prev="$state"; flat_tick=0
  fi
  pev=$(python3 "$PP" tick 2>/dev/null); [ -n "$pev" ] && echo "$pev"
  pstate=$(python3 "$PP" state 2>/dev/null)
  if [ "$state" = "OPEN" ]; then
    # Report the bar for the instrument ACTUALLY HELD, not the one the chart
    # capture happens to be watching (2026-08-31: held AUD/USD while every
    # in-trade line described USD/JPY).
    nl=$(python3 "$PB" 2>/dev/null)
    if [ "$nl" != "$lastline" ] && [ -n "$nl" ]; then
      echo "IN-TRADE $nl"
      lastline="$nl"
    fi
    sleep 55
  else
    # a paper position is a trade for cadence purposes: 1-min lines while it
    # lives, so the same bar-by-bar exit discipline applies to the paper book
    if [ "$pstate" = "OPEN" ] && [ $((flat_tick % 2)) -eq 0 ]; then
      echo "IN-PAPER $(date '+%H:%M') $(python3 "$PP" status 2>/dev/null)"
    fi
    # flat: report every 5 minutes (10 x 30s)
    if [ $((flat_tick % 10)) -eq 0 ]; then
      # "focus" = the chart capture's pair; "basket" = the full gate-band scan
      # (the operator 2026-09-01: "it seems like you may be doing only one pair")
      bar=$(grep "^FX USD_JPY" "$LOG" | tail -1)
      scan=$(grep "^FX SCAN" "$LOG" | tail -1)
      ords=$(python3 "$FE" orders 2>/dev/null | tail -1)
      btc=$(python3 "$CB" balance 2>/dev/null)
      bord=$(python3 "$CB" orders 2>/dev/null | head -1)
      echo "5MIN BTC $btc"
      echo "     BTC order: $bord | $(python3 "$PP" status 2>/dev/null)"
      echo "     FX focus ${bar#FX }"
      echo "     FX basket ${scan#FX SCAN } | fx orders: $ords"
    fi
    flat_tick=$((flat_tick+1))
    sleep 30
  fi
done
