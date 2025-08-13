import json
from pathlib import Path

from app.adapters import detect_source_format, normalize_conversation

FIXTURES = Path(__file__).parent / 'fixtures'


def test_chatgpt_fixture_normalization():
    data = json.loads((FIXTURES / 'chatgpt_sample.json').read_text(encoding='utf-8'))
    assert detect_source_format(data) == 'chatgpt'
    msgs = normalize_conversation(data, prefer='chatgpt')
    # Expect 2 messages, user then assistant
    roles = [m['role'] for m in msgs]
    assert roles == ['user', 'assistant']
    assert 'Hello from user' in msgs[0]['content']
    assert 'ChatGPT' in msgs[1]['content']


def test_claude_fixture_normalization():
    data = json.loads((FIXTURES / 'claude_sample.json').read_text(encoding='utf-8'))
    fmt = detect_source_format(data)
    assert fmt in ('claude', 'unknown')
    msgs = normalize_conversation(data, prefer='claude')
    assert [m['role'] for m in msgs] == ['user', 'assistant']
    assert 'Hi Claude' in msgs[0]['content']
    assert 'Hello human' in msgs[1]['content']