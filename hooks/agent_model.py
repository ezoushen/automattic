#!/usr/bin/env python3
"""PreToolUse hook: an Agent launch names its model, unless its definition pins one.

Without a model, Claude Code runs helpers on the session's model, usually the most
expensive one. Set AUTOMATTIC_AGENT_MODEL_HOOK=off to disable the check.
"""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
# Built-in agents that follow the session model when no model is passed.
INHERITING_BUILTINS = {None, '', 'general-purpose', 'Explore', 'Plan', 'claude'}
REASON = (
    'Pass an explicit `model` to this Agent call; without it the subagent runs on the session model. '
    'Choose the cheapest adequate one: haiku for search, lookups and summaries; sonnet for research, '
    'review and bounded implementation; opus only for hard design, adversarial review or deep diagnosis. '
    'Automattic role workers are routed with agent_models.py first.'
)

ROLE_REASON = ('An Automattic role worker needs its assignment fields: pass absolute `adapter`, `role_file` and '
               '`plugin_root` in the prompt (see the host adapter and the dispatch launch template).')


def field(path, name):
    """Return a front-matter field of an agent definition, unquoted, or None."""
    front = re.match(r'---\n(.*?)\n---', path.read_text(errors='replace'), re.S)
    match = front and re.search(rf'^{name}:\s*(.+)$', front.group(1), re.M)
    return match.group(1).strip().strip('"\'') if match else None


def pinned_model(path):
    model = field(path, 'model')
    return model.split()[0] if model else None


def tools(path):
    value = field(path, 'tools')
    return {tool.strip() for tool in value.split(',')} if value else None


def stale_profile(name, cwd):
    """Return why a generated `automattic-<role>-<digest>` profile no longer matches its role, or None."""
    match = re.fullmatch(r'automattic-([a-z0-9-]+)-[0-9a-f]{12}', name)
    role = match and ROOT / 'agents' / f'{match.group(1)}.md'
    profile = match and definition(name, cwd)
    if not (profile and role.is_file()) or None in (tools(profile), tools(role)) or tools(profile) == tools(role):
        return None
    missing, extra = sorted(tools(role) - tools(profile)), sorted(tools(profile) - tools(role))
    return (f'{profile} was rendered from an older `agents/{match.group(1)}.md`: its tools differ '
            f'(missing: {", ".join(missing) or "none"}; extra: {", ".join(extra) or "none"}). Re-render it with '
            f'`agent_models.py --route ... --profile` as {ROOT}/harnesses/claude/adapter.md describes, and launch '
            f'the name it returns.')


def definition(name, cwd):
    """Return the agent definition file for a subagent name, or None when unknown."""
    if ':' in name:
        plugin, agent = name.split(':', 1)
        manifest = ROOT / '.claude-plugin/plugin.json'
        if manifest.is_file() and json.loads(manifest.read_text()).get('name') == plugin:
            candidates = [ROOT / 'agents' / f'{agent}.md']
        else:
            candidates = sorted((Path.home() / '.claude/plugins/cache').glob(f'*/{plugin}/*/agents/{agent}.md'))
    else:
        candidates = [Path(cwd) / '.claude/agents' / f'{name}.md', Path.home() / '.claude/agents' / f'{name}.md']
    return next((path for path in candidates if path.is_file()), None)


def main():
    if os.environ.get('AUTOMATTIC_AGENT_MODEL_HOOK') == 'off':
        return
    try:
        event = json.load(sys.stdin)
        if event.get('tool_name') not in ('Agent', 'Task'):
            return
        tool_input = event.get('tool_input') or {}
        subagent = tool_input.get('subagent_type') or ''
        if re.fullmatch(r'automattic(:[a-z0-9-]+|-[a-z0-9-]+-[0-9a-f]{12})', subagent) \
                and 'role_file' not in (tool_input.get('prompt') or ''):
            deny(ROLE_REASON)
            return
        stale = stale_profile(subagent, event.get('cwd') or os.getcwd())
        if stale:
            deny(stale)
            return
        if tool_input.get('model'):
            return
        subagent = tool_input.get('subagent_type')
        if subagent == 'fork':
            return  # Forks always share the parent's model and context.
        if subagent not in INHERITING_BUILTINS:
            path = definition(subagent, event.get('cwd') or os.getcwd())
            if path is None or pinned_model(path) not in (None, 'inherit'):
                return  # Unknown definitions are not blocked; pinned ones choose their own model.
    except Exception:
        return  # A broken check must never block work.
    deny(REASON)


def deny(reason):
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': reason}}))


if __name__ == '__main__':
    main()
