"""Explicit version/hash gate for the independently frozen C1-r2 runners."""
from check_common_report import digest, require

FILES = ['check_common_report.py', 'check_common_report_c1.py',
         'check_dynamic_report_c1.py', 'c1_public_plan.py', 'c1_actor_binding.py',
         'c1_verifier_authorization.py', 'run_common_c1.py', 'profile_dynamic_c1.py']


def verify_authorization(here, freeze):
    require(freeze.get('product_revision') == '6c1a046e2725eb125da9805690f9fbb68758dcb7',
            'C1-r2 runner requires the declared product freeze')
    require(freeze.get('qualification_authorized') is True, 'candidate qualification not authorized')
    actual = {name: digest(here / name) for name in FILES}
    require(freeze.get('qualification_verifier_version') == 'C1-r2-v1'
            and freeze.get('qualification_verifier_sha256') == actual,
            'missing/mismatched independent verifier freeze')
    require(actual['check_common_report.py'] == '4d432cde7bc9ceae67e5afb438ffd640f5912a2ce25b0cdfbc4968c74096daa1',
            'original C0 checker changed')
    return actual
