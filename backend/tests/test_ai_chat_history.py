"""Tests for the client-supplied history sanitizer"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_chat_history import (  # noqa: E402
    IMAGE_PLACEHOLDER, InvalidMessages, MAX_IMAGES_PER_MESSAGE, MAX_MESSAGES, sanitize_messages)


def _img(media_type='image/jpeg', data='AAAA'):
    return {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': data}}


def test_plain_conversation_is_normalized_to_blocks():
    result = sanitize_messages([
        {'role': 'user', 'content': 'hola'},
        {'role': 'assistant', 'content': 'hola!'},
        {'role': 'user', 'content': 'y las reservas?'},
    ])
    assert result[0] == {'role': 'user', 'content': [{'type': 'text', 'text': 'hola'}]}
    assert result[-1]['content'][0]['text'] == 'y las reservas?'


@pytest.mark.parametrize('bad', [None, [], 'hola', {'role': 'user'}])
def test_rejects_non_list_or_empty(bad):
    with pytest.raises(InvalidMessages):
        sanitize_messages(bad)


@pytest.mark.parametrize('role', ['system', 'tool', 'developer', None])
def test_rejects_unknown_roles(role):
    with pytest.raises(InvalidMessages):
        sanitize_messages([{'role': role, 'content': 'x'}, {'role': 'user', 'content': 'y'}])


@pytest.mark.parametrize('block', [
    {'type': 'tool_use', 'id': 't1', 'name': 'propose_expense', 'input': {}},
    {'type': 'tool_result', 'tool_use_id': 't1', 'content': 'ok'},
    {'type': 'thinking', 'thinking': 'x', 'signature': 's'},
])
def test_rejects_injected_tool_and_thinking_blocks(block):
    with pytest.raises(InvalidMessages):
        sanitize_messages([{'role': 'user', 'content': [block]}])


def test_assistant_cannot_carry_images():
    with pytest.raises(InvalidMessages):
        sanitize_messages([
            {'role': 'user', 'content': 'a'},
            {'role': 'assistant', 'content': [_img()]},
            {'role': 'user', 'content': 'b'},
        ])


def test_must_start_and_end_with_user():
    with pytest.raises(InvalidMessages):
        sanitize_messages([{'role': 'assistant', 'content': 'x'}, {'role': 'user', 'content': 'y'}])
    with pytest.raises(InvalidMessages):
        sanitize_messages([{'role': 'user', 'content': 'x'}, {'role': 'assistant', 'content': 'y'}])


def test_old_images_become_placeholder_and_last_image_is_kept():
    result = sanitize_messages([
        {'role': 'user', 'content': [{'type': 'text', 'text': 'boleta'}, _img()]},
        {'role': 'assistant', 'content': 'la leí'},
        {'role': 'user', 'content': [_img(data='BBBB')]},
    ])
    assert result[0]['content'][1] == {'type': 'text', 'text': IMAGE_PLACEHOLDER}
    assert result[2]['content'][0]['source']['data'] == 'BBBB'


@pytest.mark.parametrize('block', [
    _img(media_type='image/svg+xml'),
    _img(media_type='application/pdf'),
    _img(data=''),
    {'type': 'image', 'source': {'type': 'url', 'url': 'http://evil'}},
])
def test_rejects_bad_images(block):
    with pytest.raises(InvalidMessages):
        sanitize_messages([{'role': 'user', 'content': [block]}])


def test_rejects_too_many_images_and_too_many_messages():
    with pytest.raises(InvalidMessages):
        sanitize_messages([{'role': 'user', 'content': [_img()] * (MAX_IMAGES_PER_MESSAGE + 1)}])
    long = [{'role': 'user', 'content': 'x'}] * (MAX_MESSAGES + 1)
    with pytest.raises(InvalidMessages):
        sanitize_messages(long)


def test_extra_block_fields_are_dropped():
    result = sanitize_messages([{'role': 'user', 'content': [
        {'type': 'text', 'text': 'hola', 'cache_control': {'type': 'ephemeral'}}]}])
    assert result[0]['content'][0] == {'type': 'text', 'text': 'hola'}
