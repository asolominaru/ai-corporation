"""Offline audit: never loads .env and never contacts Telegram."""
import ast
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'KIMI  КОРПОРАЦИЯ/КОРПОРАЦИЯ'
source = ROOT / 'approval-bot/approvals.py'
tree = ast.parse(source.read_text())
# Load only imports/functions; bypass top-level TOKEN and all entry-point code.
safe_tree = ast.Module(body=[n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef))], type_ignores=[])
ns = {}
exec(compile(safe_tree, str(source), 'exec'), ns)
with tempfile.TemporaryDirectory(prefix='kimi-approval-audit-') as tmp:
    ns['STATE'] = str(Path(tmp) / 'state.json')
    ns['LOG'] = str(Path(tmp) / 'events.jsonl')
    ns['save_state']({'offset': 0, 'chat_id': 111})
    ns['log_event']({'type': 'request_sent', 'request_id': 'audit001', 'options': ['approve', 'reject']})
    updates = [
        {'update_id': 1, 'message': {'chat': {'id': 222}, 'from': {'id': 222}, 'text': '/start'}},
        {'update_id': 2, 'callback_query': {'id': 'cb1', 'from': {'id': 222}, 'message': {'chat': {'id': 222}}, 'data': 'audit001:0'}},
        {'update_id': 3, 'callback_query': {'id': 'cb2', 'from': {'id': 222}, 'message': {'chat': {'id': 222}}, 'data': 'audit001:1'}},
        {'update_id': 4, 'callback_query': {'id': 'cb3', 'from': {'id': 222}, 'message': {'chat': {'id': 222}}, 'data': 'unknown:0'}},
    ]
    calls = []
    def fake_call(method, **params):
        calls.append(method)
        return updates if method == 'getUpdates' else {}
    ns['call'] = fake_call
    ns['poll']()
    events = [json.loads(line) for line in Path(ns['LOG']).read_text().splitlines()]
    decisions = [e for e in events if e['type'] == 'decision']
    result = {
        'unrelated_message_replaces_owner_chat': ns['load_state']()['chat_id'] == 222,
        'non_owner_decision_logged': any(e['by'] == 222 for e in decisions),
        'same_request_accepts_conflicting_decisions': len([e for e in decisions if e['request_id'] == 'audit001']) == 2,
        'unknown_request_decision_logged': any(e['request_id'] == 'unknown' for e in decisions),
        'network_calls': 0,
        'real_credentials_loaded': False,
    }
    print(json.dumps(result, indent=2))
    assert all(result[k] for k in list(result)[:4]), 'Observed behavior changed; reassess findings'
