"""Tests for chat image validation/storage and its wiring in the endpoint"""
import base64
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import ai_chat_routes  # noqa: E402
from services.ai_uploads import InvalidImage, extract_images, store_images  # noqa: E402
from tests.test_ai_chat_routes import _admin, fake_client, client  # noqa: E402,F401

JPEG = b'\xff\xd8\xff\xe0' + b'0' * 20
PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 20


def _msg(data, media_type='image/jpeg'):
    b64 = base64.b64encode(data).decode()
    return [{'role': 'user', 'content': [
        {'type': 'text', 'text': 'boleta'},
        {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': b64}}]}]


class FakeBucket:
    def __init__(self):
        self.uploaded = {}

    def blob(self, path):
        def upload(data, content_type=None):
            self.uploaded[path] = (data, content_type)
        return SimpleNamespace(upload_from_string=upload)


def test_extract_images_decodes_bytes():
    assert extract_images(_msg(JPEG)) == [('image/jpeg', JPEG)]


def test_extract_rejects_mismatched_or_broken_content():
    with pytest.raises(InvalidImage):
        extract_images(_msg(PNG, 'image/jpeg'))          # PNG bytes labelled as JPEG
    with pytest.raises(InvalidImage):
        extract_images(_msg(b'<svg onload=alert(1)>'))   # not an image at all
    broken = _msg(JPEG)
    broken[0]['content'][1]['source']['data'] = '%%%not-base64%%%'
    with pytest.raises(InvalidImage):
        extract_images(broken)


def test_store_images_uses_private_per_user_path():
    bucket = FakeBucket()
    attachments = store_images(bucket, 'u1', [('image/jpeg', JPEG), ('image/png', PNG)])
    assert [a['media_type'] for a in attachments] == ['image/jpeg', 'image/png']
    assert all(a['path'].startswith('ai_uploads/u1/') for a in attachments)
    assert attachments[0]['path'].endswith('.jpg') and attachments[1]['path'].endswith('.png')
    assert bucket.uploaded[attachments[0]['path']] == (JPEG, 'image/jpeg')


def test_endpoint_stores_image_and_sends_it_to_the_model(client, fake_client, monkeypatch):
    _admin(monkeypatch)
    bucket = FakeBucket()
    monkeypatch.setattr(ai_chat_routes, 'get_storage_bucket', lambda: bucket)
    res = client.post('/api/ai-chat/', json={'messages': _msg(JPEG)}, headers={'Authorization': 'Bearer t'})
    assert res.status_code == 200
    assert len(bucket.uploaded) == 1 and next(iter(bucket.uploaded)).startswith('ai_uploads/u1/')
    sent = fake_client.messages.calls[0]['messages'][-1]['content']
    assert sent[1]['type'] == 'image'


def test_endpoint_rejects_fake_image(client, fake_client, monkeypatch):
    _admin(monkeypatch)
    monkeypatch.setattr(ai_chat_routes, 'get_storage_bucket', lambda: FakeBucket())
    res = client.post('/api/ai-chat/', json={'messages': _msg(b'not an image')}, headers={'Authorization': 'Bearer t'})
    assert res.status_code == 400
    assert fake_client.messages.calls == []


def test_storage_failure_does_not_block_the_chat(client, fake_client, monkeypatch):
    _admin(monkeypatch)

    def boom():
        raise RuntimeError('storage down')

    monkeypatch.setattr(ai_chat_routes, 'get_storage_bucket', boom)
    res = client.post('/api/ai-chat/', json={'messages': _msg(JPEG)}, headers={'Authorization': 'Bearer t'})
    assert res.status_code == 200
