"""Sanitization of the conversation history sent by the browser.

The server is stateless: the client resends the whole conversation on every
request, so nothing in it can be trusted. Only plain user/assistant text and
user images are accepted; tool_use / tool_result / thinking / system content
injected from the client is rejected, and block metadata is rebuilt from
scratch instead of being forwarded.
"""

ALLOWED_ROLES = ('user', 'assistant')
ALLOWED_IMAGE_TYPES = ('image/jpeg', 'image/png', 'image/webp', 'image/gif')

MAX_MESSAGES = 40
MAX_TEXT_CHARS = 20_000
MAX_IMAGES_PER_MESSAGE = 3
MAX_IMAGE_BASE64_CHARS = 5_500_000  # ~4 MB of binary data per image

IMAGE_PLACEHOLDER = '[imagen enviada]'


class InvalidMessages(ValueError):
    """The client sent a conversation that must be rejected (HTTP 400)"""


def _clean_text(value, where):
    if not isinstance(value, str):
        raise InvalidMessages(f'{where}: el texto debe ser una cadena')
    if len(value) > MAX_TEXT_CHARS:
        raise InvalidMessages(f'{where}: el texto es demasiado largo')
    return value


def _clean_image(block, where):
    source = block.get('source')
    if not isinstance(source, dict) or source.get('type') != 'base64':
        raise InvalidMessages(f'{where}: la imagen debe venir en base64')
    media_type = source.get('media_type')
    if media_type not in ALLOWED_IMAGE_TYPES:
        raise InvalidMessages(f'{where}: tipo de imagen no permitido')
    data = source.get('data')
    if not isinstance(data, str) or not data:
        raise InvalidMessages(f'{where}: imagen vacía')
    if len(data) > MAX_IMAGE_BASE64_CHARS:
        raise InvalidMessages(f'{where}: la imagen es demasiado grande')
    return {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': data}}


def _clean_blocks(role, content, where):
    if isinstance(content, str):
        return [{'type': 'text', 'text': _clean_text(content, where)}]

    if not isinstance(content, list) or not content:
        raise InvalidMessages(f'{where}: contenido inválido')

    cleaned = []
    for block in content:
        if not isinstance(block, dict):
            raise InvalidMessages(f'{where}: bloque inválido')
        block_type = block.get('type')
        if block_type == 'text':
            cleaned.append({'type': 'text', 'text': _clean_text(block.get('text'), where)})
        elif block_type == 'image' and role == 'user':
            cleaned.append(_clean_image(block, where))
        else:
            raise InvalidMessages(f'{where}: tipo de bloque no permitido ({block_type})')
    return cleaned


def sanitize_messages(raw_messages):
    """Return a clean copy of the conversation or raise InvalidMessages.

    Images are kept only in the last message; earlier turns get a text
    placeholder so the conversation does not re-pay image tokens every turn.
    """
    if not isinstance(raw_messages, list) or not raw_messages:
        raise InvalidMessages('No messages provided')
    if len(raw_messages) > MAX_MESSAGES:
        raise InvalidMessages('La conversación es demasiado larga')

    last_index = len(raw_messages) - 1
    messages = []
    for index, message in enumerate(raw_messages):
        where = f'mensaje {index + 1}'
        if not isinstance(message, dict):
            raise InvalidMessages(f'{where}: formato inválido')
        role = message.get('role')
        if role not in ALLOWED_ROLES:
            raise InvalidMessages(f'{where}: rol no permitido')

        blocks = _clean_blocks(role, message.get('content'), where)

        if index != last_index:
            blocks = [
                {'type': 'text', 'text': IMAGE_PLACEHOLDER} if b['type'] == 'image' else b
                for b in blocks
            ]
        elif sum(1 for b in blocks if b['type'] == 'image') > MAX_IMAGES_PER_MESSAGE:
            raise InvalidMessages(f'Máximo {MAX_IMAGES_PER_MESSAGE} imágenes por mensaje')

        messages.append({'role': role, 'content': blocks})

    if messages[0]['role'] != 'user' or messages[-1]['role'] != 'user':
        raise InvalidMessages('La conversación debe empezar y terminar con un mensaje del usuario')
    return messages
