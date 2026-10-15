"""CPU-only gate fixtures. Mock pins never authorize an actual installation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from check_common_report import ContractError, digest
import c1_verifier_authorization_r4 as gate

HERE = Path(__file__).resolve().parent
PRODUCT, COMPONENT, SOURCE = 'a' * 40, 'b' * 40, 'c' * 64
INSTALL = {'nvidia': 'd' * 64, 'enflame': 'e' * 64, 'ascend': 'f' * 64}


def synthetic_freeze(backend='nvidia'):
    return dict(backend=backend, product_revision=PRODUCT, component_source_revision=COMPONENT,
                source_freeze_sha256=SOURCE, parent_install_seal_sha256=INSTALL[backend],
                candidate_frozen=True, qualification_authorized=True,
                public_docs_sha256={'public-schema': '1' * 64}, installed_native_sha256={'native': '2' * 64},
                qualification_verifier_version=gate.VERSION,
                qualification_verifier_sha256={name: digest(HERE / name) for name in gate.FILES})


class R4Authorization(unittest.TestCase):
    def mock_pins(self):
        return patch.multiple(gate, EXPECTED_PRODUCT_REVISION=PRODUCT,
                              EXPECTED_COMPONENT_REVISION=COMPONENT,
                              EXPECTED_SOURCE_FREEZE_SHA256=SOURCE,
                              EXPECTED_INSTALL_SEAL_SHA256=INSTALL)

    def test_real_preparation_gate_rejects_all_candidates_even_claimed_authorized(self):
        for revision in [None, '', '6c1a046e2725eb125da9805690f9fbb68758dcb7',
                         '77cd4623cd4f9d671b06fe4c63a6f6025a222ac2', PRODUCT]:
            with self.subTest(revision=revision):
                freeze = synthetic_freeze()
                freeze['product_revision'] = revision
                with self.assertRaisesRegex(ContractError, 'pins not frozen'):
                    gate.verify_authorization(HERE, freeze)

    def test_only_synthetic_mock_pins_accept_complete_exact_freeze_all_backends(self):
        with self.mock_pins():
            for backend in INSTALL:
                with self.subTest(backend=backend):
                    self.assertEqual(gate.verify_authorization(HERE, synthetic_freeze(backend)),
                                     synthetic_freeze(backend)['qualification_verifier_sha256'])

    def test_wrong_revision_component_source_install_and_backend_rejected(self):
        mutations = [('product_revision', '0' * 40), ('product_revision', PRODUCT[:7]),
                     ('product_revision', '6c1a046e2725eb125da9805690f9fbb68758dcb7'),
                     ('product_revision', '77cd4623cd4f9d671b06fe4c63a6f6025a222ac2'),
                     ('component_source_revision', '0' * 40), ('source_freeze_sha256', '0' * 64),
                     ('parent_install_seal_sha256', INSTALL['enflame']), ('backend', 'unknown')]
        with self.mock_pins():
            for key, value in mutations:
                with self.subTest(key=key):
                    freeze = synthetic_freeze()
                    freeze[key] = value
                    with self.assertRaises(ContractError):
                        gate.verify_authorization(HERE, freeze)

    def test_missing_and_false_authorization_or_freeze_rejected(self):
        with self.mock_pins():
            for key in ['candidate_frozen', 'qualification_authorized']:
                freeze = synthetic_freeze()
                freeze.pop(key)
                with self.assertRaisesRegex(ContractError, 'not explicitly authorized'):
                    gate.verify_authorization(HERE, freeze)
                for value in [None, False, 1, 'true']:
                    with self.subTest(key=key, value=value):
                        freeze = synthetic_freeze()
                        freeze[key] = value
                        with self.assertRaisesRegex(ContractError, 'not explicitly authorized'):
                            gate.verify_authorization(HERE, freeze)

    def test_wrong_missing_extra_and_tampered_verifier_hash_rejected(self):
        with self.mock_pins():
            for mutation in ['version', 'missing', 'extra', 'wrong_hash', 'tampered_file']:
                with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                    target = Path(tmp)
                    for name in gate.FILES:
                        (target / name).write_bytes((HERE / name).read_bytes())
                    freeze = synthetic_freeze()
                    if mutation == 'version':
                        freeze['qualification_verifier_version'] = 'C1-r2-v1'
                    elif mutation == 'missing':
                        freeze['qualification_verifier_sha256'].pop(gate.FILES[-1])
                    elif mutation == 'extra':
                        freeze['qualification_verifier_sha256']['unrelated.py'] = '0' * 64
                    elif mutation == 'wrong_hash':
                        freeze['qualification_verifier_sha256'][gate.FILES[-1]] = '0' * 64
                    else:
                        (target / gate.FILES[-1]).write_text('tampered')
                    with self.assertRaisesRegex(ContractError, 'version/file digest mismatch'):
                        gate.verify_authorization(target, freeze)

    def test_checker_tampering_not_hidden_by_recomputed_authorization_hash(self):
        with self.mock_pins(), tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            for name in gate.FILES:
                (target / name).write_bytes((HERE / name).read_bytes())
            (target / 'c1_actor_binding.py').write_text('tampered checker')
            freeze = synthetic_freeze()
            freeze['qualification_verifier_sha256']['c1_actor_binding.py'] = digest(target / 'c1_actor_binding.py')
            with self.assertRaisesRegex(ContractError, 'historical capture checker changed'):
                gate.verify_authorization(target, freeze)

    def test_install_unfrozen_or_invalid_pins_remain_closed(self):
        with self.mock_pins():
            for value in [None, '', 'd' * 63, 'not-a-hash' * 7]:
                with self.subTest(value=value), patch.object(gate, 'EXPECTED_INSTALL_SEAL_SHA256',
                                                           dict(INSTALL, nvidia=value)):
                    with self.assertRaisesRegex(ContractError, 'installation pin not frozen'):
                        gate.verify_authorization(HERE, synthetic_freeze())

    def test_runners_refuse_before_output_or_workload_subprocess(self):
        # Exercise the actual runner main entry points in server Docker. The
        # candidate pins are unresolved, so no product import or GPU can occur.
        import profile_dynamic_r4 as dynamic
        import run_common_r4 as common
        for module in [common, dynamic]:
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                freeze = root / 'freeze.json'
                freeze.write_text(json.dumps(synthetic_freeze()))
                booking = root / 'booking.json'
                booking.write_text(json.dumps(dict(exclusive=True, owner='usability_qualification',
                                                  backend='nvidia', device=0)))
                argv = ['runner', '--backend', 'nvidia', '--device', '0', '--freeze', str(freeze),
                        '--booking', str(booking), '--output', str(root / 'results'), '--pass-kind', 'repair']
                if module is dynamic:
                    eligibility = root / 'eligibility.json'
                    # Metadata fixture contains no kernel math or numerical oracle.
                    doc = dict(profiler_invoked=False, status='pass', resolved=8,
                               source_sha256={'reserve_dynamic.py': '85e5c10abd07c4a106894b9bfd27dd5f98fd89f867e22159f2a367979458e39e'},
                               results=[dict(case=case, shape_index=si, config_index=ci)
                                        for case in ['coupled_logistic', 'neighbor_accumulation']
                                        for si in [0, 1] for ci in [0, 1]])
                    eligibility.write_text(json.dumps(doc))
                    argv += ['--eligibility', str(eligibility)]
                with patch('sys.argv', argv), patch.object(module.subprocess, 'Popen') as launch:
                    with self.assertRaisesRegex(ContractError, 'pins not frozen'):
                        module.main()
                    launch.assert_not_called()
                self.assertFalse((root / 'results').exists())


if __name__ == '__main__':
    unittest.main()
