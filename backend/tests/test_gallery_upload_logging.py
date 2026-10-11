"""The gallery upload route must never log request headers (they carry Authorization bearer tokens)"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402

SECRET = 'Bearer SUPER-SECRET-ID-TOKEN-123'


def test_authorization_header_is_not_logged(capsys, caplog):
    main.limiter.enabled = False
    main.app.config['TESTING'] = True
    client = main.app.test_client()
    with caplog.at_level(logging.DEBUG):
        client.post('/api/gallery/upload', headers={'Authorization': SECRET}, data={})
    out = capsys.readouterr()
    assert 'SUPER-SECRET-ID-TOKEN-123' not in out.out + out.err + caplog.text
