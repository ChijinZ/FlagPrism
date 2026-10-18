"""Real old/new decoded reports preserve all data with bounded gzip reading."""
import argparse
import hashlib
import json
from pathlib import Path


def run(timeline, output, *, reports):
    output.mkdir(parents=True)
    original = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in timeline.rglob('*') if p.is_file()
    }
    rows, rejected = [], []

    def reject(name, call):
        try:
            call()
        except (ValueError, KeyError, TypeError) as error:
            rejected.append(dict(case=name, reason=str(error)))
        else:
            raise RuntimeError('Invalid decoded report accepted: ' + name)

    reject('invalid_capture_type',
           lambda: reports.read_decoded_report(output, None))

    for item in json.loads((timeline / 'index.json').read_text())['captures']:
        capture = json.loads((timeline / item['capture_file']).read_text())
        decoded = reports.read_decoded_report(timeline, capture)
        plain = json.dumps(decoded, separators=(',', ':'),
                           allow_nan=False).encode()
        encoded = reports.encode_decoded_report(decoded)
        if encoded != reports.encode_decoded_report(decoded):
            raise RuntimeError('New auxiliary encoding is not deterministic')
        if reports.decode_report_bytes(
                plain,
                reports.PLAIN_JSON) != decoded or reports.decode_report_bytes(
                    encoded, reports.GZIP_JSON) != decoded:
            raise RuntimeError('Actual decoded report lost fields or values')
        if len(encoded) >= len(plain):
            raise RuntimeError('Actual expanded report did not shrink')
        fixture = output / capture['owner']['invocation_id']
        fixture.mkdir()
        (fixture / 'report.json').write_bytes(plain)
        (fixture / 'report.json.gz').write_bytes(encoded)
        for cap in [
                dict(decoded_file='report.json'),
                dict(decoded_file='report.json',
                     decoded_encoding=reports.PLAIN_JSON),
                dict(decoded_file='report.json.gz',
                     decoded_encoding=reports.GZIP_JSON)
        ]:
            if reports.read_decoded_report(fixture, cap) != decoded:
                raise RuntimeError(
                    'Actual old/new declared report reader differs')
        reject('unknown_codec',
               lambda: reports.decode_report_bytes(encoded, 'unknown-v1'))
        reject(
            'truncated_gzip', lambda: reports.decode_report_bytes(
                encoded[:-8], reports.GZIP_JSON))
        reject(
            'concatenated_gzip', lambda: reports.decode_report_bytes(
                encoded + encoded, reports.GZIP_JSON))
        reject(
            'trailing_gzip_data', lambda: reports.decode_report_bytes(
                encoded + b'X', reports.GZIP_JSON))
        reject(
            'bounded_gzip_expansion', lambda: reports.decode_report_bytes(
                encoded, reports.GZIP_JSON, max_bytes=1024))
        reject(
            'bounded_plain_json', lambda: reports.decode_report_bytes(
                plain, reports.PLAIN_JSON, max_bytes=1024))
        reject(
            'boolean_size', lambda: reports.decode_report_bytes(
                encoded, reports.GZIP_JSON, max_bytes=True))
        reject(
            'non_bytes_payload', lambda: reports.decode_report_bytes(
                bytearray(encoded), reports.GZIP_JSON))
        reject(
            'unknown_declared_codec', lambda: reports.read_decoded_report(
                fixture,
                dict(decoded_file='report.json.gz',
                     decoded_encoding='unknown-v1')))
        changed = bytearray(encoded)
        changed[-8] ^= 1
        reject(
            'wrong_gzip_crc', lambda: reports.decode_report_bytes(
                bytes(changed), reports.GZIP_JSON))
        rows.append(
            dict(invocation_id=capture['owner']['invocation_id'],
                 plain_bytes=len(plain),
                 gzip_bytes=len(encoded),
                 raw_sha256=decoded['raw_sha256'],
                 source_encoding=capture.get('decoded_encoding',
                                             reports.PLAIN_JSON),
                 complete_roundtrip=True))
    if original != {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in timeline.rglob('*') if p.is_file()
    }:
        raise RuntimeError('Original artifacts changed')
    (output / 'result.json').write_text(
        json.dumps(dict(rows=rows,
                        negative_checks=len(rejected),
                        rejected=rejected,
                        original_files_unchanged=len(original),
                        application_replayed=False),
                   indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--timeline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    from flagtree.profiler import timeline_decoded_reports
    run(args.timeline, args.output, reports=timeline_decoded_reports)
