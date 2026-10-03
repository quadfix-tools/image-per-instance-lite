#!/bin/bash
cd "$(dirname "$0")/.."
for B in /Applications/Blender.app ~/Applications/blender-versions/Blender-4.2.23.app ~/Applications/blender-versions/Blender-4.5.14.app; do
  T=$(mktemp -d); echo "== $B"
  "$B/Contents/MacOS/Blender" -b -P tests/test_lite.py -- "$PWD" "$T" 2>&1 | grep -E "RESULT|ALL PASS|Traceback|Error:|Assertion" | head -6
done
