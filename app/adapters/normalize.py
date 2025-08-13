# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any, List

from .detector import detect_source_format


def _normalize_aistudio(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    msgs: List[Dict[str, Any]] = []
    # 1) messages
    if isinstance(data.get('messages'), list):
        for m in data['messages']:
            if not isinstance(m, dict):
                continue
            content = m.get('content') or m.get('text')
            if isinstance(content, list):
                # плоское склеивание
                flat = []
                for p in content:
                    if isinstance(p, dict) and isinstance(p.get('text'), str):
                        flat.append(p['text'])
                    elif isinstance(p, str):
                        flat.append(p)
                content = '\n'.join(flat)
            msgs.append({
                'role': (m.get('role') or '').lower(),
                'content': content or '',
                'timestamp': m.get('timestamp') or m.get('time'),
                'meta': {}
            })
    # 2) chunkedPrompt
    elif isinstance(data.get('chunkedPrompt', {}).get('chunks'), list):
        for ch in data['chunkedPrompt']['chunks']:
            if not isinstance(ch, dict):
                continue
            if ch.get('isThought'):
                continue
            content = ch.get('text')
            if not content and isinstance(ch.get('parts'), list):
                fragments = []
                for p in ch['parts']:
                    if isinstance(p, dict) and isinstance(p.get('text'), str):
                        fragments.append(p['text'])
                content = '\n'.join(fragments)
            msgs.append({
                'role': (ch.get('role') or 'assistant').lower(),
                'content': content or '',
                'timestamp': ch.get('timestamp') or ch.get('time'),
                'meta': {}
            })
    return msgs


def _normalize_chatgpt(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    msgs: List[Dict[str, Any]] = []
    mapping = data.get('mapping')
    if isinstance(mapping, dict):
        # ChatGPT official export: граф узлов, нужна топологическая/DFS
        # Упростим: соберем сообщения по порядку через parents
        visited = set()
        # найдем корневые узлы (без parent)
        roots = [k for k, v in mapping.items() if not (isinstance(v, dict) and v.get('parent'))]
        stack = roots[:]
        while stack:
            key = stack.pop()
            if key in visited:
                continue
            visited.add(key)
            node = mapping.get(key) or {}
            msg = (node.get('message') or {})
            author = ((msg.get('author') or {}).get('role') or '').lower()
            parts = msg.get('content', {}).get('parts') if isinstance(msg.get('content'), dict) else None
            text = ''
            if isinstance(parts, list):
                text = '\n'.join([p for p in parts if isinstance(p, str)])
            title = data.get('title')
            if author and text:
                msgs.append({
                    'role': 'assistant' if author == 'assistant' else ('user' if author == 'user' else author),
                    'content': text,
                    'timestamp': msg.get('create_time') or node.get('create_time'),
                    'meta': {'title': title}
                })
            # дети
            for ch in (node.get('children') or []):
                stack.append(ch)
    return msgs


def _normalize_claude(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    msgs: List[Dict[str, Any]] = []
    arr = data.get('messages')
    if isinstance(arr, list):
        for m in arr:
            if not isinstance(m, dict):
                continue
            role = (m.get('role') or '').lower()
            content = m.get('content')
            if isinstance(content, list):
                text_parts = []
                for p in content:
                    if isinstance(p, dict) and isinstance(p.get('text'), str):
                        text_parts.append(p['text'])
                    elif isinstance(p, str):
                        text_parts.append(p)
                content = '\n'.join(text_parts)
            if isinstance(content, str):
                msgs.append({
                    'role': role,
                    'content': content,
                    'timestamp': m.get('timestamp') or m.get('created_at'),
                    'meta': {}
                })
    return msgs


def normalize_conversation(data: Dict[str, Any], prefer: str = 'auto') -> List[Dict[str, Any]]:
    fmt = prefer if prefer and prefer != 'auto' else detect_source_format(data)
    if fmt == 'aistudio':
        return _normalize_aistudio(data)
    if fmt == 'chatgpt':
        out = _normalize_chatgpt(data)
        if out:
            return out
    if fmt == 'claude':
        out = _normalize_claude(data)
        if out:
            return out
    # fallback: messages[] простые
    generic = []
    if isinstance(data.get('messages'), list):
        for item in data['messages']:
            if not isinstance(item, dict):
                continue
            text = item.get('content') or item.get('text') or ''
            generic.append({
                'role': (item.get('role') or '').lower(),
                'content': text,
                'timestamp': item.get('timestamp') or item.get('time'),
                'meta': {}
            })
    return generic