#!/usr/bin/env bash
# Disable the stock fixed-threshold (5 s) span-duration monitors of the open-telemetry StackPack;
# GenAI Insights replaces them with baseline-relative monitors. Needs an `sts` context for the target hub.
# Usage: scripts/disable-generic-otel-span-monitors.sh [--dry-run]
set -euo pipefail
names=("Span duration for Open Telemetry services"
       "Span duration for Open Telemetry service instances"
       "Span duration for pods")
list=$(sts monitor list -o json)
for n in "${names[@]}"; do
  id=$(python3 -I -c '
import json,sys
want=sys.argv[1]
def walk(o):
    if isinstance(o,dict):
        if o.get("name")==want and o.get("identifier"): yield o["identifier"]
        for v in o.values(): yield from walk(v)
    elif isinstance(o,list):
        for v in o: yield from walk(v)
print(next(walk(json.load(sys.stdin)),""))' "$n" <<<"$list")
  [[ -n "$id" ]] || { echo "not found: $n" >&2; continue; }
  echo "disable: $n -> $id"
  [[ "${1:-}" == "--dry-run" ]] || sts monitor disable --identifier "$id"
done
