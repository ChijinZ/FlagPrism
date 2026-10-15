"""Captured-source navigation with file/digest and line-range evidence.

Only bundle snapshots or digest-checked capture bytes are used. The report never
opens an original capture-machine path or guesses a source by its basename.
"""
import base64
import hashlib
from html import escape
import json
from pathlib import Path
import tokenize
from io import BytesIO
from urllib.parse import urlencode


class SourceCatalog:

    def __init__(self, output):
        self.output = Path(output)
        self.sources = {}
        self.locations = {}
        self.diagnostics = []

    def _note(self, binary_id, filename, reason):
        self.diagnostics.append(
            dict(binary_id=binary_id, file=filename, reason=reason))

    def _add(self, binary_id, filename, payload, expected, kind, basis):
        if not isinstance(binary_id, str) or not binary_id:
            return
        digest = hashlib.sha256(payload).hexdigest()
        if not isinstance(expected, str) or digest != expected:
            self._note(binary_id, filename, 'snapshot_digest_mismatch')
            return
        try:
            encoding, _ = tokenize.detect_encoding(BytesIO(payload).readline)
            text = payload.decode(encoding)
        except (SyntaxError, UnicodeError, LookupError):
            self._note(binary_id, filename, 'snapshot_encoding_unavailable')
            return
        identity = hashlib.sha256(
            json.dumps([binary_id, filename, digest,
                        kind]).encode()).hexdigest()
        if identity in self.sources:
            return
        relative = f'ai/sources/{digest}.py'
        path = self.output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != payload:
            raise ValueError(
                'Captured source digest path contains different bytes')
        path.write_bytes(payload)
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        line_count = len(lines) - (1 if lines[-1] == '' else 0)
        self.sources[identity] = dict(
            id=identity,
            binary_id=binary_id,
            file=filename,
            kind=kind,
            sha256=digest,
            snapshot_file=relative,
            line_count=line_count,
            capture_basis=basis,
            compiled_text_alignment='not_independently_verified'
            if kind == 'file_snapshot' else 'captured_jit_function_text',
            text=text,
            observed_lines={})
        if kind == 'file_snapshot' and isinstance(filename, str):
            self.locations.setdefault((binary_id, filename),
                                      []).append(identity)

    def _exported(self, binary_id, filename, reference, digest, kind):
        if not isinstance(reference, str):
            return
        target = (self.output / reference).resolve()
        if not target.is_relative_to(self.output.resolve()):
            self._note(binary_id, filename, 'snapshot_path_outside_bundle')
            return
        try:
            payload = target.read_bytes()
        except OSError:
            self._note(binary_id, filename, 'snapshot_file_unavailable')
            return
        self._add(binary_id, filename, payload, digest, kind,
                  'exported_binary_source_snapshot')

    def load(self, captures):
        path = self.output / 'ai/binaries.json'
        binaries = json.loads(path.read_text()) if path.is_file() else []
        for binary in binaries:
            source = binary.get('source') or {}
            for snapshot in binary.get('source_snapshots', []):
                if snapshot.get('status') == 'captured':
                    self._exported(binary.get('id'), snapshot.get('file'),
                                   snapshot.get('snapshot_file'),
                                   snapshot.get('sha256'), 'file_snapshot')
                else:
                    self._note(binary.get('id'), snapshot.get('file'),
                               'compiler_referenced_snapshot_unavailable')
            self._exported(binary.get('id'), source.get('path'),
                           source.get('file_snapshot_file'),
                           source.get('file_sha256'), 'file_snapshot')
            self._exported(binary.get('id'), source.get('path'),
                           source.get('text_file'), source.get('sha256'),
                           'jit_function_text')
        for capture in captures:
            for source in capture.get('scope_origin_sources', []):
                if source.get('status') != 'captured':
                    continue
                try:
                    payload = base64.b64decode(source['content'],
                                               validate=True)
                except (KeyError, TypeError, ValueError):
                    self._note(capture.get('binary_id'), source.get('file'),
                               'invalid_source_capture_encoding')
                    continue
                self._add(capture.get('binary_id'), source.get('file'),
                          payload, source.get('sha256'), 'file_snapshot',
                          source.get('capture_boundary'))

    def annotate(self, records):
        for record in records:
            candidates = record.get('source_location_candidates')
            if candidates is None:
                candidates = [
                    dict(location, role='compiler_location')
                    for location in record.get('source_locations', [])
                ]
            annotated, valid = [], {}
            for candidate in candidates:
                item = dict(candidate)
                matches = self.locations.get(
                    (record.get('binary_id'), item.get('file')), [])
                if not matches:
                    item['validation_status'] = 'snapshot_unavailable'
                elif len(matches) != 1:
                    item['validation_status'] = 'ambiguous_snapshot_versions'
                else:
                    source = self.sources[matches[0]]
                    item.update(source_id=source['id'],
                                snapshot_sha256=source['sha256'],
                                snapshot_line_count=source['line_count'])
                    line = item.get('line')
                    if type(
                            line
                    ) is not int or not 1 <= line <= source['line_count']:
                        item[
                            'validation_status'] = 'outside_snapshot_line_range'
                    else:
                        item[
                            'validation_status'] = 'in_range_snapshot_position'
                        item['href'] = 'sources.html?' + urlencode(
                            {'source': source['id']}) + f'#L{line}'
                        key = (item['file'], line, item.get('column', 0))
                        valid[key] = {
                            field: item.get(field, 0)
                            for field in ('file', 'line', 'column')
                        }
                annotated.append(item)
            record['source_location_candidates'] = annotated
            record['source_locations'] = list(valid.values())
            record['source_status'] = 'located' if valid else 'unresolved'
            record['source_links'] = [
                item for item in annotated if item.get('href')
            ]
            seen = set()
            for item in record['source_links']:
                key = (item['source_id'], item['line'])
                if key not in seen:
                    counts = self.sources[item['source_id']]['observed_lines']
                    counts[str(
                        item['line'])] = counts.get(str(item['line']), 0) + 1
                    seen.add(key)

    def write(self):
        entries = list(self.sources.values())
        index = dict(
            schema_version=1,
            sources=[{
                k: v
                for k, v in source.items() if k != 'text'
            } for source in entries],
            diagnostics=self.diagnostics,
            limits=[
                'File bounds do not establish compiled-text alignment.',
                'JIT text uses relative lines; no file-line offset is guessed.',
                'Compiler primary and inline callsite roles remain distinct.'
            ])
        (self.output / 'ai/source_index.json'
         ).write_text(json.dumps(index, allow_nan=False) + '\n')
        payload = json.dumps(entries,
                             allow_nan=False).replace('<', '\\u003c').replace(
                                 '>', '\\u003e').replace('&', '\\u0026')
        (self.output / 'report/sources.html').write_text(
            _PAGE.replace('__SOURCES__', payload))


def source_cell(record):
    rows, seen = [], set()
    for item in record.get('source_links', []):
        key = (item['file'], item['line'], item.get('column',
                                                    0), item.get('role'))
        if key in seen:
            continue
        seen.add(key)
        label = f"{item['file']}:{item['line']}:{item.get('column', 0)}"
        role = item.get('role', 'compiler_location').replace('_', ' ')
        rows.append(f'<a href="{escape(item["href"], quote=True)}">'
                    f'{escape(label)}</a> <small>{escape(role)}</small>')
    for item in record.get('source_location_candidates', []):
        status = item.get('validation_status')
        if status and status != 'in_range_snapshot_position':
            label = f"{item['file']}:{item['line']}:{item.get('column', 0)}"
            role = item.get('role', 'compiler_location').replace('_', ' ')
            rows.append(
                '<span class="source-warning">' +
                escape(f'{label} · {role} · {status.replace("_", " ")}') +
                '</span>')
    if rows:
        return '<br>'.join(rows)
    return escape(
        ', '.join(f"{loc['file']}:{loc['line']}:{loc.get('column', 0)}"
                  for loc in record.get('source_locations', []))
        or 'Unresolved source')


_PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Captured source · FlagPrism</title>
<style>body{font:15px system-ui;margin:2rem;color:#17212b}a{color:#175eb1}
select{padding:.5rem;max-width:100%;width:64rem}pre{border:1px solid #ddd;
padding:1rem;overflow:auto;line-height:1.6;background:#fafbfc}
.line{display:block;min-height:1.6em}.line:target{background:#fff0ae}
.observed{border-left:3px solid #24785f}.number{display:inline-block;width:4em;
text-align:right;padding-right:1em;color:#606870}.records{margin-left:2em;
font:12px system-ui;color:#24785f}p{overflow-wrap:anywhere}code{white-space:pre}
</style><h1>Captured source</h1><nav><a href="index.html">Overview</a> |
<a href="fine_grained.html">Internal records</a> |
<a href="execution.html">Execution mapping</a></nav>
<p>File snapshots preserve capture-time bytes. Matching a line to its snapshot
does not independently verify alignment with compiled text. JIT function text
has relative line numbers; no offset into the original file is inferred.</p>
<label for="source-select">Binary and captured source</label><br>
<select id="source-select"></select><p id="source-meta"></p>
<p>Green marks identify source-linked retained observations, not operation cost
or complete execution counts. Select a record count to inspect its observations.</p>
<pre id="source-code" aria-label="Captured source with line numbers"></pre>
<script type="application/json" id="source-data">__SOURCES__</script><script>
'use strict';
const sources=JSON.parse(document.getElementById('source-data').textContent),
 select=document.getElementById('source-select'), code=document.getElementById('source-code'),
 meta=document.getElementById('source-meta');
for(const s of sources){let option=document.createElement('option');option.value=s.id;
 option.textContent=s.binary_id.slice(0,12)+' · '+(s.file||'Unavailable path')+' · '+s.kind;
 select.append(option);}
function show(){const source=sources.find(s=>s.id===select.value);code.replaceChildren();
 if(!source){meta.textContent='No readable captured source snapshot is available.';return;}
 meta.textContent='Binary: '+source.binary_id+' · SHA-256: '+source.sha256+
 ' · '+source.kind+' · Compiled-text relation: '+source.compiled_text_alignment;
 for(const [index,text] of source.text.split(/\\r\\n|\\r|\\n/).entries()){
  const line=index+1;if(line>source.line_count)break;
  let row=document.createElement('span');row.id='L'+line;row.className='line';
  let anchor=document.createElement('a');anchor.className='number';anchor.href='#L'+line;
  anchor.textContent=String(line);row.append(anchor,document.createTextNode(text));
  let count=source.observed_lines[String(line)];if(count){row.classList.add('observed');
   let records=document.createElement('a');records.className='records';
   records.textContent=count+' retained records';records.href='fine_grained.html?'+
    new URLSearchParams({filter:source.file+':'+line+':',binary:source.binary_id});row.append(records);}
  code.append(row);}
 const target=document.getElementById(location.hash.slice(1));if(target)target.scrollIntoView();}
const requested=new URLSearchParams(location.search).get('source');
if(sources.some(s=>s.id===requested))select.value=requested;
select.addEventListener('change',()=>{location.href='sources.html?'+
 new URLSearchParams({source:select.value})+'#L1';});show();
</script></html>'''
