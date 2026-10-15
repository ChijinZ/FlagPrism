"""Independent C1 public-plan constraints; original C0 verifier stays unchanged.

Scope binding is separate: these typed budget checks never exempt a record from
selected binary/module/actor/semantic inventory membership. No product imports.
"""
from check_common_report import ContractError, integer, require

CONTROL_POLICY = 'all_requested_original_control_sites'
CONTROL_BUDGET_SCOPE = 'existing_primitives_and_original_loop_headers'


def validate_control_entry(entry):
    require(entry.get('plan_kind') == 'control', 'null budget requires typed control plan')
    require(isinstance(entry.get('binary_id'), str) and entry['binary_id'], 'control binary identity missing')
    require(isinstance(entry.get('module_sha256'), str) and len(entry['module_sha256']) == 64, 'control compiler module identity missing')
    plan = entry.get('plan')
    require(isinstance(plan, dict), 'control plan object missing')
    require(plan.get('policy') == CONTROL_POLICY, 'unknown/unbounded control policy')
    require(plan.get('budget_scope') == CONTROL_BUDGET_SCOPE, 'control budget scope missing')
    require('max_sites' in plan and plan['max_sites'] is None, 'all-requested control budget must be explicit null')
    require(plan.get('operation_max_sites_applies') is False, 'operation budget incorrectly includes controls')
    require(integer(plan.get('record_capacity_per_actor')) and plan['record_capacity_per_actor'] > 0,
            'dynamic actor capacity missing; null static cap does not mean unlimited records')
    inventory = plan.get('inventory')
    require(isinstance(inventory, list), 'control candidate inventory missing')
    for key in ['candidate_count', 'selected_count']:
        require(integer(plan.get(key)) and plan[key] >= 0, 'invalid control inventory count')
    require(plan['candidate_count'] == len(inventory), 'control candidate count differs from complete inventory')
    ids = set()
    selected = []
    for item in inventory:
        site = item.get('site_id')
        require(integer(site) and site >= 0 and site not in ids, 'duplicate/invalid control site ID')
        ids.add(site)
        require(isinstance(item.get('selected'), bool), 'control selected status missing')
        require(isinstance(item.get('selection_reason'), str) and item['selection_reason'], 'control selection/exclusion reason missing')
        require(isinstance(item.get('public_semantic'), str) and item['public_semantic'], 'control public semantic missing')
        require(isinstance(item.get('operation'), str) and item['operation'], 'original control operation missing')
        if item['selected']:
            selected.append(item)
    require(plan['selected_count'] == len(selected), 'control selected count differs from inventory')
    return selected


def selected_control_item(entry, site, semantic):
    selected = validate_control_entry(entry)
    matches = [item for item in selected if item['site_id'] == site and item['public_semantic'] == semantic]
    require(len(matches) == 1, 'control record missing from matching selected semantic inventory')
    return matches[0]
