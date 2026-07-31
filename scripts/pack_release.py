"""Build release/SonomikaTD_X.YY.zip from production/.

Run with system Python from the repo root:
    python scripts/pack_release.py
    python scripts/pack_release.py --version 1.07
"""
from __future__ import annotations

import argparse
import os
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / 'production'
RELEASE = ROOT / 'release'

ASSET_SKIP_NAMES = {
    'sonomika_logo_backup_pre_hires.png',
    '_tmp_logo_render.png',
}


def _detect_next_version() -> str:
    versions = []
    for path in RELEASE.glob('SonomikaTD_*.zip'):
        name = path.stem  # SonomikaTD_1.06
        parts = name.split('_')
        if len(parts) >= 2:
            versions.append(parts[-1])
    if not versions:
        return '1.01'

    def key(v: str):
        try:
            return tuple(int(p) for p in v.split('.'))
        except Exception:
            return (0,)

    latest = max(versions, key=key)
    nums = [int(p) for p in latest.split('.')]
    nums[-1] += 1
    return '.'.join(str(n) for n in nums)


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _sync_tree(src: Path, dst: Path, *, skip_names: set[str] | None = None) -> int:
    skip_names = skip_names or set()
    count = 0
    if dst.exists():
        shutil.rmtree(dst)
    for path in src.rglob('*'):
        if path.is_dir():
            continue
        if path.name in skip_names or path.name.startswith('.'):
            continue
        rel = path.relative_to(src)
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
        count += 1
    return count


def sync_release_folder(include_assets: bool = False) -> dict:
    stats = {}
    toe_src = PRODUCTION / 'SonomikaTD.toe'
    if not toe_src.is_file():
        raise FileNotFoundError(toe_src)
    _copy_file(toe_src, RELEASE / 'SonomikaTD.toe')
    stats['toe'] = toe_src.stat().st_size

    manual_src = PRODUCTION / 'manual.pdf'
    if manual_src.is_file():
        _copy_file(manual_src, RELEASE / 'Sonomika_Manual.pdf')
        stats['manual'] = manual_src.stat().st_size

    tox_count = _sync_tree(PRODUCTION / 'tox' / 'factory', RELEASE / 'tox' / 'factory')
    stats['tox'] = tox_count

    if (PRODUCTION / 'templates').is_dir():
        stats['templates'] = _sync_tree(PRODUCTION / 'templates', RELEASE / 'templates')

    if (PRODUCTION / 'licenses').is_dir():
        stats['licenses'] = _sync_tree(PRODUCTION / 'licenses', RELEASE / 'licenses')

    # UI media is embedded in the .toe VFS for portable releases.
    assets_dst = RELEASE / 'assets'
    if include_assets and (PRODUCTION / 'assets').is_dir():
        stats['assets'] = _sync_tree(
            PRODUCTION / 'assets',
            assets_dst,
            skip_names=ASSET_SKIP_NAMES,
        )
    else:
        if assets_dst.exists():
            shutil.rmtree(assets_dst)
        stats['assets'] = 0

    sets_readme = RELEASE / 'sets' / 'README.txt'
    sets_readme.parent.mkdir(parents=True, exist_ok=True)
    if not sets_readme.is_file():
        sets_readme.write_text(
            'SAVE YOUR PERFORMANCE SETS HERE\n\n'
            'Use SonomikaTD Settings > Sets to save and open performance sets.\n',
            encoding='utf-8',
        )
    return stats


def build_zip(version: str, include_assets: bool = False) -> Path:
    zip_path = RELEASE / f'SonomikaTD_{version}.zip'
    if zip_path.exists():
        zip_path.unlink()

    include_roots = [
        RELEASE / 'SonomikaTD.toe',
        RELEASE / 'Sonomika_Manual.pdf',
        RELEASE / 'licenses',
        RELEASE / 'sets',
        RELEASE / 'templates',
        RELEASE / 'tox',
    ]
    if include_assets:
        include_roots.append(RELEASE / 'assets')

    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for item in include_roots:
            if not item.exists():
                continue
            if item.is_file():
                archive.write(item, arcname=item.name)
                continue
            for path in item.rglob('*'):
                if path.is_dir():
                    continue
                if path.name.startswith('.'):
                    continue
                archive.write(path, arcname=str(path.relative_to(RELEASE)).replace('\\', '/'))
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description='Pack SonomikaTD release zip')
    parser.add_argument('--version', default=None, help='Version like 1.07 (default: next)')
    parser.add_argument(
        '--include-assets',
        action='store_true',
        help='Also ship disk assets/ (normally embedded in the .toe VFS)',
    )
    args = parser.parse_args()
    version = args.version or _detect_next_version()

    print('Syncing release/ from production/ ...')
    stats = sync_release_folder(include_assets=bool(args.include_assets))
    for key, value in stats.items():
        print(f'  {key}: {value}')

    print(f'Building SonomikaTD_{version}.zip ...')
    zip_path = build_zip(version, include_assets=bool(args.include_assets))
    print(f'Created {zip_path} ({zip_path.stat().st_size} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
