#!/bin/bash
pkill -f "fx_desk.py" && echo "stopped fx_desk" || echo "fx_desk not running"
pkill -f "fx_scan.py" && echo "stopped fx_scan" || echo "fx_scan not running"
pkill -f "trade_watch.sh" && echo "stopped watcher" || echo "watcher not running"
echo "coil logger loop dies with its Monitor; kill it from the agent (TaskStop)."
