"""Small, validated, local-only identity/preferences and recent text context store."""
from __future__ import annotations
import copy
import json
import os
import tempfile
import time
import uuid
from pathlib import Path

DEFAULT_IDENTITY = {'name': '灵犀', 'role': '陪伴用户的桌面机器人，可以聊天、按需看画面，并通过预设接口控制底盘。',
                    'style': '温柔、自然、有分寸。通常用一至三句中文回答，避免机械地复述观察清单。', 'notes': ''}
PREFERENCES = {'nickname': '用户称呼', 'reminder_tone': '提醒语气', 'motion_intensity': '动作轻重', 'rest_style': '休息偏好'}


def fields(value, limits):
    if not isinstance(value, dict) or set(value) != set(limits):
        raise ValueError('字段不完整或包含未知字段')
    result = {}
    for key, limit in limits.items():
        text = value[key]
        if not isinstance(text, str) or len(text) > limit or '\x00' in text:
            raise ValueError(f'{key} 内容无效或超过 {limit} 字')
        result[key] = text.strip()
    return result


class MemoryStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.data = {'version': 1, 'revision': 0, 'contextRevision': 0,
                     'identity': dict(DEFAULT_IDENTITY), 'preferences': {k: '' for k in PREFERENCES}, 'history': []}
        if self.path and self.path.exists():
            raw = json.loads(self.path.read_text())
            self.data['identity'] = fields(raw['identity'], {'name': 40, 'role': 1000, 'style': 1000, 'notes': 3000})
            if not self.data['identity']['name']:
                raise ValueError('机器人名字不能为空')
            self.data['preferences'] = fields(raw['preferences'], {k: 300 for k in PREFERENCES})
            history = raw['history']
            if not isinstance(history, list) or len(history) > 24:
                raise ValueError('本地对话记录格式无效')
            for item in history:
                if item['role'] not in ('user', 'assistant') or not isinstance(item['text'], str) or len(item['text']) > 1200:
                    raise ValueError('本地对话记录格式无效')
                if not isinstance(item['id'], str) or not isinstance(item['at'], (int, float)):
                    raise ValueError('本地对话标识无效')
            self.data['history'] = history
            for key in ('revision', 'contextRevision'):
                if type(raw[key]) is not int or raw[key] < 0:
                    raise ValueError('本地版本号无效')
                self.data[key] = raw[key]

    def commit(self, data):
        # Replace only after a complete write; an I/O failure leaves RAM unchanged.
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix='.lingxi-memory-', dir=self.path.parent)
            try:
                with os.fdopen(fd, 'w') as file:
                    json.dump(data, file, ensure_ascii=False, indent=2)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(tmp, self.path)  # mkstemp is private (0600)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        self.data = data

    def settings(self, identity, preferences, revision):
        if revision != self.data['revision']:
            raise RuntimeError('设置已变化，请重新载入后保存；你的输入仍保留在页面中')
        identity = fields(identity, {'name': 40, 'role': 1000, 'style': 1000, 'notes': 3000})
        preferences = fields(preferences, {k: 300 for k in PREFERENCES})
        if not identity['name']:
            raise ValueError('机器人名字不能为空')
        data = copy.deepcopy(self.data)
        data.update(identity=identity, preferences=preferences, revision=data['revision']+1)
        self.commit(data)

    def remember(self, key, value):
        if not isinstance(key, str) or key not in PREFERENCES or not isinstance(value, str) or not value.strip() or len(value) > 300:
            raise ValueError('只允许保存四种明确偏好，每项最多 300 字')
        data = copy.deepcopy(self.data)
        data['preferences'][key] = value.strip()
        data['revision'] += 1
        self.commit(data)

    def append(self, role, text):
        if role not in ('user', 'assistant'):
            raise ValueError('无效角色')
        data = copy.deepcopy(self.data)
        data['history'].append({'id': uuid.uuid4().hex, 'role': role, 'text': text[:1200], 'at': time.time()})
        data['history'] = data['history'][-24:]
        self.commit(data)

    def edit(self, item_id, previous, text):
        if text is not None and (not isinstance(text, str) or len(text) > 1200 or not text.strip()):
            raise ValueError('对话内容须为 1–1200 字')
        data = copy.deepcopy(self.data)
        item = next((i for i in data['history'] if i['id'] == item_id), None)
        if item is None or item['text'] != previous:
            raise RuntimeError('该条对话已变化或不存在，请刷新对话列表')
        if text is None:
            data['history'].remove(item)
        else:
            item['text'] = text.strip()
        data['contextRevision'] += 1
        self.commit(data)

    def clear(self):
        data = copy.deepcopy(self.data)
        data['history'] = []
        data['contextRevision'] += 1
        self.commit(data)

    def pairs(self):
        return [(item['role'], item['text']) for item in self.data['history']]

    def instructions(self):
        identity = self.data['identity']
        prefs = '\n'.join(f'{label}：{self.data["preferences"][key] or "尚未设置，不要臆测"}' for key, label in PREFERENCES.items())
        return (f'你的名字是{identity["name"]}。\n角色：{identity["role"]}\n表达方式：{identity["style"]}\n'
                f'补充设定：{identity["notes"] or "无"}\n用户明确偏好：\n{prefs}\n'
                '用户明确要求记住或修改上述四种偏好时，调用 remember 保存，不从照片、情绪或随口提及推断偏好。'
                '只有保存成功才确认已记住；其他内容仅作为最近对话上下文，不宣称永久记忆。'
                '动作轻重偏好不改变底盘安全限制，也不代表底盘已经实现相应幅度。\n')
