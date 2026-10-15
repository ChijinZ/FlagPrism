"""Validate retained compiler emission evidence before binding raw actor slots."""
from __future__ import annotations

import copy
import hashlib
import json


def _digest(text):
    if not isinstance(text, str):
        raise ValueError('actor binding requires retained compiler text')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def bind_compiler_sites(handoff, *, require_binding=False):
    """Project exact-module selected sites onto emitted admissible ABI slots.

    This is compiler emission evidence, not evidence that an empty slot executed.
    Legacy artifacts without bindings are deliberately left unassociated.
    """
    sites, keys = [], set()
    for artifact in handoff.get('artifacts', []):
        manifest = artifact.get('metadata') or {}
        binding = manifest.get('runtime_actor_binding')
        if not binding:
            if require_binding:
                raise ValueError(
                    'automatic capture lacks runtime actor binding')
            continue
        original = _digest(artifact.get('llir'))
        adapted = _digest((artifact.get('adapted') or {}).get('llir'))
        manifest_sha = _digest(artifact.get('manifest_text'))
        if (original != artifact.get('sha256')
                or original != manifest.get('module_sha256')
                or adapted != (artifact.get('adapted') or {}).get('sha256')
                or manifest_sha != artifact.get('manifest_sha256')
                or json.loads(artifact['manifest_text']) != manifest
                or not handoff.get('compile_id')
                or manifest.get('compile_id') != handoff['compile_id']):
            raise ValueError(
                'runtime actor binding compiler provenance mismatch')
        kind = binding.get('actor_kind')
        slots = [0] if kind == 'AIC' else [1, 2] if kind == 'AIV' else []
        expression = ({
            'kind': 'constant_i64',
            'value': 0
        } if kind == 'AIC' else {
            'kind': 'add_i64',
            'call': 'llvm.hivm.GET.SUBBLOCKID',
            'constant': 1
        })
        if (not slots or binding.get('schema_version') != 1
                or binding.get('module_sha256') != original
                or binding.get('compile_id') != handoff['compile_id']
                or binding.get('layout') != 'actor_header4_record8_v1'
                or binding.get('segment_count') != 3
                or type(binding.get('segment_words')) is not int
                or binding['segment_words'] < 12
                or (binding['segment_words'] - 4) % 8
                or binding.get('record_actor_word') != 5
                or binding.get('admissible_slots') != slots
                or binding.get('expression') != expression
                or binding.get('value_use')
                != 'same_emitted_i64_for_segment_offset_and_record_word5' or
                binding.get('basis') != 'actual_emitted_logger_actor_value'):
            raise ValueError(
                'unsupported runtime actor binding emission contract')
        actors = [
            actor for actor in manifest.get('actors', [])
            if actor.get('function') == binding.get('function')
            and actor.get('actor_kind') == kind
            and actor.get('dynamic_observation_prepared') is True
        ]
        if len(actors) != 1:
            raise ValueError(
                'runtime actor binding function is missing or ambiguous')
        inventory = {}
        for plan_kind in ('operation', 'control'):
            for item in (manifest.get(plan_kind + '_plan')
                         or {}).get('inventory', []):
                if item.get('selected') is True:
                    key = item.get('site_id')
                    if key in inventory:
                        raise ValueError(
                            'ambiguous selected compiler site inventory')
                    inventory[key] = item
        actor = {
            'id': f"late_llvm:{original}:{binding['function']}",
            'function': binding['function'],
            'kind': kind,
            'module_sha256': original,
            'compile_id': handoff['compile_id'],
            'runtime_actor_binding': copy.deepcopy(binding),
            'binding_proof': {
                'status':
                'verified_compiler_emission_manifest',
                'manifest_sha256':
                manifest_sha,
                'original_module_sha256':
                original,
                'adapted_module_sha256':
                adapted,
                'selection_membership':
                'selected_dynamic_site_in_exact_module_plan'
            }
        }
        for site in manifest.get('dynamic_sites', []):
            selected = inventory.get(site.get('site_id'))
            if (selected is None
                    or selected.get('semantics') != site.get('semantics')
                    or selected.get('public_semantic')
                    != site.get('public_semantic')):
                raise ValueError(
                    'dynamic compiler site lacks exact selected plan membership'
                )
            for slot in slots:
                key = slot, site['site_id']
                if key in keys:
                    raise ValueError(
                        'ambiguous runtime actor/site across compiler modules')
                keys.add(key)
                sites.append(
                    dict(site,
                         actor_slot=slot,
                         compiler_actor=copy.deepcopy(actor)))
    if require_binding and not sites:
        raise ValueError(
            'automatic capture has no bound selected compiler sites')
    return sites
