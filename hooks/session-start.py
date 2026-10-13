#!/usr/bin/env python3
"""Supply the registered host adapter and applicable environment guidance."""
import argparse
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('harness', choices=('claude', 'codex'))
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
context = f'Automattic harness: {args.harness}. When using an Automattic skill, first read {root}/harnesses/{args.harness}/adapter.md. Plugin root: {root}. Load only this host adapter; pass its absolute path and the shared role file to workers.'
if os.environ.get('HERDR_ENV') == '1':
    context += f' Herdr environment detected: before delegation also read {root}/harnesses/herdr.md for routing, waits and cleanup.'
print(json.dumps({'hookSpecificOutput': {
    'hookEventName': 'SessionStart',
    'additionalContext': context
}}))
