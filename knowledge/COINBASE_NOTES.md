# Coinbase module — REAL MONEY, disabled by default

`desk/execute.py` (spot) and `desk/btc_desk.py`/`btc_qualify.py` drive
Coinbase Advanced. There is NO practice mode. Do not enable this because it
seems useful; enable it because your user read this file and said so.

- Fees: taker fees on a small account eat most intraday edges. Maker-only
  exits (limit orders resting) where the venue allows.
- The measured record that parked it here: a ~$100 account netted −$4.31
  with $1.51 fees on one closed round trip. The edge must clear fees ×2.
- Enabling: uncomment the COINBASE_ADV_* lines in `.env`, and your user must
  write the enablement into MANDATE.md in their own words.
- Sizing rules, qualification gates, and the paper-desk simulator
  (`desk/paper.py` — reproduces fees against live 1-min bars) all still
  apply. Run paper first. The paper ledger is never mixed with real fills.
