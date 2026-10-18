"""Lossless bounded storage for auxiliary decoded reports, never raw records."""
import gzip
import json
import zlib

from .timeline_store import read_artifact

MAX_JSON_BYTES = 256 * 1024 * 1024
GZIP_JSON = 'gzip-json-v1'
PLAIN_JSON = 'json-v1'


def encode_decoded_report(document):
    data = json.dumps(document, separators=(',', ':'),
                      allow_nan=False).encode()
    if len(data) > MAX_JSON_BYTES:
        raise ValueError('Decoded JSON exceeds bounded report storage')
    return gzip.compress(data, compresslevel=1, mtime=0)


def decode_report_bytes(payload, encoding, *, max_bytes=MAX_JSON_BYTES):
    if type(payload) is not bytes or type(
            max_bytes) is not int or not 1 <= max_bytes <= MAX_JSON_BYTES:
        raise ValueError('Invalid decoded report payload or bound')
    if encoding == GZIP_JSON:
        inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            data = inflater.decompress(payload, max_bytes + 1)
        except zlib.error as error:
            raise ValueError('Invalid decoded-report gzip stream') from error
        if len(
                data
        ) > max_bytes or not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
            raise ValueError(
                'Truncated, oversized or concatenated decoded-report gzip stream'
            )
    elif encoding == PLAIN_JSON:
        data = payload
        if len(data) > max_bytes:
            raise ValueError('Decoded JSON exceeds bounded report reader')
    else:
        raise ValueError('Unknown decoded-report encoding')
    return json.loads(data)


def read_decoded_report(directory, capture):
    """Read existing plain reports and explicitly encoded new reports alike."""
    if type(capture) is not dict:
        raise ValueError('Invalid decoded report capture')
    encoding = capture.get('decoded_encoding', PLAIN_JSON)
    if encoding not in (GZIP_JSON, PLAIN_JSON):
        raise ValueError('Unknown decoded-report encoding')
    return decode_report_bytes(
        read_artifact(directory, capture['decoded_file']), encoding)
