"""Browse real dependency traces in the pinned standard Perfetto UI.
This checker does not replace numerical, native-clock or independent qualification.
"""
import argparse, functools, hashlib, http.server, json, os, threading, time
from pathlib import Path


def need(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
p.add_argument('--timeline', type=Path, required=True)
p.add_argument('--minimum-traces', type=int, default=6)
a = p.parse_args()
a.output.mkdir(parents=True)
ui = Path('/workspace/chijin-timeline-r012/runs/ui-install-v1/output/ui')
root = a.timeline.resolve()
reports = []
for item in json.loads((root / 'index.json').read_text())['captures']:
    cap = json.loads((root / item['capture_file']).read_text())
    if cap.get('observed_dependency_exports'):
        reports.append(dict(exports=cap['observed_dependency_exports']))
need(
    sum((len(r['exports']) for r in reports)) >= a.minimum_traces,
    'Not enough real dependency traces')
summary = dict(reports=reports)
before = {str(f): sha(f) for f in root.rglob('*') if f.is_file()}
os.environ[
    'LD_LIBRARY_PATH'] = '/workspace/chijin-timeline-r017/runs/ui-offline-v2/output/libraries/usr/lib/x86_64-linux-gnu:/workspace/chijin-timeline-r017/runs/ui-offline-v2/output/libraries/lib/x86_64-linux-gnu'


class Handler(http.server.SimpleHTTPRequestHandler):

    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        super().end_headers()

    def log_message(self, *args):
        pass


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
                                         functools.partial(Handler,
                                                           directory=str(ui)))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

checks = []
blocked = []
try:
    with sync_playwright() as play:
        browser = play.chromium.launch(
            executable_path=
            '/workspace/chijin-timeline-r017/runs/ui-offline-v1/output/browser/chrome-linux/headless_shell',
            headless=True,
            args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'])
        try:
            for report in summary['reports']:
                for row in report['exports']:
                    folder = a.output / str(len(checks))
                    folder.mkdir()
                    errors = []
                    page = browser.new_page(viewport=dict(width=1600,
                                                          height=1100),
                                            device_scale_factor=1,
                                            service_workers='block')
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    origin = f'http://127.0.0.1:{server.server_port}/'

                    def route(request):
                        if request.request.url.startswith(origin):
                            request.continue_()
                        else:
                            blocked.append(request.request.url)
                            request.abort()

                    page.route('**/*', route)
                    try:
                        view = json.loads(
                            (root / row['view_file']).read_text())
                        need(
                            sha(root / row['trace_file']) == row['sha256'],
                            'Trace changed')
                        inputs = json.loads(
                            (root / Path(row['receipt_file']).parent /
                             'inputs.json').read_text())
                        clock = next(
                            (r['clock'] for r in inputs['proofs']
                             if r['clock']['domain_id'] == view['domain_id']))
                        canonical = json.loads(
                            (root / Path(row['view_file']).parent.parent /
                             'canonical.json').read_text())
                        end = max(
                            ((r['tick'] - view['origin_tick']) *
                             clock['period_numerator_ns'] //
                             clock['period_denominator']
                             for r in canonical['records']
                             if r['observer_id'] in clock['observer_ids']))
                        page.goto(origin,
                                  wait_until='domcontentloaded',
                                  timeout=30000)
                        opener = page.get_by_text('Open trace file',
                                                  exact=False).first
                        opener.wait_for(timeout=20000)
                        with page.expect_file_chooser(
                                timeout=10000) as chooser:
                            opener.click()
                        chooser.value.set_files(str(root / row['trace_file']))
                        invocation = view['identity']['invocation_id']
                        page.wait_for_function(
                            '(id)=>document.body.innerText.includes(id)',
                            arg=invocation,
                            timeout=30000)
                        cookie = page.get_by_text('OK', exact=True)
                        if cookie.count():
                            cookie.first.click()
                        root_title = invocation + ' / program ' + str(
                            view['program_coordinates']
                        ) + ' — shared counter ns (precision unverified)'
                        page.locator('.pf-track__title').filter(
                            has_text=root_title).first.locator('..').locator(
                                '.pf-track__collapse-button').click()
                        for observer in [
                                o for o in canonical['observers']
                                if o['id'] in clock['observer_ids']
                        ]:
                            page.locator('.pf-track__title').filter(
                                has_text='Observer ' +
                                observer['local_id']).first.locator(
                                    '..').locator(
                                        '.pf-track__collapse-button').click()
                        page.evaluate(
                            'async()=>{await document.fonts.ready;await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame)}'
                        )
                        (folder / 'tracks.json').write_text(
                            json.dumps(page.locator(
                                '.pf-track__title').all_text_contents(),
                                       indent=2))
                        page.screenshot(path=str(folder / 'full-range.png'))
                        checkpoints = page.locator('.pf-track__title').filter(
                            has_text='Observed dependency checkpoints')
                        need(checkpoints.count() == len(clock['observer_ids']),
                             'Actual observer checkpoint lanes missing')
                        observer_id = clock['observer_ids'][0]
                        nodes = sorted([
                            n for n in view['nodes']
                            if n['observer_id'] == observer_id
                        ],
                                       key=lambda n: n['time_ns'])

                        def gap(index):
                            t = nodes[index]['time_ns']
                            return min(
                                t -
                                nodes[index - 1]['time_ns'] if index else t,
                                nodes[index + 1]['time_ns'] - t if index +
                                1 < len(nodes) else end - t)

                        candidates = sorted(
                            range(len(nodes)),
                            key=lambda i:
                            ('Async wait' in nodes[i]['label'] and nodes[i][
                                'phase'] == 'exit', gap(i)),
                            reverse=True)
                        track = checkpoints.first.locator('xpath=../../..')
                        track.scroll_into_view_if_needed(timeout=3000)
                        box = track.locator('.pf-track__canvas').bounding_box()
                        need(box and box['width'] > 0, 'No checkpoint canvas')
                        selected = None
                        for index in candidates[:8]:
                            node = nodes[index]
                            for delta in [0, -2, 2, -4, 4]:
                                page.mouse.click(
                                    box['x'] +
                                    node['time_ns'] / end * box['width'] +
                                    delta,
                                    box['y'] + min(12, box['height'] / 2))
                                try:
                                    page.wait_for_function(
                                        '(id)=>document.body.innerText.includes(id)',
                                        arg=node['id'],
                                        timeout=400)
                                    selected = node
                                    break
                                except PlaywrightTimeoutError:
                                    pass
                            if selected:
                                break
                        need(selected is not None,
                             'Could not select actual dependency checkpoint')
                        body = page.locator('body').inner_text()
                        for field in [
                                'source_locations', 'raw_tick', 'raw_offset',
                                'dependency_relations',
                                'dynamic_dependencies_verified', selected['id']
                        ]:
                            need(field in body,
                                 'Missing dependency details: ' + field)
                        need('outgoing:' in body or 'incoming:' in body,
                             'No readable actual generation relation')
                        (folder / 'details.txt').write_text(body)
                        page.screenshot(path=str(folder / 'details.png'))
                        page.keyboard.press('f')
                        for _ in range(20):
                            page.keyboard.press('s')
                        page.mouse.move(0, 0)
                        page.evaluate(
                            'async()=>{await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame)}'
                        )
                        page.screenshot(path=str(folder /
                                                 'focus-with-flows.png'))
                        need(not errors, 'UI errors: ' + repr(errors))
                        checks.append(
                            dict(trace_file=row['trace_file'],
                                 trace_sha256=row['sha256'],
                                 node_id=selected['id'],
                                 observer_id=observer_id,
                                 raw_tick=selected['tick'],
                                 raw_offset=selected['raw_offset'],
                                 page_errors=errors,
                                 screenshots={
                                     n:
                                     dict(file=str(f.relative_to(a.output)),
                                          sha256=sha(f))
                                     for n in [
                                         'full-range', 'details',
                                         'focus-with-flows'
                                     ]
                                     for f in [folder / (n + '.png')]
                                 }))
                    except BaseException:
                        page.screenshot(path=str(folder / 'failure.png'))
                        (folder / 'failure.txt').write_text(
                            page.locator('body').inner_text())
                        raise
                    finally:
                        page.close()
        finally:
            browser.close()
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
need(before == {str(f): sha(f)
                for f in root.rglob('*')
                if f.is_file()}, 'Browser modified retained bundle')
(a.output / 'result.json').write_text(
    json.dumps(dict(
        status='actual_dependency_traces_UI_passed_not_full_qualification',
        checks=checks,
        blocked_external_requests=blocked),
               indent=2))
