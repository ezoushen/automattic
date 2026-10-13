"""Bounded image snapshots and retained assets for decision requests."""

import base64
import copy
import hashlib
import io
import os
from pathlib import Path
import stat
import tempfile
import warnings


MAX_IMAGES = 4
MAX_ENCODED_BYTES = 8 * 1024 * 1024
MAX_EVALUATION_BYTES = 32 * 1024 * 1024
MAX_SOURCE_BYTES = MAX_ENCODED_BYTES * 3 // 4
MAX_PIXELS = 4_194_304
MAX_DIMENSION = 4096
FORMATS = {'PNG': ('image/png', '.png'), 'JPEG': ('image/jpeg', '.jpg'), 'WEBP': ('image/webp', '.webp')}


def validate_references(images):
    if not isinstance(images, list) or not 1 <= len(images) <= MAX_IMAGES:
        raise ValueError('Supply 1–4 image references')
    for ref in images:
        if (not isinstance(ref, dict) or set(ref) != {'path', 'label'}
                or not isinstance(ref['path'], str) or not 1 <= len(ref['path']) <= 4096
                or '\x00' in ref['path'] or not Path(ref['path']).is_absolute()
                or not isinstance(ref['label'], str) or not ref['label'].strip() or len(ref['label']) > 240):
            raise ValueError('Each image requires an absolute path and a nonblank label of at most 240 characters')


def metadata(data):
    try:
        from PIL import Image
    except ImportError as error:
        raise ValueError('Image evidence requires Pillow; install requirements.txt in the plugin environment') from error
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                width, height = image.size
                if (image.format not in FORMATS or getattr(image, 'n_frames', 1) != 1
                        or width * height > MAX_PIXELS or max(width, height) > MAX_DIMENSION):
                    raise ValueError('Image must be a single PNG/JPEG/WebP frame, at most 4096 per side and 4194304 pixels')
                mime, _ = FORMATS[image.format]
                image.load()
    except (OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError(f'Invalid image evidence: {error}') from error
    return {'sha256': hashlib.sha256(data).hexdigest(), 'mime': mime, 'width': width, 'height': height}


def read_bytes(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NONBLOCK), 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('Image evidence must be a regular file')
        data = stream.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError('Image evidence exceeds the 8 MiB encoded budget')
    return data


def data_url(data, mime):
    return f'data:{mime};base64,' + base64.b64encode(data).decode('ascii')


def validate_wire(images):
    if (not isinstance(images, list) or not 1 <= len(images) <= MAX_IMAGES
            or any(not isinstance(url, str) or not url.isascii() for url in images)):
        raise ValueError('Wire images must be 1–4 data URLs')
    if sum(len(url) for url in images) > MAX_ENCODED_BYTES:
        raise ValueError('Image evidence exceeds the 8 MiB encoded budget')


def prepare(references):
    if references is None:
        return None
    validate_references(references)
    urls, evidence = [], []
    for ref in references:
        data = read_bytes(ref['path'])
        info = dict(metadata(data), label=ref['label'])
        urls.append(data_url(data, info['mime']))
        validate_wire(urls)
        evidence.append(info)
    return {'urls': urls, 'evidence': evidence}


def identity(prepared):
    return prepared['evidence'] if prepared else []


def prepare_many(requests):
    images, total = [], 0
    for request in requests:
        prepared = prepare(request.get('images'))
        total += sum(len(url) for url in prepared['urls']) if prepared else 0
        if total > MAX_EVALUATION_BYTES:
            raise ValueError('Image evaluation exceeds 32 MiB encoded; narrow the cases')
        images.append(prepared)
    return images


def asset_path(journal, info):
    journal = Path(journal)
    mime_to_suffix = dict(FORMATS.values())
    sha = info.get('sha256')
    if (not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha)
            or info.get('mime') not in mime_to_suffix):
        raise ValueError('Invalid retained image identity')
    return journal.parent / (journal.name + '.assets') / (sha + mime_to_suffix[info['mime']])


def retain(journal, payload, references):
    """Replace wire images with private, content-addressed assets without changing bytes."""
    if not payload or 'images' not in payload:
        return payload
    validate_wire(payload['images'])
    if len(payload['images']) != len(references):
        raise ValueError('Image references do not match the submitted images')
    stored = copy.deepcopy(payload)
    stored['images'] = []
    for url, ref in zip(payload['images'], references):
        prefix, encoded = url.split(',', 1)
        data = base64.b64decode(encoded, validate=True)
        info = dict(metadata(data), label=ref['label'])
        if prefix != f'data:{info["mime"]};base64':
            raise ValueError('Image data URL does not match its decoded format')
        path = asset_path(journal, info)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.parent.is_symlink() or path.is_symlink():
            raise ValueError('Retained image assets must not be symlinks')
        with tempfile.NamedTemporaryFile(dir=path.parent) as stream:
            stream.write(data)
            stream.flush()
            try:
                os.link(stream.name, path)
            except FileExistsError:
                if read_bytes(path) != data:
                    raise ValueError('Retained image asset changed')
        stored['images'].append(dict(info, path=str(path.relative_to(Path(journal).parent))))
    return stored


def restore(journal, payload):
    """Reconstruct wire images only from intact assets beside their journal."""
    if not payload or 'images' not in payload:
        return payload
    refs = payload['images']
    if not isinstance(refs, list) or not 1 <= len(refs) <= MAX_IMAGES:
        raise ValueError('Invalid retained image list')
    wire = copy.deepcopy(payload)
    wire['images'] = []
    for ref in refs:
        if not isinstance(ref, dict):
            raise ValueError('Replay requires retained image asset references')
        path = asset_path(journal, ref)
        if (ref.get('path') != str(path.relative_to(Path(journal).parent))
                or path.parent.is_symlink() or path.is_symlink()):
            raise ValueError('Invalid retained image asset path')
        data = read_bytes(path)
        if any(ref.get(key) != value for key, value in metadata(data).items()):
            raise ValueError('Retained image asset integrity mismatch')
        wire['images'].append(data_url(data, ref['mime']))
    validate_wire(wire['images'])
    return wire
