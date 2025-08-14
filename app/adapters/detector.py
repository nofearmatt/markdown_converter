# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Any


def detect_source_format(data: Dict[str, Any]) -> str:
    """Грубая эвристика определения формата: aistudio | chatgpt | claude | unknown"""
    if not isinstance(data, dict):
        return 'unknown'

    # AI Studio: часто встречаются run_settings/runSettings, chunkedPrompt, systemInstruction
    if any(k in data for k in ('run_settings', 'runSettings', 'chunkedPrompt', 'systemInstruction')):
        return 'aistudio'

    # ChatGPT official export: top-level keys like 'title', 'mapping', 'current_node'
    if any(k in data for k in ('mapping', 'current_node')):
        return 'chatgpt'

    # Claude: часто messages: [{role: 'user'|'assistant'}] + 'uuid'/'conversation_uuid' и т.п.
    if 'messages' in data and isinstance(data['messages'], list):
        roles = [m.get('role') for m in data['messages'] if isinstance(m, dict)]
        if any(r in ('user', 'assistant') for r in roles):
            return 'claude'

    return 'unknown'