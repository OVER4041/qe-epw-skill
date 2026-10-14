"""Offline regression checks for the installed skill; no QE or SSH execution."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1] / "skills" / "qe-epw"
sys.path.insert(0, str(SKILL / "scripts"))
from qe_epw_common import emit_namelist, parse_namelists, get_value
from render_inputs import build, STAGES
from check_inputs import run, full_kpoints
from check_runtime import checkpoint, output


class SkillChecks(unittest.TestCase):
    def setUp(self):
        self.case = json.loads((SKILL / "assets/case.example.json").read_text(encoding="utf-8"))
        self.temp = tempfile.TemporaryDirectory(prefix="qe_epw_test_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def report(self, outputs):
        paths = []
        for name, text in outputs.items():
            path = self.root / name
            path.write_text(text, encoding="utf-8", newline="\n")
            paths.append(path)
        return run(paths)

    def small_case(self):
        case = copy.deepcopy(self.case)
        case["nscf_kgrid"] = [2, 3, 4]
        case["qgrid"] = [1, 1, 2]
        return case

    def epw_error(self, additions):
        text = build(self.small_case(), ["epw_fresh"])["04_epw_fresh.in"]
        text = text.rstrip().removesuffix("/") + additions + "\n/\n"
        return self.report({"epw.in": text})

    def test_example_workflow(self):
        outputs = build(self.case, STAGES)
        self.assertEqual(len(outputs), 5)
        report = self.report(outputs)
        self.assertTrue(report["passed"], report)
        self.assertFalse(report["physics_convergence_verified"])

    def test_full_noncubic_grid(self):
        outputs = build(self.small_case(), STAGES)
        self.assertEqual(len(full_kpoints(outputs["03_nscf.in"])), 24)
        self.assertTrue(self.report(outputs)["passed"])

    def test_full_bands_grid_preserves_symmetry_and_is_cross_checked(self):
        case = self.small_case()
        case['coarse_calculation'] = 'bands'
        outputs = build(case, STAGES)
        groups = parse_namelists(outputs['03_nscf.in'])
        self.assertEqual(get_value(groups['control'], 'calculation'), 'bands')
        self.assertNotIn('nosym', groups['system'])
        self.assertNotIn('noinv', groups['system'])
        self.assertTrue(self.report(outputs)['passed'])
        outputs['04_epw_fresh.in'] = outputs['04_epw_fresh.in'].replace('nk1 = 2', 'nk1 = 3').replace('nk2 = 3', 'nk2 = 2')
        self.assertFalse(self.report(outputs)['passed'])

    def test_bands_path_is_not_an_epw_coarse_grid(self):
        case = self.small_case()
        case['coarse_calculation'] = 'bands'
        outputs = build(case, STAGES)
        outputs['03_nscf.in'] = outputs['03_nscf.in'].split('K_POINTS crystal')[0] + 'K_POINTS crystal_b\n2\n0 0 0 20\n0.5 0 0 1\n'
        self.assertFalse(self.report(outputs)['passed'])
        self.assertTrue(self.report({'bands.in': outputs['03_nscf.in']})['passed'])

    def test_invalid_coarse_calculation_rejected(self):
        case = self.small_case()
        case['coarse_calculation'] = 'relax'
        with self.assertRaisesRegex(ValueError, 'coarse_calculation'):
            build(case, STAGES)

    def test_ignored_outer_lower_window_warns_without_false_errors(self):
        text = build(self.case, ['epw_fresh'])['04_epw_fresh.in']
        text = text.replace('dis_win_min = -2', 'dis_win_min = 100')
        result = self.report({'epw.in': text})
        self.assertTrue(result['passed'], result)
        self.assertTrue(any('ignores dis_win_min' in w for w in result['files'][0]['warnings']))

    def test_restart_preflight_catches_missing_rotation_matrix(self):
        for name in ['epwdata.fmt', 'vmedata.fmt', 'crystal.fmt', 'demo.epmatwp']:
            (self.root / name).write_bytes(b'fixture')
        self.assertFalse(checkpoint(self.root, 'demo')['passed'])
        (self.root / 'demo.ukk').write_bytes(b'fixture')
        result = checkpoint(self.root, 'demo')
        self.assertTrue(result['passed'])
        self.assertFalse(result['checkpoint_compatibility_verified'])
        (self.root / 'demo.epmatwp').write_bytes(b'')
        self.assertFalse(checkpoint(self.root, 'demo')['passed'])

    def test_epw_completion_does_not_require_qe_marker(self):
        text = 'Program EPW v.5.8.1\nTotal program execution\nfunctionality-dependent EPW.bib file.\n'
        self.assertTrue(output('epw', text, 0)['passed'])
        self.assertFalse(output('epw', text, 1)['passed'])
        self.assertFalse(output('epw', text.replace('functionality-dependent EPW.bib file.', ''), 0)['passed'])
        self.assertFalse(output('epw', text + 'Error in routine\n', 0)['passed'])
        self.assertFalse(output('epw', text.replace('5.8.1', '6.1'), 0)['passed'])

    def test_controlled_ph_stop_is_incomplete_despite_normal_exit(self):
        self.assertTrue(output('ph', 'JOB DONE.\n', 0)['passed'])
        self.assertFalse(output('ph', 'Maximum CPU time exceeded\nJOB DONE.\n', 0)['passed'])

    def test_weights_of_one_are_legal_nscf(self):
        outputs = build(self.small_case(), STAGES)
        text = outputs["03_nscf.in"]
        header, rows = text.split("K_POINTS crystal\n24\n")
        outputs["03_nscf.in"] = header + "K_POINTS crystal\n24\n" + "".join(" ".join(line.split()[:3]) + " 1\n" for line in rows.splitlines())
        self.assertTrue(self.report(outputs)["passed"])

    def test_same_point_count_different_shape_rejected(self):
        outputs = build(self.small_case(), STAGES)
        outputs["04_epw_fresh.in"] = outputs["04_epw_fresh.in"].replace("nk1 = 2", "nk1 = 3").replace("nk2 = 3", "nk2 = 2")
        report = self.report(outputs)
        self.assertFalse(report["passed"])
        self.assertTrue(any("coordinates" in error for error in report["cross_file_errors"]))

    def test_duplicate_grid_points_rejected(self):
        outputs = build(self.small_case(), STAGES)
        header, rows = outputs["03_nscf.in"].split("K_POINTS crystal\n24\n")
        rows = rows.splitlines()
        rows[1] = rows[0]
        outputs["03_nscf.in"] = header + "K_POINTS crystal\n24\n" + "\n".join(rows) + "\n"
        self.assertFalse(self.report(outputs)["passed"])

    def test_prefix_mismatch_rejected(self):
        outputs = build(self.small_case(), STAGES)
        outputs["02_ph.in"] = outputs["02_ph.in"].replace("prefix = 'cu'", "prefix = 'different'")
        self.assertIn("prefix mismatch across supplied workflow files", self.report(outputs)["cross_file_errors"])

    def test_q_grid_mismatch_rejected(self):
        outputs = build(self.small_case(), STAGES)
        outputs["02_ph.in"] = outputs["02_ph.in"].replace("nq1 = 1", "nq1 = 2")
        self.assertFalse(self.report(outputs)["passed"])

    def test_subspace_above_bands_rejected(self):
        outputs = build(self.small_case(), STAGES)
        outputs["03_nscf.in"] = outputs["03_nscf.in"].replace("nbnd = 20", "nbnd = 4")
        self.assertFalse(self.report(outputs)["passed"])

    def test_legacy_unknown_keys_rejected(self):
        for key in ("ecutwfc = 80", "kmaps = .true.", "tempsmin = 300", "eps_acoustic = 1"):
            with self.subTest(key=key):
                report = self.epw_error(key)
                self.assertFalse(report["passed"])
                self.assertTrue(any("Unknown epw key" in error for error in report["files"][0]["errors"]))

    def test_incompatible_coarse_grids_rejected(self):
        self.case["nscf_kgrid"] = [6, 6, 6]
        with self.assertRaisesRegex(ValueError, "multiple"):
            build(self.case, STAGES)
        outputs = build(self.small_case(), STAGES)
        outputs["04_epw_fresh.in"] = outputs["04_epw_fresh.in"].replace("nq2 = 1", "nq2 = 2")
        self.assertFalse(self.report(outputs)["passed"])

    def test_restart_flags(self):
        text = build(self.case, ["epw_restart"])["05_epw_restart.in"]
        epw = parse_namelists(text)["inputepw"]
        self.assertIs(get_value(epw, "epwread"), True)
        self.assertIs(get_value(epw, "wannierize"), False)
        self.assertIs(get_value(epw, "epbread"), False)

    def test_restart_with_wannier_rejected(self):
        text = build(self.case, ["epw_restart"])["05_epw_restart.in"].replace("wannierize = .false.", "wannierize = .true.")
        self.assertFalse(self.report({"epw.in": text})["passed"])

    def test_a2f_without_phonselfen_rejected(self):
        text = build(self.case, ["epw_fresh"])["04_epw_fresh.in"].replace("phonselfen = .true.", "phonselfen = .false.")
        self.assertFalse(self.report({"epw.in": text})["passed"])

    def test_wrong_version_rejected(self):
        self.case["versions"]["epw"] = "6.1"
        with self.assertRaisesRegex(ValueError, "cached"):
            build(self.case, STAGES)

    def test_invalid_config_values_rejected(self):
        for section, key, value in (("system", "ecutwfc", "80"), ("system", "ecutwfc", float("nan")), ("system", "ibrav", 2.0), ("epw", "nbndsub", 0)):
            with self.subTest(key=key, value=value):
                case = copy.deepcopy(self.case)
                case[section][key] = value
                with self.assertRaises(ValueError):
                    build(case, STAGES)

    def test_nan_mass_and_coordinate_rejected(self):
        case = copy.deepcopy(self.case)
        case["species"][0]["mass"] = float("nan")
        with self.assertRaises(ValueError):
            build(case, STAGES)
        case = copy.deepcopy(self.case)
        case["positions"][0][1] = float("nan")
        with self.assertRaises(ValueError):
            build(case, STAGES)

    def test_lattice_conventions_rejected(self):
        self.case["system"]["celldm(1)"] = 6.8
        with self.assertRaisesRegex(ValueError, "conventions"):
            build(self.case, STAGES)

    def test_explicit_cell_and_singular_cell(self):
        self.case["system"] = {"ibrav": 0, "ecutwfc": 80}
        self.case["cell_angstrom"] = [[3, 0, 0], [0, 3, 0], [0, 0, 3]]
        self.assertIn("CELL_PARAMETERS angstrom", build(self.case, ["scf"])["01_scf.in"])
        self.case["cell_angstrom"][2] = [0, 0, 0]
        with self.assertRaisesRegex(ValueError, "volume"):
            build(self.case, ["scf"])

    def test_fortran_quotes_comments_slashes(self):
        values = {"prefix": "O'Brien", "outdir": "/scratch/!x=y", "temps": [100, 300], "wannierize": False}
        text = emit_namelist("inputepw", values).replace("temps(1)", "! comment / =\n  temps(1)")
        group = parse_namelists(text)["inputepw"]
        self.assertEqual(get_value(group, "prefix"), "O'Brien")
        self.assertEqual(get_value(group, "outdir"), "/scratch/!x=y")
        self.assertEqual(get_value(group, "temps(2)"), 300)
        self.assertIs(get_value(group, "wannierize"), False)

    def test_duplicate_assignment_and_unterminated_string(self):
        for text in ("&inputepw\nprefix='cu'\nprefix='other'\n/\n", "&inputepw\nprefix='cu\n/\n"):
            with self.assertRaises(ValueError):
                parse_namelists(text)

    def test_window_and_bad_types_rejected(self):
        text = build(self.case, ["epw_fresh"])["04_epw_fresh.in"]
        for bad in (text.replace("dis_froz_max = 18", "dis_froz_max = 40"), text.replace("dis_win_max = 30", "dis_win_max = 'bad'"), text.replace("nbndsub = 6", "nbndsub = 6.0"), text.replace("nk1 = 12", "nk1 = .true.")):
            with self.subTest(input=bad[:30]):
                self.assertFalse(self.report({"epw.in": bad})["passed"])

    def test_legacy_noniterative_metal_scattering_rejected(self):
        self.assertFalse(self.epw_error("assume_metal = .true.\nscattering = .true.")["passed"])

    def test_metal_ibte_not_rejected_by_legacy_routine_guard(self):
        result = self.epw_error("assume_metal = .true.\nscattering = .true.\niterative_bte = .true.")
        self.assertTrue(result["passed"], result)

    def test_metal_spectrum_without_scattering_allowed(self):
        self.assertTrue(self.epw_error("assume_metal = .true.")["passed"])

    def test_ibte_mismatched_fine_grids_rejected(self):
        outputs = build(self.small_case(), ["epw_fresh"])
        text = outputs["04_epw_fresh.in"].rstrip().removesuffix("/")
        text += "iterative_bte = .true.\n/\n"
        # Unequal fine meshes trigger a runtime input error in epw_readin.
        text = text.replace("nqf1 = " + str(self.case["fine_qgrid"][0]), "nqf1 = 1")
        self.assertFalse(self.report({"epw.in": text})["passed"])

    def test_cli_generates_then_refuses_overwrite(self):
        case_path = self.root / "case.json"
        case_path.write_text(json.dumps(self.small_case()), encoding="utf-8")
        command = [sys.executable, "-B", "-X", "utf8", str(SKILL / "scripts/render_inputs.py"), "--case", str(case_path), "--output", str(self.root / "inputs")]
        first = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        manifest = json.loads((self.root / "inputs/input-manifest.json").read_text())
        self.assertFalse(manifest["physics_convergence_verified"])
        before = (self.root / "inputs/01_scf.in").read_bytes()
        second = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(second.returncode, 2)
        self.assertIn("overwrite", second.stderr)
        self.assertEqual(before, (self.root / "inputs/01_scf.in").read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
