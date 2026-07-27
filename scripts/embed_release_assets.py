"""Embed assets/ into SonomikaTD.toe and audit unresolved file parameters.

Run inside TouchDesigner:
    exec(open(project.folder + '/scripts/embed_release_assets.py', encoding='utf-8').read())
"""
import os


ROOT_DIR = os.path.normpath(project.folder).replace('\\', '/')
ASSETS_DIR = os.path.join(ROOT_DIR, 'assets').replace('\\', '/')
REPORT_PATH = os.path.join(ROOT_DIR, 'output', 'release_asset_audit.txt').replace('\\', '/')
VFS_OWNER = op('/project1')


def _all_ops():
    nodes = [op('/')]
    try:
        nodes.extend(op('/').findChildren(maxDepth=99))
    except Exception:
        pass
    return nodes


def _embed_assets():
    if VFS_OWNER is None:
        raise RuntimeError('Missing /project1 VFS owner')
    embedded = {}
    for name in sorted(os.listdir(ASSETS_DIR)):
        disk_path = os.path.join(ASSETS_DIR, name).replace('\\', '/')
        if not os.path.isfile(disk_path):
            continue
        key = 'assets/' + name
        try:
            old = VFS_OWNER.vfs.find(pattern=key)
            for item in old:
                item.destroy()
        except Exception:
            pass
        item = VFS_OWNER.vfs.addFile(disk_path, overrideName=key)
        embedded[name.lower()] = item.virtualPath
    return embedded


def _rewrite_asset_parameters(embedded):
    changed = []
    for node in _all_ops():
        for par in getattr(node, 'pars', lambda: [])():
            try:
                value = str(par.eval()).strip().strip('"').replace('\\', '/')
            except Exception:
                continue
            if not value or value.startswith('vfs:'):
                continue
            base = os.path.basename(value).lower()
            if base not in embedded:
                continue
            try:
                par.val = embedded[base]
                changed.append('{}:{}'.format(node.path, par.name))
                if par.name.lower() == 'file':
                    pulse = getattr(node.par, 'reloadpulse', None)
                    if pulse is not None:
                        pulse.pulse()
            except Exception:
                pass
    return changed


def _looks_like_file_parameter(par, value):
    try:
        if bool(par.isFile):
            return True
    except Exception:
        pass
    name = str(getattr(par, 'name', '')).lower()
    if name in (
        'file', 'folder', 'externaltox', 'fontfile', 'filename',
        'path', 'sourcefile', 'moviefile', 'audiofile',
    ):
        return True
    ext = os.path.splitext(value.split('?', 1)[0])[1].lower()
    return ext in (
        '.tox', '.png', '.jpg', '.jpeg', '.svg', '.gif', '.bmp',
        '.mp4', '.mov', '.avi', '.webm', '.wav', '.mp3', '.aif',
        '.aiff', '.ttf', '.otf', '.json', '.csv', '.txt', '.glsl',
    )


def _audit_missing():
    missing = []
    for node in _all_ops():
        for par in getattr(node, 'pars', lambda: [])():
            try:
                value = str(par.eval()).strip().strip('"').replace('\\', '/')
            except Exception:
                continue
            if not value or value.startswith(('vfs:', 'http:', 'https:', 'op(')):
                continue
            if not _looks_like_file_parameter(par, value):
                continue
            full = value
            if not os.path.isabs(full):
                full = os.path.join(ROOT_DIR, full).replace('\\', '/')
            if not os.path.exists(full):
                missing.append('{}\t{}\t{}'.format(node.path, par.name, value))
    return sorted(set(missing))


def _internalize_broken_references():
    """Keep cooked/internal COMP contents but remove unusable reload sources."""
    cleaned = []
    for node in _all_ops():
        ext = getattr(getattr(node, 'par', None), 'externaltox', None)
        if ext is not None:
            try:
                value = str(ext.eval()).strip().strip('"').replace('\\', '/')
            except Exception:
                value = ''
            if value and not value.startswith('vfs:'):
                full = value if os.path.isabs(value) else os.path.join(ROOT_DIR, value)
                if not os.path.isfile(full):
                    try:
                        enable = getattr(node.par, 'enableexternaltox', None)
                        if enable is not None:
                            enable.val = False
                        ext.val = ''
                        cleaned.append('{}:externaltox={}'.format(node.path, value))
                    except Exception:
                        pass
        file_par = getattr(getattr(node, 'par', None), 'file', None)
        if file_par is not None:
            try:
                value = str(file_par.eval()).strip()
                if value.lower() in ('none', 'null'):
                    file_par.val = ''
                    cleaned.append('{}:file={}'.format(node.path, value))
            except Exception:
                pass
    return cleaned


def apply():
    # Pull the current modular source into the embedded logic DAT first.
    logic = op('/project1/performance_mode/logic')
    if logic is not None:
        try:
            logic.module.reload_scripts()
        except Exception as exc:
            print('Logic reload warning:', exc)

    embedded = _embed_assets()
    changed = _rewrite_asset_parameters(embedded)
    cleaned = _internalize_broken_references()
    missing = _audit_missing()

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, 'w', encoding='utf-8') as report:
        report.write('Embedded assets: {}\n'.format(len(embedded)))
        for name, path in sorted(embedded.items()):
            report.write('  {} -> {}\n'.format(name, path))
        report.write('\nRewritten parameters: {}\n'.format(len(changed)))
        for path in changed:
            report.write('  {}\n'.format(path))
        report.write('\nInternalized/cleared broken references: {}\n'.format(len(cleaned)))
        for path in cleaned:
            report.write('  {}\n'.format(path))
        report.write('\nUnresolved external references: {}\n'.format(len(missing)))
        for row in missing:
            report.write('  {}\n'.format(row))

    project.save()
    print('Embedded {} assets; rewrote {} parameters; cleaned {}; unresolved {}'.format(
        len(embedded), len(changed), len(cleaned), len(missing)
    ))
    print('Audit ->', REPORT_PATH)
    print('Saved ->', project.file)
    return {
        'embedded': len(embedded),
        'rewritten': len(changed),
        'cleaned': len(cleaned),
        'missing': len(missing),
        'report': REPORT_PATH,
    }


apply()
