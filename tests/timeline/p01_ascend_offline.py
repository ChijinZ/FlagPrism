"""Fresh-process real-bundle re-export, with original environments denied."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

AUDITED = r'''
import pathlib,sys,json,os
import torch,torch_npu
from flagtree.profiler.timeline_reexport import reexport_bundle
if torch.npu.is_initialized():raise RuntimeError('Offline bootstrap initialized an NPU context')
bundle=pathlib.Path(sys.argv[1]).resolve();dest=pathlib.Path(sys.argv[2]);denied=json.loads(sys.argv[3])
def guard(event,args):
 if event=='subprocess.Popen':raise RuntimeError('Offline decode attempted a subprocess')
 if event in ('open','os.listdir','os.scandir') and args and isinstance(args[0],(str,bytes,os.PathLike)):
  p=pathlib.Path(os.fsdecode(args[0])).absolute()
  if any(p==pathlib.Path(root) or pathlib.Path(root) in p.parents for root in denied):raise RuntimeError('Offline decode attempted original environment access: '+str(p))
sys.addaudithook(guard)
def no_device(*args,**kwargs):raise RuntimeError('Offline decoder attempted NPU initialization')
torch.npu._lazy_init=no_device
result=reexport_bundle(bundle)
if torch.npu.is_initialized():raise RuntimeError('Offline decoder initialized an NPU context')
dest.write_text(json.dumps(result,indent=2))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--deny', action='append', default=[])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    timeline = args.output / 'portable' / 'timeline'
    shutil.copytree(args.timeline, timeline)
    originals = {
        p.relative_to(timeline).as_posix():
        hashlib.sha256(p.read_bytes()).hexdigest()
        for p in timeline.rglob('*') if p.is_file()
    }
    audited = args.output / 'audited.py'
    audited.write_text(AUDITED)
    reports, steps = [], []
    for mode in ('public', 'normal', 'optimized'):
        cwd = args.output / ('empty-' + mode)
        cwd.mkdir()
        env = os.environ.copy()
        env.pop('PYTHONPATH', None)
        env.update(ASCEND_RT_VISIBLE_DEVICES='',
                   TORCH_DEVICE_BACKEND_AUTOLOAD='0',
                   TRITON_CACHE_DIR=str(cwd / 'cache'))
        report_file = args.output / (mode + '.json')
        if mode == 'public':
            command = [
                sys.executable, '-I', '-m',
                'flagtree.profiler.timeline_reexport',
                str(timeline)
            ]
        else:
            command = [sys.executable, '-I'
                       ] + (['-O'] if mode == 'optimized' else []) + [
                           str(audited),
                           str(timeline),
                           str(report_file),
                           json.dumps(args.deny)
                       ]
        with (args.output / (mode + '.stdout')).open('wb') as out, (
                args.output / (mode + '.stderr')).open('wb') as err:
            result = subprocess.run(command,
                                    cwd=cwd,
                                    env=env,
                                    stdout=out,
                                    stderr=err,
                                    timeout=60)
        steps.append(
            dict(mode=mode, returncode=result.returncode, argv=command))
        (args.output / 'steps.json').write_text(json.dumps(steps, indent=2))
        if result.returncode:
            raise RuntimeError(mode + ' actual offline re-export failed')
        if mode == 'public':
            report_file.write_bytes(
                (args.output / 'public.stdout').read_bytes())
        report = json.loads(report_file.read_text())
        if report.get(
                'application_replayed') is not False or not report['captures']:
            raise RuntimeError('Offline result has no retained captures')
        for row in report['captures']:
            if row['backend'] != 'ascend' or row['status'] != 'raw_only':
                raise RuntimeError('Unvalidated units were manufactured')
        reports.append(report)
    if not all(r == reports[0] for r in reports):
        raise RuntimeError(
            'Same retained inputs produced different offline identities')
    for name, digest in originals.items():
        if hashlib.sha256(
            (timeline / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Offline re-export changed an original file')
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status='real_offline_public_normal_optimized_passed',
            original_files=len(originals),
            captures=len(reports[0]['captures']),
            application_replayed=False,
            limits=
            'Python audit hook and configured visibility environment; no device initialization; not an OS sandbox or proof that hardware is inaccessible',
            denied_original_roots=args.deny,
            steps=steps),
                   indent=2))


if __name__ == '__main__':
    main()
