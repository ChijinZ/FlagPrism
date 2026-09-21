"""Shared, device-independent handling of optional caller context."""
import json
import math


def snapshot(value, *, require_object=True):
    """Own a finite JSON snapshot. Python tuples retain legacy array conversion."""
    ancestors = set()

    def check(item, path):
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if not isinstance(item, (dict, list, tuple)):
            raise ValueError(
                f"metadata {path or '/'}: expected finite JSON, got {type(item).__name__}"
            )
        if id(item) in ancestors:
            raise ValueError(f"metadata {path or '/'}: cyclic value")
        ancestors.add(id(item))
        entries = item.items() if isinstance(item, dict) else enumerate(item)
        for key, child in entries:
            if isinstance(item, dict) and not isinstance(key, str):
                raise ValueError(
                    f"metadata {path or '/'}: object keys must be strings")
            token = str(key).replace('~', '~0').replace('/', '~1')
            check(child, path + '/' + token)
        ancestors.remove(id(item))

    check(value, '')
    if require_object and not isinstance(value, dict):
        raise ValueError(
            f"metadata /: expected object, got {type(value).__name__}")
    return json.loads(json.dumps(value, allow_nan=False))


def diagnose(metadata):
    issues, missing = [], []

    def field(parent, name, path, expected, valid, recommended=False):
        value = parent.get(name)
        location = path + '/' + name
        if value is None:
            if recommended:
                missing.append(location)
            return None
        if not valid(value):
            issues.append(
                dict(
                    path=location,
                    code='invalid_structure',
                    expected=expected,
                    actual_type=type(value).__name__,
                    hint=
                    'Original value is retained in supplied; see the workload template in ai/README.md.'
                ))
            return None
        return value

    for name in ('hardware', 'software', 'workload', 'compilation'):
        section = field(metadata, name, '', 'object or null',
                        lambda v: isinstance(v, dict), name == 'workload')
        if name != 'workload' or section is None:
            continue
        field(section, 'operator', '/workload', 'nonempty string or null',
              lambda v: isinstance(v, str) and bool(v.strip()), True)
        field(section, 'parameters', '/workload', 'object or null',
              lambda v: isinstance(v, dict), True)
        for policy in ('warmup', 'measurement', 'validation'):
            path = '/workload/' + policy
            value = field(section, policy, '/workload', 'object or null',
                          lambda v: isinstance(v, dict), True)
            if value is None:
                continue
            if policy != 'validation':
                field(value, 'iterations', path, 'nonnegative integer or null',
                      lambda v: type(v) is int and v >= 0, True)
            if policy == 'measurement':
                for key in ('scope', 'synchronization'):
                    field(value, key, path, 'nonempty string or null',
                          lambda v: isinstance(v, str) and bool(v.strip()),
                          True)
            if policy == 'validation':
                field(
                    value, 'status', path,
                    'passed, failed, not_checked or unknown',
                    lambda v: isinstance(v, str) and v in
                    ('passed', 'failed', 'not_checked', 'unknown'), True)
                field(value, 'reference', path, 'string or null',
                      lambda v: isinstance(v, str))
                for key in ('atol', 'rtol'):
                    field(
                        value, key, path, 'nonnegative finite number or null',
                        lambda v: type(v) in (float, int) and v >= 0 and
                        (type(v) is int or math.isfinite(v)))
    return dict(metadata_issues=issues, metadata_missing_fields=missing)


TEMPLATE = {
    "workload": {
        "operator": None,
        "parameters": {},
        "warmup": {
            "iterations": None
        },
        "measurement": {
            "iterations": None,
            "scope": None,
            "synchronization": None
        },
        "validation": {
            "status": "not_checked",
            "reference": None,
            "atol": None,
            "rtol": None
        }
    }
}
