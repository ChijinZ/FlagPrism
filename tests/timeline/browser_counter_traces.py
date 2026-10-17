"""Browse six real counter traces in the standard pinned Perfetto UI.

This tests real UI import, tracks, selection, details and focus. It does not
qualify source boundaries, physical timer precision, hardware busy or flows.
Run in the server browser-tools venv, without importing or replaying product.
"""
import argparse
import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import threading


def need(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--ui', type=Path, required=True)
    p.add_argument('--browser', type=Path, required=True)
    p.add_argument('--library-path', required=True)
    args=p.parse_args();args.output.mkdir(exist_ok=False)
    os.environ['LD_LIBRARY_PATH']=args.library_path
    all_rows=[r for r in json.loads(args.manifest.read_text()) if not r.get('fixture')]
    groups={}
    for row in all_rows:
        view=json.loads(Path(row['view_file']).read_text())
        groups.setdefault(view['identity']['invocation_id'],[]).append((row,view))
    need(len(groups)>=4, 'Need four actual invocations, not fixture traces')
    selected=[rows[0] for rows in list(groups.values())[:4]]
    selected.extend(rows[-1] for rows in list(groups.values())[:2])
    need(len({r['trace_file'] for r,_ in selected})==6, 'Need six distinct real traces')
    bundle=Path(all_rows[0]['trace_file'])
    while bundle.name!='timeline' and bundle.parent!=bundle:
        bundle=bundle.parent
    need(bundle.name=='timeline', 'Manifest must refer to a retained timeline bundle')
    before={str(f.relative_to(bundle)):digest(f) for f in bundle.rglob('*') if f.is_file()}
    class Handler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Cross-Origin-Opener-Policy','same-origin')
            self.send_header('Cross-Origin-Embedder-Policy','require-corp')
            super().end_headers()
        def log_message(self,*args):
            pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
        functools.partial(Handler,directory=str(args.ui)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    from playwright.sync_api import sync_playwright
    checks=[]
    try:
        with sync_playwright() as play:
            browser=play.chromium.launch(executable_path=str(args.browser),headless=True,
                args=['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'])
            try:
                for number,(row,view) in enumerate(selected):
                    folder=args.output/str(number);folder.mkdir()
                    errors=[]
                    page=browser.new_page(viewport=dict(width=1440,height=1000),device_scale_factor=1)
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    try:
                        need(digest(Path(row['trace_file']))==row['sha256'], 'Input trace SHA changed')
                        page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='domcontentloaded',timeout=30000)
                        opener=page.get_by_text('Open trace file',exact=False).first
                        opener.wait_for(timeout=20000)
                        with page.expect_file_chooser(timeout=10000) as chooser:
                            opener.click()
                        chooser.value.set_files(row['trace_file'])
                        invocation=view['identity']['invocation_id']
                        page.wait_for_function('(id)=>document.body.innerText.includes(id)',arg=invocation,timeout=30000)
                        cookie=page.get_by_text('OK',exact=True)
                        if cookie.count():cookie.first.click()
                        page.locator('.pf-track__title').filter(has_text=invocation+' — isolated counter ns').first.locator('..').locator('.pf-track__collapse-button').click()
                        observer=view['observer']
                        title='program '+str(observer['program_coordinates'])+' / '+observer['kind']+' '+observer['local_id']
                        page.locator('.pf-track__title').filter(has_text=title).first.locator('..').locator('.pf-track__collapse-button').click()
                        page.wait_for_function("()=>document.body.innerText.includes('observer_region_elapsed /')",timeout=10000)
                        page.screenshot(path=str(folder/'overview.png'))
                        event=max((e for e in view['events'] if e['end_ns'] is not None),
                                  key=lambda e:e['end_ns']-e['start_ns'])
                        need(event['end_ns']>event['start_ns'], 'No positive real interval to select')
                        site=next(s for s in view['sites'] if s['id']==event['site_id'])
                        track=page.locator('.pf-track__title').filter(
                            has_text=event['semantic']+' / '+site['name']+' / lane 0').first.locator('xpath=../../..')
                        box=track.locator('.pf-track__canvas').bounding_box()
                        need(box and box['width']>0, 'No visible rendered source-site track')
                        end=max(r['relative_ns'] for r in view['records'])
                        page.mouse.click(box['x']+(event['start_ns']+event['end_ns'])/2/end*box['width'],
                                         box['y']+box['height']/2)
                        page.wait_for_function('(id)=>document.body.innerText.includes(id)',arg=event['id'],timeout=10000)
                        body=page.locator('body').inner_text()
                        for field in ['raw_ticks','source_locations','counter_unit_only_precision_unverified']:
                            need(field in body, 'Slice details lost '+field)
                        page.screenshot(path=str(folder/'details.png'))
                        (folder/'details.txt').write_text(body)
                        page.keyboard.press('f')
                        page.screenshot(path=str(folder/'focus.png'))
                        need(not errors, 'Standard UI page errors: '+repr(errors))
                        need(digest(Path(row['trace_file']))==row['sha256'], 'Browser changed the trace')
                        checks.append(dict(trace_file=row['trace_file'],trace_sha256=row['sha256'],
                            event_id=event['id'],invocation_id=invocation,
                            program_coordinates=observer['program_coordinates'],
                            actual_track_canvas=box,page_errors=errors,
                            screenshots={name:dict(file=str((folder/(name+'.png')).relative_to(args.output)),
                                sha256=digest(folder/(name+'.png'))) for name in ['overview','details','focus']}))
                        (folder/'result.json').write_text(json.dumps(checks[-1],indent=2)+'\n')
                    finally:
                        (folder/'final-body.txt').write_text(page.locator('body').inner_text())
                        page.screenshot(path=str(folder/'final.png'));page.close()
                version=browser.version
            finally:
                browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
    after={str(f.relative_to(bundle)):digest(f) for f in bundle.rglob('*') if f.is_file()}
    need(before==after, 'UI inspection changed the original bundle')
    (args.output/'result.json').write_text(json.dumps(dict(
        status='six_actual_counter_traces_UI_checked_not_full_timeline_qualification',
        browser_version=version,browser_sha256=digest(args.browser),
        ui_index_sha256=digest(args.ui/'index.html'),checks=checks,
        before_bundle_files=before,after_bundle_files=after,
        precision_qualified=False,source_boundaries_qualified=False,
        async_and_flow_qualified=False),indent=2)+'\n')


if __name__=='__main__':
    main()
