"""Basic checks for a colocated EPW 5.8.1 restart bundle and run completion."""
import argparse
import json
from pathlib import Path
import re


def checkpoint(directory, prefix):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', prefix) or prefix in ('.', '..'):
        raise ValueError('prefix must be a simple filename stem')
    names = ['epwdata.fmt', 'vmedata.fmt', 'crystal.fmt', prefix + '.epmatwp', prefix + '.ukk']
    files = []
    errors = []
    for name in names:
        path = directory / name
        size = path.stat().st_size if path.is_file() else 0
        files.append({'name': name, 'bytes': size, 'present_nonempty': size > 0})
        if size <= 0:
            errors.append('Missing or empty checkpoint file: ' + name)
    return {'passed': not errors, 'errors': errors, 'files': files,
        'profile': 'EPW 5.8.1 basic colocated Wannier restart bundle',
        'checkpoint_compatibility_verified': False, 'physics_convergence_verified': False,
        'notes': ['Use this directory as the restart working directory with outdir=./; other layouts and modes need separate review.',
                  'Existence checks do not verify binary format, source version, grids, band manifold or additional dependencies.']}


def output(program, text, exit_code):
    errors = []
    if exit_code != 0:
        errors.append('Calculation process exited with code ' + str(exit_code))
    for pattern, message in [
        (r'Error in routine|MPI_Abort|segmentation fault', 'Runtime error reported in log'),
        (r'convergence NOT achieved|Maximum CPU time exceeded', 'Phase stopped before the requested calculation completed'),
    ]:
        if re.search(pattern, text, re.I):
            errors.append(message)
    if program == 'epw':
        version = re.search(r'Program EPW v\.([\d.]+)', text)
        if not version or version[1] != '5.8.1':
            errors.append('This completion check is verified for EPW 5.8.1; review the actual version')
        markers = ['Total program execution', 'functionality-dependent EPW.bib file.']
    else:
        markers = ['JOB DONE']
    for marker in markers:
        if marker not in text:
            errors.append('Missing completion marker: ' + marker)
    return {'passed': not errors, 'program': program, 'exit_code': exit_code,
        'errors': errors, 'physics_convergence_verified': False,
        'notes': ['Use the exit code and separate log from the same process invocation; completion is not physical convergence.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    cp = modes.add_parser('checkpoint', help='Check the verified basic colocated restart bundle')
    cp.add_argument('--directory', type=Path, required=True)
    cp.add_argument('--prefix', required=True)
    log = modes.add_parser('output', help='Check a process return code and its log')
    log.add_argument('--program', choices=['pw', 'ph', 'epw'], required=True)
    log.add_argument('--log', type=Path, required=True)
    log.add_argument('--exit-code', type=int, required=True)
    args = parser.parse_args()
    try:
        report = checkpoint(args.directory, args.prefix) if args.mode == 'checkpoint' else output(args.program, args.log.read_text(encoding='utf-8'), args.exit_code)
    except (OSError, ValueError) as exc:
        report = {'passed': False, 'errors': [str(exc)], 'physics_convergence_verified': False}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['passed'] else 2)


if __name__ == '__main__':
    main()
