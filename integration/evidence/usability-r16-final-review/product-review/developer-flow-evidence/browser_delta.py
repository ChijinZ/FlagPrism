import json
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path('/workspace/chijin-r16-flow-review');base='file:///workspace/chijin-r15-python-alignment-r2/public-smoke-r15/bundle/'
r={'page_errors':[]}
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/workspace/usability-run-001/nvidia/p1-developer/browser-assets/chrome-linux/headless_shell',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
 try:
  page=b.new_page();page.on('pageerror',lambda e:r['page_errors'].append(str(e)));page.goto(base+'report/fine_grained.html')
  rows=page.locator('#records tr:visible');r['programs']=rows.locator('td:nth-child(5)').all_inner_texts();r['visits']=rows.locator('td:nth-child(9)').all_inner_texts();r['actors']=rows.locator('td:nth-child(6)').all_inner_texts()
  link=page.locator('#records a').filter(has_text='warp_specialization_affine.py:38').first;link.click();r['worker_source_target']=page.locator(':target').inner_text();page.locator(':target a.records').first.click();r['worker_backlink_rows']=page.locator('#records tr:visible').all_inner_texts()
  page.goto(base+'report/fine_grained.html');page.get_by_role('link',name='Records JSON',exact=True).click();r['records_json_url']=page.url;r['records_json_keys']=list(json.loads(page.locator('body').inner_text()).keys())
  r['raw_navigation']={}
  for path in ['ai/observations.json','raw/native/capture.observations.json','raw/native/capture.launches.json','raw/native/capture.finalization.json']:
   page.goto(base+path);j=json.loads(page.locator('body').inner_text());r['raw_navigation'][path]={'url':page.url,'type':type(j).__name__,'keys':list(j.keys()) if isinstance(j,dict) else None}
 finally:b.close()
(out/'browser-delta-results.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
