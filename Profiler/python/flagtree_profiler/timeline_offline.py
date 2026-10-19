"""Select the existing retained-timeline providers without importing an SDK.

Physical decoding, target/clock evidence and mechanism interpretation belong
to each backend. Common consumers use canonical data and qualified views.
Adding a backend requires one registration entry and its provider functions;
there is no runtime plugin loader or device execution in this registry.
"""
from importlib import import_module

_PROVIDERS = ('timeline_nvidia_offline', 'timeline_ascend_offline',
              'timeline_enflame_offline')


def offline_provider(capture):
    if (type(capture) is not dict or type(capture.get('owner')) is not dict
            or type(capture.get('metadata')) is not dict
            or type(capture['metadata'].get('compiler_metadata')) is not dict):
        raise ValueError('Malformed retained producer identity')
    matches = []
    for name in _PROVIDERS:
        provider = import_module('.' + name, __package__)
        if provider.matches(capture):
            matches.append(provider)
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous offline retained producer')
    return matches[0]
