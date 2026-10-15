"""Prepared r4 gate. Empty pins intentionally forbid all candidate execution.

Replace pins only after independent review of the final source/install freezes;
commit and freeze this new version separately. Never edit the historical v1 gate.
"""
from check_common_report import digest, require

VERSION = 'C1-r4-v1'
EXPECTED_PRODUCT_REVISION = None
EXPECTED_COMPONENT_REVISION = None
EXPECTED_SOURCE_FREEZE_SHA256 = None
EXPECTED_INSTALL_SEAL_SHA256 = {'nvidia': None, 'enflame': None, 'ascend': None}
FILES = ['check_common_report.py', 'check_common_report_c1.py',
         'check_dynamic_report_c1.py', 'c1_public_plan.py', 'c1_actor_binding.py',
         'c1_verifier_authorization_r4.py', 'run_common_r4.py', 'profile_dynamic_r4.py']
UNCHANGED_CHECKERS = {
    'check_common_report.py': '4d432cde7bc9ceae67e5afb438ffd640f5912a2ce25b0cdfbc4968c74096daa1',
    'check_common_report_c1.py': 'cd029e6f1ca95b0960cbe9697fb09eca3b831d329275a57dfc6fdec53f0bd141',
    'check_dynamic_report_c1.py': 'b7f226f71dd1c27cc9a291ae93bce85057c3400c36978365fe8af9b463f7c1d9',
    'c1_public_plan.py': 'e1a3c2e51b45302f669a7effd8207605cc48b7e011b333902232b6ff5388bbed',
    'c1_actor_binding.py': 'ea145c7175b0779b1726ed2dfd43cc1d6aa6b2d98a2870a731f2d59e8331f8f5',
}


def hex_digest(value, length):
    return isinstance(value, str) and len(value) == length and all(c in '0123456789abcdef' for c in value)


def verify_authorization(here, freeze):
    require(hex_digest(EXPECTED_PRODUCT_REVISION, 40)
            and hex_digest(EXPECTED_COMPONENT_REVISION, 40)
            and hex_digest(EXPECTED_SOURCE_FREEZE_SHA256, 64),
            'r4 final runtime/source pins not frozen; candidate execution forbidden')
    backend = freeze.get('backend')
    require(backend in EXPECTED_INSTALL_SEAL_SHA256, 'unknown qualification backend')
    install_pin = EXPECTED_INSTALL_SEAL_SHA256[backend]
    require(hex_digest(install_pin, 64), 'r4 backend installation pin not frozen')
    require(freeze.get('product_revision') == EXPECTED_PRODUCT_REVISION,
            'r4 product revision mismatch')
    require(freeze.get('component_source_revision') == EXPECTED_COMPONENT_REVISION,
            'r4 component revision mismatch')
    require(freeze.get('source_freeze_sha256') == EXPECTED_SOURCE_FREEZE_SHA256,
            'r4 source-freeze digest mismatch')
    require(freeze.get('parent_install_seal_sha256') == install_pin,
            'r4 backend installation seal mismatch')
    require(freeze.get('candidate_frozen') is True
            and freeze.get('qualification_authorized') is True,
            'r4 candidate qualification not explicitly authorized/frozen')
    actual = {name: digest(here / name) for name in FILES}
    require(freeze.get('qualification_verifier_version') == VERSION
            and freeze.get('qualification_verifier_sha256') == actual,
            'r4 verifier version/file digest mismatch')
    require(all(actual[name] == expected for name, expected in UNCHANGED_CHECKERS.items()),
            'historical capture checker changed')
    return actual
