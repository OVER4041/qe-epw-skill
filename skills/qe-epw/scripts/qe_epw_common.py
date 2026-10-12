"""Small Fortran namelist helpers; no third-party runtime dependencies."""
from pathlib import Path
import json
import math
import re

ROOT = Path(__file__).resolve().parents[1]
KEY = re.compile(r"[A-Za-z]\w*(?:\(\d+(?:,\d+)*\))?\Z")
UNIT_COMMENTS = {
    "system": {"a": "angstrom", "b": "angstrom", "c": "angstrom",
               "celldm": "celldm(1): bohr; remaining components: dimensionless",
               "ecutwfc": "Ry", "ecutrho": "Ry", "degauss": "Ry"},
    "electrons": {"conv_thr": "Ry"},
    "inputepw": {"amass": "amu", "degaussw": "eV", "fsthick": "eV",
                 "degaussq": "meV", "delta_qsmear": "meV", "temps": "K",
                 "dis_win_min": "eV, QE energy reference",
                 "dis_win_max": "eV, QE energy reference",
                 "dis_froz_min": "eV, QE energy reference",
                 "dis_froz_max": "eV, QE energy reference",
                 "eps_acustic": "cm^-1"}
}



def registry():
    return json.loads((ROOT / "assets/qe-7.3.1_epw-5.8.1.json").read_text(encoding="utf-8"))


def base_key(key):
    return key.lower().split("(", 1)[0]


def literal(value):
    if isinstance(value, bool):
        return ".true." if value else ".false."
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Input numbers must be finite")
        return format(value, ".14g").replace("e", "d")
    if isinstance(value, str):
        if any(ord(char) < 32 for char in value):
            raise ValueError("Namelist strings must be single-line")
        return "'" + value.replace("'", "''") + "'"
    raise ValueError("Use scalar values or indexed one-dimensional arrays")


def emit_namelist(name, values):
    lines = ["&" + name.upper()]
    for key, value in values.items():
        if not KEY.fullmatch(key):
            raise ValueError("Invalid namelist key: " + key)
        unit = UNIT_COMMENTS.get(name.lower(), {}).get(base_key(key))
        suffix = " ! " + unit if unit else ""
        if isinstance(value, list):
            if "(" in key or not value:
                raise ValueError("Use an unindexed name and a nonempty scalar array")
            for index, item in enumerate(value, 1):
                lines.append(f"  {key}({index}) = {literal(item)}{suffix}")
        else:
            lines.append(f"  {key} = {literal(value)}{suffix}")
    return "\n".join(lines + ["/"]) + "\n"


def strip_comments(text):
    output = []
    quote = None
    index = 0
    while index < len(text):
        char = text[index]
        if quote:
            output.append(char)
            if char == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    output.append(text[index + 1])
                    index += 1
                else:
                    quote = None
        elif char in ("'", '"'):
            quote = char
            output.append(char)
        elif char == "!":
            while index < len(text) and text[index] != "\n":
                index += 1
            if index < len(text):
                output.append("\n")
        else:
            output.append(char)
        index += 1
    if quote:
        raise ValueError("Unterminated quoted string")
    return "".join(output)


def mask_strings(text):
    masked = list(text)
    quote = None
    index = 0
    while index < len(text):
        char = text[index]
        if quote:
            masked[index] = " " if char != "\n" else "\n"
            if char == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    masked[index + 1] = " "
                    index += 1
                else:
                    quote = None
        elif char in ("'", '"'):
            quote = char
            masked[index] = " "
        index += 1
    return "".join(masked)


def value_of(raw):
    raw = raw.strip().rstrip(",").strip()
    lowered = raw.lower()
    if lowered in (".true.", ".t."):
        return True
    if lowered in (".false.", ".f."):
        return False
    if len(raw) >= 2 and raw[0] in ("'", '"') and raw[-1] == raw[0]:
        return raw[1:-1].replace(raw[0] * 2, raw[0])
    try:
        return float(re.sub(r"[dD]", "e", raw))
    except ValueError:
        return raw


def parse_namelists(text):
    clean = strip_comments(text.replace("\r\n", "\n"))
    masked = mask_strings(clean)
    groups = {}
    end = 0
    group_pattern = re.compile(r"(?m)^\s*&([A-Za-z]\w*)")
    assignment = re.compile(r"([A-Za-z]\w*(?:\s*\(\s*\d+(?:\s*,\s*\d+)*\s*\))?)\s*=")
    while match := group_pattern.search(masked, end):
        name = match.group(1).lower()
        if name == "end":
            raise ValueError("Unexpected &END")
        closure = re.search(r"/|&end\b", masked[match.end():], re.I)
        if not closure:
            raise ValueError("Missing namelist terminator for " + name)
        finish = match.end() + closure.start()
        body = clean[match.end():finish]
        body_mask = masked[match.end():finish]
        keys = list(assignment.finditer(body_mask))
        leading = body_mask[:keys[0].start()] if keys else body_mask
        if leading.strip(" \r\n\t,"):
            raise ValueError("Unexpected text before the first assignment in " + name)
        values = {}
        for index, key_match in enumerate(keys):
            key = re.sub(r"\s+", "", key_match.group(1)).lower()
            if key in values:
                raise ValueError("Duplicate assignment: " + key)
            stop = keys[index + 1].start() if index + 1 < len(keys) else len(body)
            raw = body[key_match.end():stop].strip().rstrip(",").strip()
            if not raw:
                raise ValueError("Missing value for " + key)
            values[key] = raw
        if name in groups:
            raise ValueError("Duplicate namelist: " + name)
        groups[name] = values
        end = finish + len(closure.group())
    return groups


def get_value(group, key, default=None):
    return value_of(group[key]) if key in group else default


def keywords_ok(program, groups):
    definitions = registry()["namelists"][program]
    errors = []
    for name, values in groups.items():
        if name not in definitions:
            errors.append(f"Unsupported namelist &{name} in this cached {program} profile")
            continue
        for key in values:
            if base_key(key) not in definitions[name]:
                errors.append(f"Unknown {program} key for cached release: {key}")
    return errors
