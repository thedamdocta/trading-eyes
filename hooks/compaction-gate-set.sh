#!/bin/bash
# PreCompact hook: arm the gate so the next session saves its summary first.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
date "+%A %Y-%m-%d %H:%M:%S" > "$DIR/memory/.compaction-pending"
