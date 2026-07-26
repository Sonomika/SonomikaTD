# Run inside TouchDesigner (MCP execute_python_script or Textport).
# Exports every effect in /project1/effect_library to portable .tox files.
#
# Example:
#   export_effect_tox()
#   export_effect_tox(r'D:/MyToxLibrary/effects')

import os

SUPPORT_NODES = {'effect_catalog', 'library_parexec', 'readme'}
DEFAULT_OUT = r'C:/Users/ridle/OneDrive/Documents Backup/1_Cursor/TouchDesigner/tox/effects'


def _library():
    return op('/project1/effect_library')


def _catalog_rows(lib):
    tbl = lib.op('effect_catalog')
    if tbl is None or tbl.numRows < 2:
        return []
    rows = []
    for r in range(1, tbl.numRows):
        rows.append({
            'name': str(tbl[r, 'name'].val),
            'label': str(tbl[r, 'label'].val),
            'category': str(tbl[r, 'category'].val),
        })
    return rows


def export_effect_tox(out_dir=None, portable=True):
    lib = _library()
    if lib is None:
        raise RuntimeError('Missing /project1/effect_library — run build_effect_library.py first')

    if portable:
        try:
            make_effects_canvas_portable()
        except NameError:
            pass
        except Exception as exc:
            print('Warning: portable canvas bind failed:', exc)

    out_dir = out_dir or DEFAULT_OUT
    out_dir = os.path.normpath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    meta = _catalog_rows(lib)
    meta_by_name = {m['name']: m for m in meta}

    exported = []
    failed = []

    for comp in sorted(lib.children, key=lambda c: c.name):
        if not comp.isCOMP or comp.name in SUPPORT_NODES:
            continue
        tox_path = os.path.join(out_dir, comp.name + '.tox')
        try:
            comp.save(tox_path)
            info = meta_by_name.get(comp.name, {})
            exported.append({
                'name': comp.name,
                'label': info.get('label', comp.name),
                'category': info.get('category', 'Other'),
                'tox': tox_path,
                'bytes': os.path.getsize(tox_path),
            })
        except Exception as exc:
            failed.append((comp.name, str(exc)))

    manifest = lib.op('effect_catalog')
    if manifest is not None:
        manifest_path = os.path.join(out_dir, 'effect_manifest.tsv')
        lines = ['name\tlabel\tcategory\ttox_file']
        for item in exported:
            lines.append('{name}\t{label}\t{category}\t{name}.tox'.format(**item))
        with open(manifest_path, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines) + '\n')

    print('Exported {} effects to {}'.format(len(exported), out_dir))
    for item in exported:
        print('  {} ({})'.format(item['name'], item['category']))
    if failed:
        print('Failed:')
        for name, err in failed:
            print('  {}: {}'.format(name, err))

    return exported


def main(out_dir=None):
    return export_effect_tox(out_dir)


if __name__ == '__main__':
    main()
