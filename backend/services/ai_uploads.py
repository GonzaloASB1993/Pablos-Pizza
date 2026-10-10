"""Images attached to the AI chat: validation of the bytes and private storage.

Originals are stored under `ai_uploads/{uid}/{uuid}.{ext}` through the Admin
SDK. storage.rules denies all client access to that prefix, so they are never
public; the path is linked from the pending action as evidence.
"""
import base64
import binascii
import uuid

EXTENSIONS = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/gif': 'gif'}


class InvalidImage(ValueError):
    pass


def _matches_magic(media_type, data):
    if media_type == 'image/jpeg':
        return data[:3] == b'\xff\xd8\xff'
    if media_type == 'image/png':
        return data[:8] == b'\x89PNG\r\n\x1a\n'
    if media_type == 'image/webp':
        return data[:4] == b'RIFF' and data[8:12] == b'WEBP'
    if media_type == 'image/gif':
        return data[:6] in (b'GIF87a', b'GIF89a')
    return False


def extract_images(messages):
    """Decoded images of the LAST message (the only one that keeps them)"""
    images = []
    for block in messages[-1]['content']:
        if block['type'] != 'image':
            continue
        media_type = block['source']['media_type']
        try:
            data = base64.b64decode(block['source']['data'], validate=True)
        except (binascii.Error, ValueError):
            raise InvalidImage('La imagen no está bien codificada')
        if not _matches_magic(media_type, data):
            raise InvalidImage('El contenido de la imagen no coincide con su tipo')
        images.append((media_type, data))
    return images


def store_images(bucket, uid, images):
    """Upload to private storage and return [{'path', 'media_type', 'size'}]"""
    attachments = []
    for media_type, data in images:
        path = f"ai_uploads/{uid}/{uuid.uuid4()}.{EXTENSIONS[media_type]}"
        bucket.blob(path).upload_from_string(data, content_type=media_type)
        attachments.append({'path': path, 'media_type': media_type, 'size': len(data)})
    return attachments
