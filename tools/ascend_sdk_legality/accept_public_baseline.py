"""Derive a producer-only baseline receipt without changing the failed replay."""
import argparse
import json
from pathlib import Path
import hashlib
from compare_public_elf import compare, REFERENCE_SHA
INPUT_SHA = '6b910a15aa5e87da20bbfc7ae29515093d362a609eae1a8c39126514f6a76b3f'
BIND_SHA = {'0_hivm-bind-sub-block.mlir': '0b1f6b3241e15b95dfbcfa74b7d4dcc0166eca74c02a94928b89ea1b6dc66c2f', '1_hivm-bind-sub-block.mlir': '03c4eddd74753f6bcdda5a403e1db4417d201c20d5abb1c20729198a4f3cbe0e'}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate(replay_path):
    replay = json.loads(replay_path.read_text())
    if not (replay['state'] == 'binary_mismatch' and replay['returncode'] == 0):
        raise RuntimeError('Public baseline validation failed')
    if not replay['byteequal'] is False:
        raise RuntimeError('Public baseline validation failed')
    if not replay['input_sha256'] == sha(replay['input']) == INPUT_SHA:
        raise RuntimeError('Public baseline validation failed')
    if not replay['compiler_sha256'] == sha(replay['compiler']):
        raise RuntimeError('Public baseline validation failed')
    if not replay['reference_sha256'] == sha(replay['reference']) == REFERENCE_SHA:
        raise RuntimeError('Public baseline validation failed')
    if not replay['binary_sha256'] == sha(replay['binary']):
        raise RuntimeError('Public baseline validation failed')
    comparison = compare(Path(replay['binary']), Path(replay['reference']))
    bind = {}
    for name, expected in BIND_SHA.items():
        paths = list((replay_path.parent / 'ir').rglob(name))
        if not (len(paths) == 1 and sha(paths[0]) == expected):
            raise RuntimeError('actual Bind IR changed')
        bind[name] = expected
    return {'classification': 'producer-comment-only', 'bitidentical': False, 'all_other_bytes_equal': True, 'replay': str(replay_path.resolve()), 'replay_sha256': sha(replay_path), 'input_sha256': INPUT_SHA, 'compiler': replay['compiler'], 'compiler_sha256': replay['compiler_sha256'], 'actual_sha256': comparison['actual_sha256'], 'reference_sha256': REFERENCE_SHA, 'bind_ir_sha256': bind, 'elf_comparison': comparison, 'scope': 'CPU baseline only; device mathematical and State criteria unchanged'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--replay', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('Refusing to overwrite derived equivalence receipt')
    result = validate(args.replay)
    result['recipe_sha256'] = sha(__file__)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'elf_comparison'}, indent=2))
if __name__ == '__main__':
    main()
