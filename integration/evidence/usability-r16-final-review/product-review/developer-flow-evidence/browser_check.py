import json, hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path('/workspace/chijin-r16-flow-review'); out.mkdir(exist_ok=True)
bundle=Path('/workspace/chijin-r15-python-alignment-r2/public-smoke-r15/bundle')
before={str(f.relative_to(bundle)):hashlib.sha256(f.read_bytes()).hexdigest() for f in bundle.rglob('*') if f.is_file()}
r={'bundle':str(bundle),'page_errors':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/workspace/usability-run-001/nvidia/p1-developer/browser-assets/chrome-linux/headless_shell',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
    try:
        page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:r['page_errors'].append(str(e)))
        base=bundle.as_uri()+'/report/'
        page.goto(base+'index.html');r['overview_title']=page.title();r['overview_links']=page.locator('a').evaluate_all('(aa)=>aa.map(a=>({text:a.innerText,href:a.getAttribute("href"),visible:!!a.getClientRects().length}))')
        page.get_by_role('link',name='Source-linked internal dynamic records',exact=False).click()
        r['records_header']=page.locator('thead').all_inner_texts();r['record_rows']=page.locator('#records tr:visible').all_inner_texts();r['records_body']=page.locator('body').inner_text()
        r['filters']={}
        for term in ['launch-1','launch-3','logical_warp','logical_program_observer','ttng.tmem_load','__no_such_record__','']:
            page.locator('#filter').fill(term);r['filters'][term]=page.locator('#records tr:visible').count()
        first=page.locator('#records tr:visible td a').first; r['first_source_href']=first.get_attribute('href');first.click()
        r['source_url']=page.url;r['source_target']=page.locator(':target').inner_text();r['source_lines']=page.locator('.line').count();r['source_selected']=page.locator('select').input_value()
        target=page.locator(':target');back=target.locator('a.records');r['target_backlink_count']=back.count()
        if back.count():
            back.first.click();r['backlink_url']=page.url;r['backlink_rows']=page.locator('#records tr:visible').all_inner_texts()
        page.goto(base+'fine_grained.html');page.screenshot(path=str(out/'records.png'))
        page.get_by_role('link',name='Execution mapping',exact=True).click();r['execution_body']=page.locator('body').inner_text();r['execution_summaries']=page.locator('summary').all_inner_texts()
        for s in page.locator('summary').all():s.click()
        r['expanded_tables']=page.locator('table:visible').count();page.screenshot(path=str(out/'execution.png'))
        page.get_by_role('link',name='Original mapping JSON',exact=True).click();r['mapping_url']=page.url;r['mapping_json_keys']=list(json.loads(page.locator('body').inner_text()).keys())
        page.goto(base+'index.html')
        rawlinks=[x for x in r['overview_links'] if x['visible'] and ('raw/' in (x['href'] or ''))]
        r['raw_navigation']=[]
        for link in rawlinks[:2]:
            page.goto(base+'index.html');page.locator('a').filter(has_text=link['text']).first.click();r['raw_navigation'].append({'text':link['text'],'url':page.url,'body_prefix':page.locator('body').inner_text()[:300]})
        page.goto(base+'observations.html');r['observations_headers']=page.locator('th').all_inner_texts()
    finally:browser.close()
after={str(f.relative_to(bundle)):hashlib.sha256(f.read_bytes()).hexdigest() for f in bundle.rglob('*') if f.is_file()}
r['bundle_bytes_unchanged']=before==after;r['file_count']=len(before);r['bundle_file_hashes']=before
(out/'browser-results.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in ['records_body','execution_body','overview_links','bundle_file_hashes','record_rows','backlink_rows']},indent=2))
