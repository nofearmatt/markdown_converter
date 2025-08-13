import pytest

from app.adapters import detect_source_format, normalize_conversation


def test_detect_aistudio():
    data = {'runSettings': {'model': 'g'}, 'messages': [{'role': 'user', 'content': 'hi'}]}
    assert detect_source_format(data) == 'aistudio'


def test_detect_chatgpt():
    data = {'mapping': {}, 'title': 'Chat'}
    assert detect_source_format(data) == 'chatgpt'


def test_detect_claude_like():
    data = {'messages': [{'role': 'assistant', 'content': [{'text': 'hey'}]}]}
    assert detect_source_format(data) in ('claude', 'unknown')


def test_normalize_aistudio_messages():
    data = {'messages': [{'role': 'user', 'content': 'hi'}, {'role': 'assistant', 'content': [{'text': 'ok'}]}]}
    msgs = normalize_conversation(data, prefer='aistudio')
    assert len(msgs) == 2
    assert msgs[0]['role'] == 'user'
    assert 'hi' in msgs[0]['content']


def test_normalize_claude_like():
    data = {'messages': [{'role': 'assistant', 'content': [{'text': 'hey'}], 'timestamp': 't'}]}
    msgs = normalize_conversation(data, prefer='claude')
    assert len(msgs) == 1
    assert msgs[0]['role'] == 'assistant'
    assert 'hey' in msgs[0]['content']


def test_normalize_chatgpt_empty_mapping():
    data = {'mapping': {}, 'title': 'Chat'}
    msgs = normalize_conversation(data, prefer='chatgpt')
    assert isinstance(msgs, list)
    assert len(msgs) == 0