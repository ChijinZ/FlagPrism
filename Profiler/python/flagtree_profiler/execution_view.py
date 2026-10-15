"""Human-readable compiler mapping beside observed execution identities.

Static actors/dependencies are never joined to measured actors by name. All
times remain in their original clock frames; no synthetic timeline is drawn.
"""
from collections import defaultdict
from html import escape
import json
from pathlib import Path
from urllib.parse import urlencode


def _value(value):
    if value is None:
        return '<span class="unavailable">Unavailable</span>'
    if isinstance(value, dict):
        return '<dl>' + ''.join(
            '<dt>' + escape(str(key)) + '</dt><dd>' + _value(item) + '</dd>'
            for key, item in value.items()) + '</dl>'
    if isinstance(value, list):
        return '<ul>' + ''.join('<li>' + _value(item) + '</li>'
                                for item in value) + '</ul>'
    return escape(str(value))


def _table(rows):
    if not rows:
        return '<p>No entries were exported.</p>'
    if not all(isinstance(row, dict) for row in rows):
        return _value(rows)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    return ('<div class="scroll"><table><thead><tr>' +
            ''.join('<th>' + escape(str(key)) + '</th>'
                    for key in fields) + '</tr></thead><tbody>' +
            ''.join('<tr>' + ''.join('<td>' + _value(row.get(key)) + '</td>'
                                     for key in fields) + '</tr>'
                    for row in rows) + '</tbody></table></div>')


def _observed(records):
    groups = defaultdict(list)
    for record in records:
        # Clock scope and call are part of identity, not aggregation labels.
        identity = {
            key: record.get(key)
            for key in ('invocation_id', 'program', 'actor', 'semantic',
                        'clock', 'association_status')
        }
        groups[json.dumps(identity, sort_keys=True)].append(record)
    rows = []
    for key, visits in groups.items():
        identity = json.loads(key)
        by_site = defaultdict(int)
        for record in visits:
            by_site[str(record.get('site'))] += 1
        identity.update(retained_records=len(visits),
                        retained_records_by_site=dict(by_site))
        rows.append(identity)
    return _table(rows)


def render(execution, records):
    sections = []
    binaries = execution.get('binaries', [])
    for binary in binaries:
        binary_id = binary.get('binary_id')
        mapping = binary.get('mapping') or {}
        observed = [
            row for row in records if row.get('binary_id') == binary_id
        ]
        link = 'fine_grained.html?' + urlencode({'binary': binary_id or ''})
        panels = [
            '<section><h2>Binary ' + escape(str(binary_id)) + '</h2>',
            _value(
                dict(backend=binary.get('backend'),
                     mapping_status=binary.get('status'),
                     execution_model=mapping.get('execution_model'))),
            '<p><a href="' + escape(link, quote=True) + '">Inspect this '
            'binary’s internal records and source links</a></p>',
            '<h3>Observed execution identities and retained visits</h3>',
            '<p>These identities come from exported dynamic records. Each row '
            'keeps its invocation, program, actor, semantic and clock frame. '
            'Counts describe retained records, not hardware utilization, total '
            'executions or inferred loop iterations.</p>',
            _observed(observed), '<h3>Compiler execution structure</h3>',
            '<p>The following tables describe compiler artifacts. Static actors, '
            'layouts and dependencies do not prove observed activity. Static '
            'and measured actor identifiers are not matched by name.</p>'
        ]
        for key, value in mapping.items():
            if key in ('schema_version', 'backend', 'binary_id', 'status',
                       'execution_model'):
                continue
            count = f' ({len(value)} entries)' if isinstance(value,
                                                             list) else ''
            body = _table(value) if isinstance(value, list) else _value(value)
            panels.append('<details><summary>' +
                          escape(key.replace('_', ' ')) + count +
                          '</summary>' + body + '</details>')
        if binary.get('source_operations'):
            panels.append(
                '<details><summary>Compiler source operations</summary>' +
                _table(binary['source_operations']) + '</details>')
        panels.append('<h3>Mapping limits</h3>' +
                      _value(binary.get('limits', [])) + '</section>')
        sections.append(''.join(panels))
    unmatched = [
        row for row in records if not any(
            row.get('binary_id') == binary.get('binary_id')
            for binary in binaries)
    ]
    if unmatched:
        sections.append(
            '<section><h2>Records without an exported binary mapping</h2>' +
            _observed(unmatched) + '</section>')
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<title>Execution mapping · FlagPrism</title><style>'
        'body{font:14px system-ui;margin:2rem;color:#17212b}a{color:#175eb1}'
        'section{border-top:1px solid #aaa;margin-top:2rem}h2{overflow-wrap:anywhere}'
        'table{border-collapse:collapse}th,td{border:1px solid #ddd;padding:.5rem;'
        'vertical-align:top;overflow-wrap:anywhere}.scroll{overflow:auto}'
        'dl{margin:.25rem}dt{font-weight:600}dd{margin:.2rem 0 .6rem 1rem}'
        'details{padding:.6rem;border:1px solid #ddd;margin:.5rem 0}'
        'summary{cursor:pointer}.unavailable{color:#68717b}</style>'
        '<h1>Execution mapping</h1><nav><a href="index.html">Overview</a> | '
        '<a href="sources.html">Captured source</a> | '
        '<a href="fine_grained.html">Internal records</a> | '
        '<a href="observations.html">Execution and clock groups</a> | '
        '<a href="../ai/execution.json">Original mapping JSON</a></nav>'
        '<p>Expand a compiler table to inspect its complete exported entries. '
        'Measured records and compiler structure are shown separately. There is '
        'no inferred cross-actor clock alignment or hardware busy timeline.</p>'
        + (''.join(sections) if sections else
           '<p>No compiler mapping was exported.</p>') + '</html>')


def write_view(output, records):
    output = Path(output)
    path = output / 'ai/execution.json'
    execution = json.loads(path.read_text()) if path.is_file() else {}
    (output / 'report/execution.html').write_text(render(execution, records))
