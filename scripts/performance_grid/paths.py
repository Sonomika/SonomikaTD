"""Package paths and script discovery for TouchDesigner reload."""
from __future__ import annotations

import os

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.normpath(os.path.join(_PKG_DIR, '..'))


def package_root() -> str:
    env = os.environ.get('SONOMIKA_TD_ROOT', '').strip()
    if env:
        return os.path.normpath(env)
    return os.path.normpath(os.path.join(_PKG_DIR, '..', '..'))


ROOT = package_root().replace('\\', '/')
TD_PROJECT_ROOT = os.path.normpath(
    os.path.join(_PKG_DIR, '..', '..', '..')
).replace('\\', '/')


def sonomika_sets_dir(project_folder=None):
    """Performance-set JSON folder: {project.folder}/sets, else package sets/."""
    pf = project_folder
    if pf is None:
        try:
            pf = project.folder
        except Exception:
            pf = ''
    if pf:
        folder = os.path.join(str(pf), 'sets')
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception:
            pass
        return os.path.normpath(folder).replace('\\', '/')
    folder = os.path.join(package_root(), 'sets')
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        pass
    return folder.replace('\\', '/')


def script_entry_paths(project_folder: str | None = None) -> list[str]:
    """Ordered paths to SonomikaTD/scripts/build_simple_grid.py for exec reload."""
    paths: list[str] = []
    env = os.environ.get('SONOMIKA_TD_ROOT', '').strip()
    if env:
        paths.append(os.path.join(env, 'scripts', 'build_simple_grid.py'))
    if project_folder:
        pf = project_folder.replace('\\', '/')
        paths.append(os.path.join(pf, 'SonomikaTD', 'scripts', 'build_simple_grid.py'))
        paths.append(os.path.join(pf, 'scripts', 'build_simple_grid.py'))
    paths.append(os.path.join(SCRIPTS_DIR, 'build_simple_grid.py'))
    # Workspace fallback when TD project.folder differs from repo (common during dev).
    _workspace = os.path.normpath(
        os.path.join(_PKG_DIR, '..', '..', '..', 'SonomikaTD', 'scripts', 'build_simple_grid.py')
    )
    paths.append(_workspace)
    if TD_PROJECT_ROOT:
        paths.append(os.path.join(TD_PROJECT_ROOT, 'SonomikaTD', 'scripts', 'build_simple_grid.py'))
        paths.append(os.path.join(TD_PROJECT_ROOT, 'scripts', 'build_simple_grid.py'))
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        p = os.path.normpath(p).replace('\\', '/')
        if p in seen or not os.path.isfile(p):
            continue
        seen.add(p)
        try:
            with open(p, encoding='utf-8') as fh:
                compile(fh.read(), p, 'exec')
        except SyntaxError as exc:
            print('Skipping invalid builder script:', p, exc)
            continue
        out.append(p)
    return out
