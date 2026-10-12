"""Render a version-matched standard SCF/PH/NSCF/EPW workflow from JSON."""
import argparse
import copy
import json
import math
from pathlib import Path
import re
import sys

from qe_epw_common import emit_namelist, keywords_ok, parse_namelists, registry

STAGES = ("scf", "ph", "nscf", "epw_fresh", "epw_restart")


def grid(value, name):
    if not isinstance(value, list) or len(value) != 3 or any(type(x) is not int or x < 1 for x in value):
        raise ValueError(name + " must contain three positive integers")
    return value


def consistent(values, key, value):
    if key in values and values[key] != value:
        raise ValueError("Conflicting derived parameter: " + key)
    values[key] = value


def build(case, selected):
    versions = case.get("versions", {})
    profile = registry()
    if versions.get("qe") != profile["qe_version"] or versions.get("epw") != profile["epw_version"]:
        raise ValueError("This generator requires the cached QE 7.3.1 / EPW 5.8.1 pair")
    prefix, outdir = case["prefix"], case["outdir"]
    if not isinstance(prefix, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", prefix):
        raise ValueError("prefix must be a simple filename stem")
    species, positions = case["species"], case["positions"]
    if not species or not positions:
        raise ValueError("Supply species and atomic positions")
    labels = [item["label"] for item in species]
    if len(set(labels)) != len(labels):
        raise ValueError("Duplicate species labels")
    for item in species:
        if not re.fullmatch(r"[A-Za-z]\w*", item["label"]) or not math.isfinite(float(item["mass"])) or float(item["mass"]) <= 0:
            raise ValueError("Invalid species label or mass")
        if not item["pseudo"] or any(char.isspace() for char in item["pseudo"]):
            raise ValueError("Use pseudopotential filenames without whitespace")
    for position in positions:
        if len(position) != 4 or position[0] not in labels:
            raise ValueError("Each crystal position is [species, x, y, z]")
        for coordinate in position[1:]:
            if not math.isfinite(float(coordinate)):
                raise ValueError('Coordinates must be finite')
    system = copy.deepcopy(case["system"])
    if type(system.get("ecutwfc")) not in (int, float) or not math.isfinite(system["ecutwfc"]) or system["ecutwfc"] <= 0:
        raise ValueError("Supply a positive ecutwfc in Ry")
    consistent(system, "nat", len(positions))
    consistent(system, "ntyp", len(species))
    if type(system.get("ibrav")) is not int:
        raise ValueError("Supply integer ibrav")
    if type(case["nscf_nbnd"]) is not int or case["nscf_nbnd"] < 1:
        raise ValueError("nscf_nbnd must be a positive integer")
    if type(case["epw"].get("nbndsub")) is not int or case["epw"]["nbndsub"] < 1:
        raise ValueError("nbndsub must be a positive integer")
    lower_keys = {key.lower() for key in system}
    if any(key.startswith("celldm") for key in lower_keys) and lower_keys.intersection({"a", "b", "c", "cosab", "cosac", "cosbc"}):
        raise ValueError("Choose celldm or A/B/C/cos lattice conventions, not both")
    cell = case.get("cell_angstrom")
    if system["ibrav"] == 0 and (not isinstance(cell, list) or len(cell) != 3 or any(len(row) != 3 for row in cell)):
        raise ValueError("ibrav=0 requires a 3x3 cell_angstrom matrix")
    if system["ibrav"] == 0:
        if any(not math.isfinite(float(x)) for row in cell for x in row):
            raise ValueError("Cell coordinates must be finite")
        a, b, c = [[float(x) for x in row] for row in cell]
        volume = sum(a[i] * (b[(i+1) % 3] * c[(i+2) % 3] - b[(i+2) % 3] * c[(i+1) % 3]) for i in range(3))
        if abs(volume) < 1e-12:
            raise ValueError("Cell vectors must span a nonzero volume")
    scf_grid = grid(case["scf_kgrid"], "scf_kgrid")
    coarse_k = grid(case["nscf_kgrid"], "nscf_kgrid")
    coarse_q = grid(case["qgrid"], "qgrid")
    if any(k % q for k, q in zip(coarse_k, coarse_q)):
        raise ValueError("Each coarse k dimension must be a multiple of the corresponding q dimension")
    coarse_count = coarse_k[0] * coarse_k[1] * coarse_k[2]
    if coarse_count > 2000000:
        raise ValueError("Review the requested NSCF grid before generating more than two million points")
    species_card = "ATOMIC_SPECIES\n" + "".join(
        f"{item['label']} {float(item['mass']):.12g} {item['pseudo']}\n" for item in species
    )
    position_card = "ATOMIC_POSITIONS crystal\n" + "".join(
        f"{position[0]} " + " ".join(f"{float(x):.14g}" for x in position[1:]) + "\n" for position in positions
    )
    cell_card = ""
    if system["ibrav"] == 0:
        cell_card = "CELL_PARAMETERS angstrom\n" + "".join(
            " ".join(f"{float(x):.14g}" for x in row) + "\n" for row in cell
        )
    cards = species_card + position_card + cell_card
    electrons = case.get("electrons", {"conv_thr": 1e-10})
    outputs = {}
    for stage in selected:
        if stage in ("scf", "nscf"):
            control = dict(case.get("control", {}))
            for key, value in {"calculation": stage, "prefix": prefix, "outdir": outdir, "pseudo_dir": case["pseudo_dir"]}.items():
                consistent(control, key, value)
            chosen_system = dict(system)
            if stage == "nscf":
                consistent(chosen_system, "nosym", True)
                consistent(chosen_system, "noinv", True)
                consistent(chosen_system, "nbnd", case["nscf_nbnd"])
                kpoints = ["K_POINTS crystal", str(coarse_count)]
                weight = 1.0 / coarse_count
                for i in range(coarse_k[0]):
                    for j in range(coarse_k[1]):
                        for k in range(coarse_k[2]):
                            kpoints.append(f"{i/coarse_k[0]:.16g} {j/coarse_k[1]:.16g} {k/coarse_k[2]:.16g} {weight:.16g}")
                kcard = "\n".join(kpoints) + "\n"
            else:
                kcard = "K_POINTS automatic\n" + " ".join(map(str, scf_grid)) + " 0 0 0\n"
            text = emit_namelist("control", control) + emit_namelist("system", chosen_system) + emit_namelist("electrons", electrons) + cards + kcard
            program, filename = "pw", "01_scf.in" if stage == "scf" else "03_nscf.in"
        elif stage == "ph":
            values = dict(case.get("ph", {}))
            for key, value in {"prefix": prefix, "outdir": outdir, "ldisp": True, "fildyn": prefix + ".dyn", "fildvscf": "dvscf"}.items():
                consistent(values, key, value)
            for index, value in enumerate(coarse_q, 1):
                consistent(values, f"nq{index}", value)
            values.setdefault("tr2_ph", 1e-14)
            if case.get("material_type") == "metal" and values.get("epsil"):
                raise ValueError("Do not enable epsil for this metallic workflow")
            text = emit_namelist("inputph", values)
            program, filename = "ph", "02_ph.in"
        else:
            values = copy.deepcopy(case["epw"])
            for key, value in {"prefix": prefix, "outdir": outdir, "dvscf_dir": case.get("dvscf_dir", "./save")}.items():
                consistent(values, key, value)
            for index, item in enumerate(species, 1):
                consistent(values, f"amass({index})", float(item["mass"]))
            for label, values_grid in (("nk", coarse_k), ("nq", coarse_q), ("nkf", grid(case["fine_kgrid"], "fine_kgrid")), ("nqf", grid(case["fine_qgrid"], "fine_qgrid"))):
                for index, value in enumerate(values_grid, 1):
                    consistent(values, f"{label}{index}", value)
            first = stage == "epw_fresh"
            modes = {"elph": True, "epbwrite": first, "epbread": False, "epwwrite": first, "epwread": not first, "wannierize": first}
            for key, value in modes.items():
                consistent(values, key, value)
            if values.get("a2f") and not values.get("phonselfen"):
                raise ValueError("a2f requires phonselfen")
            if values.get("nbndsub", 0) > case["nscf_nbnd"]:
                raise ValueError("nbndsub cannot exceed the original NSCF band count")
            text = emit_namelist("inputepw", values)
            program, filename = "epw", "04_epw_fresh.in" if first else "05_epw_restart.in"
        errors = keywords_ok(program, parse_namelists(text))
        if errors:
            raise ValueError("; ".join(errors))
        outputs[filename] = text
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stages", default=",".join(STAGES))
    args = parser.parse_args()
    try:
        selected = args.stages.split(",")
        if not selected or any(stage not in STAGES for stage in selected):
            raise ValueError("Stages: " + ",".join(STAGES))
        case = json.loads(args.case.read_text(encoding="utf-8"))
        outputs = build(case, selected)
        destination = args.output.resolve()
        if any((destination / name).exists() for name in outputs) or (destination / "input-manifest.json").exists():
            raise ValueError("Refusing to overwrite an existing input set; choose a new output directory")
        destination.mkdir(parents=True, exist_ok=True)
        for name, text in outputs.items():
            with (destination / name).open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
        manifest = {"versions": case["versions"], "notes": case.get("notes", ""), "nscf_kgrid": case["nscf_kgrid"], "qgrid": case["qgrid"], "files": list(outputs), "physics_convergence_verified": False}
        (destination / "input-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(destination), "files": list(outputs)}, ensure_ascii=False))
    except (ValueError, KeyError, OSError) as exc:
        print("qe-epw: " + str(exc), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
