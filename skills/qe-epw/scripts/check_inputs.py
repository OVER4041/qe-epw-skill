"""Static checks for the cached standard workflow; not a runtime emulator."""
import argparse
import json
import math
from pathlib import Path
import re
import sys

from qe_epw_common import base_key, get_value, keywords_ok, parse_namelists, registry, strip_comments

INTEGER_KEYS = {"nbndsub", "nbnd", "nat", "ntyp", "nstemp", "nqstep", "nqsmear", "num_iter", "ibrav"}
POSITIVE_INTEGER_KEYS = INTEGER_KEYS - {"ibrav"}
BOOLEAN_KEYS = {"elph", "epbwrite", "epbread", "epwwrite", "epwread", "wannierize", "phonselfen", "a2f", "ldisp", "nosym", "noinv", "assume_metal", "scattering", "scattering_serta", "scattering_0rta", "iterative_bte"}
REAL_KEYS = {"ecutwfc", "ecutrho", "degauss", "conv_thr", "tr2_ph", "fsthick", "degaussw", "degaussq", "delta_qsmear", "dis_win_min", "dis_win_max", "dis_froz_min", "dis_froz_max", "amass", "temps"}
POSITIVE_REAL_KEYS = {"ecutwfc", "ecutrho", "conv_thr", "tr2_ph", "amass"}


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def positive_integer(value):
    return finite_number(value) and value > 0 and float(value).is_integer()


def full_kpoints(text):
    clean = strip_comments(text)
    lines = [line for line in clean.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    clean = "\n".join(lines) + "\n"
    match = re.search(r"(?im)^\s*K_POINTS\s+[\{\(]?crystal[\}\)]?\s*\n\s*(\d+)\s*\n", clean)
    if not match:
        raise ValueError("EPW NSCF workflow expects the explicit full crystal k grid")
    count = int(match.group(1))
    rows = clean[match.end():].splitlines()[:count]
    try:
        points = [[float(re.sub(r"[dD]", "e", token)) for token in line.split()] for line in rows]
    except ValueError as exc:
        raise ValueError("Invalid NSCF k-point list") from exc
    if count < 1 or len(points) != count or any(len(p) != 4 or not all(math.isfinite(x) for x in p) for p in points):
        raise ValueError("Invalid NSCF k-point list or count")
    return points


def wrapped(value):
    return round(value % 1.0, 10) % 1.0


def check_file(path):
    errors, warnings = [], []
    text = path.read_text(encoding="utf-8")
    try:
        groups = parse_namelists(text)
    except ValueError as exc:
        return {"file": str(path), "errors": [str(exc)], "warnings": []}, {}
    program = "epw" if "inputepw" in groups else "ph" if "inputph" in groups else "pw"
    errors += keywords_ok(program, groups)
    section = groups.get("inputepw", groups.get("inputph", groups.get("system", {})))
    for group in groups.values():
        for key in group:
            value = get_value(group, key)
            name = base_key(key)
            if name in BOOLEAN_KEYS and type(value) is not bool:
                errors.append(key + " must be a Fortran logical value")
            is_grid = re.fullmatch(r"n[kq]f?[123]", name)
            if name in INTEGER_KEYS or is_grid:
                if not finite_number(value) or not re.fullmatch(r"[+-]?\d+", group[key].strip()):
                    errors.append(key + " must be a finite integer")
                elif name in POSITIVE_INTEGER_KEYS and value <= 0:
                    errors.append(key + " must be positive")
                elif is_grid and value < 0:
                    errors.append(key + " cannot be negative")
            if name in REAL_KEYS:
                # General Fortran array/repetition syntax is outside this small parser.
                if name == "temps" and "(" not in key and not finite_number(value):
                    warnings.append("Review unindexed temps array syntax manually; generator uses indexed entries")
                elif not finite_number(value):
                    errors.append(key + " must be a finite real number")
                elif name in POSITIVE_REAL_KEYS and value <= 0:
                    errors.append(key + " must be positive")
    if program == "epw":
        get = lambda key, default=None: get_value(section, key, default)
        if get("a2f") is True and get("phonselfen") is not True:
            errors.append("a2f requires phonselfen=.true.")
        if get("epwread") is True and get("wannierize") is True:
            errors.append("epwread and wannierize cannot both be true")
        if get("epwread") is True and get("epbread") is True:
            errors.append("Do not mix Bloch and Wannier restart modes")
        if get("assume_metal") is True:
            # QE 7.3.1 ephwann_shuffle calls scattering_rate_q only on this path.
            # IBTE uses print_ibte/transport_iter instead, including for metals.
            etf_mem = get("etf_mem", 1)
            if get("scattering") is True and get("iterative_bte") is not True and finite_number(etf_mem) and etf_mem < 3:
                errors.append("Metal scattering with iterative_bte=.false. and etf_mem<3 reaches scattering_rate_q, which rejects metals in EPW 5.8.1")
            if get("iterative_bte") is True:
                warnings.append("Metal IBTE has a separate supported code path; EPW 6.0 reports a population fix, so verify the installed 5.8.1 build before trusting transport results")
        if get("iterative_bte") is True:
            for axis in (1, 2, 3):
                if get("nkf" + str(axis), 0) != get("nqf" + str(axis), 0):
                    errors.append("EPW 5.8.1 IBTE requires identical homogeneous fine k and q grids")
                    break
        if finite_number(get("dis_win_min")) and get("dis_win_min") > -9999:
            warnings.append("EPW 5.8.1 ignores dis_win_min; review bands_skipped and the actual lower band manifold instead")
        for lower, upper in (("dis_froz_min", "dis_froz_max"),):
            if finite_number(get(lower)) and finite_number(get(upper)) and get(lower) >= get(upper):
                errors.append(lower + " must be below " + upper)
        for outer, inner, sense in (("dis_win_max", "dis_froz_max", -1),):
            if finite_number(get(outer)) and finite_number(get(inner)) and sense * (get(inner) - get(outer)) < 0:
                errors.append("Frozen window must lie inside the outer disentanglement window")
        if not get("epwread"):
            if not get("proj(1)") and not get("auto_projections") and not get("scdm_proj"):
                warnings.append("Review Wannier projections before a fresh run")
        else:
            warnings.append("Check the matching EPW 5.8.1 restart bundle, including prefix.ukk; file existence does not verify compatibility")
        warnings.append("Check fine-grid, electronic broadening, band interpolation and frozen-state-count convergence")
    if program == "ph" and get_value(section, "ldisp") is True and not get_value(section, "fildvscf"):
        errors.append("PH grid run must save fildvscf for the EPW workflow")
    if program == "pw":
        if not {"control", "system", "electrons"} <= groups.keys():
            errors.append("Standard PW workflow expects CONTROL, SYSTEM and ELECTRONS")
        control = groups.get("control", {})
        if get_value(control, "calculation") == "nscf":
            try:
                points = full_kpoints(text)
                if len({tuple(wrapped(x) for x in p[:3]) for p in points}) != len(points):
                    errors.append("NSCF k grid contains duplicate points modulo reciprocal lattice vectors")
                # QE NSCF weights do not affect eigenvectors; weights of one are valid.
            except ValueError as exc:
                errors.append(str(exc))
            if not get_value(section, "nosym") or not get_value(section, "noinv"):
                warnings.append("Review symmetry reduction for the full NSCF grid")
    return {"file": str(path), "program": program, "errors": errors, "warnings": warnings}, groups


def run(paths):
    reports, data = [], []
    for path in paths:
        report, groups = check_file(path)
        reports.append(report)
        if groups:
            data.append((report, groups))
    prefixes, directories = set(), set()
    nscf_data = []
    grid_read_errors = []
    for report, groups in data:
        primary = groups.get("inputepw", groups.get("inputph", groups.get("control", {})))
        if "prefix" in primary:
            prefixes.add(str(get_value(primary, "prefix")))
        if "outdir" in primary:
            directories.add(str(get_value(primary, "outdir")))
        if get_value(groups.get("control", {}), "calculation") in ("nscf", "bands"):
            nbnd = get_value(groups.get("system", {}), "nbnd")
            try:
                points = full_kpoints(Path(report["file"]).read_text(encoding="utf-8"))
            except ValueError as exc:
                points = []
                grid_read_errors.append(str(exc))
            nscf_data.append((nbnd, points))
    cross_errors = []
    if any("inputepw" in groups for report, groups in data):
        cross_errors.extend(grid_read_errors)
    if len(prefixes) > 1:
        cross_errors.append("prefix mismatch across supplied workflow files")
    if len(directories) > 1:
        cross_errors.append("outdir mismatch across supplied workflow files")
    for report, groups in data:
        epw = groups.get("inputepw", {})
        if not epw:
            continue
        nk = [get_value(epw, f"nk{i}") for i in (1, 2, 3)]
        nq = [get_value(epw, f"nq{i}") for i in (1, 2, 3)]
        if all(positive_integer(x) for x in nk + nq) and any(int(k) % int(q) for k, q in zip(nk, nq)):
            cross_errors.append("Coarse k dimensions must be multiples of corresponding q dimensions")
        if all(positive_integer(x) for x in nk):
            dims = [int(x) for x in nk]
            for nbnd, points in nscf_data:
                if not points:
                    continue
                if len(points) != math.prod(dims):
                    cross_errors.append("EPW coarse k dimensions disagree with NSCF point count")
                    continue
                indices = set()
                for point in points:
                    scaled = [(point[i] % 1.0) * dims[i] for i in range(3)]
                    if any(abs(x - round(x)) > 1e-7 for x in scaled):
                        cross_errors.append("EPW coarse k dimensions disagree with NSCF Gamma-centered grid coordinates")
                        break
                    indices.add(tuple(round(x) % dims[i] for i, x in enumerate(scaled)))
                if len(indices) != len(points):
                    cross_errors.append("NSCF points do not form the complete EPW coarse k grid")
        elif all(x is not None for x in nk):
            cross_errors.append("Standard coarse k dimensions must be positive integers")
        for other, sections in data:
            ph = sections.get("inputph", {})
            if ph and any(get_value(epw, f"nq{i}") != get_value(ph, f"nq{i}") for i in (1, 2, 3)):
                cross_errors.append("EPW coarse q dimensions disagree with PH")
        subspace = get_value(epw, "nbndsub")
        if finite_number(subspace) and any(positive_integer(nbnd) and subspace > nbnd for nbnd, points in nscf_data):
            cross_errors.append("Wannier subspace exceeds NSCF band count")
    passed = not cross_errors and not any(item["errors"] for item in reports)
    return {"profile": registry()["profile"], "passed": passed, "files": reports, "cross_file_errors": sorted(set(cross_errors)), "physics_convergence_verified": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    paths = []
    for path in args.paths:
        paths.extend(sorted(path.glob("*.in")) if path.is_dir() else [path])
    if not paths:
        parser.error("No .in files found")
    try:
        report = run(paths)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(0 if report["passed"] else 2)
    except (ValueError, OSError) as exc:
        print("qe-epw: " + str(exc), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
