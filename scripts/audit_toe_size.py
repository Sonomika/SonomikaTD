"""Estimate the largest contributors to the currently open TouchDesigner project."""
import os


OUT_DIR = os.path.join(project.folder, 'output', 'toe_size_audit').replace('\\', '/')
REPORT = os.path.join(project.folder, 'output', 'toe_size_audit.txt').replace('\\', '/')
os.makedirs(OUT_DIR, exist_ok=True)


def _all_ops():
    nodes = [op('/')]
    try:
        nodes.extend(op('/').findChildren(maxDepth=99))
    except Exception:
        pass
    return nodes


def _fmt(size):
    size = float(size)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024.0 or unit == 'GB':
            return '{:.2f} {}'.format(size, unit)
        size /= 1024.0


def _vfs_files():
    rows = []
    for node in _all_ops():
        try:
            for item in node.vfs.find(pattern='*'):
                rows.append((int(item.size), item.virtualPath))
        except Exception:
            pass
    return sorted(set(rows), reverse=True)


def _locked_ops():
    rows = []
    for node in _all_ops():
        try:
            if not bool(node.lock):
                continue
        except Exception:
            continue
        estimate = 0
        detail = node.OPType
        try:
            width, height = int(node.width), int(node.height)
            estimate = width * height * 4
            detail += ' {}x{}'.format(width, height)
        except Exception:
            try:
                estimate = len(node.text.encode('utf-8'))
            except Exception:
                pass
        rows.append((estimate, node.path, detail))
    return sorted(rows, reverse=True)


def _large_dats():
    rows = []
    for node in _all_ops():
        if getattr(node, 'family', '') != 'DAT':
            continue
        try:
            size = len(node.text.encode('utf-8'))
        except Exception:
            continue
        if size >= 4096:
            rows.append((size, node.path, node.OPType))
    return sorted(rows, reverse=True)


def _component_exports():
    rows = []
    root = op('/')
    candidates = []
    try:
        candidates.extend(root.children)
    except Exception:
        pass
    project1 = op('/project1')
    if project1 is not None:
        try:
            candidates.extend(project1.children)
        except Exception:
            pass
    seen = set()
    for node in candidates:
        if node.path in seen or getattr(node, 'family', '') != 'COMP':
            continue
        seen.add(node.path)
        safe = node.path.strip('/').replace('/', '__') or 'root'
        path = os.path.join(OUT_DIR, safe + '.tox').replace('\\', '/')
        try:
            node.save(path)
            rows.append((os.path.getsize(path), node.path, path))
        except Exception as exc:
            rows.append((-1, node.path, 'ERROR ' + str(exc)))
    return sorted(rows, reverse=True)


def apply():
    vfs = _vfs_files()
    locked = _locked_ops()
    dats = _large_dats()
    comps = _component_exports()
    with open(REPORT, 'w', encoding='utf-8') as out:
        out.write('TOE: {} ({})\n\n'.format(project.file, _fmt(os.path.getsize(project.file))))
        out.write('APPROXIMATE EXPORTED COMPONENT SIZES\n')
        out.write('(Standalone .tox sizes overlap; use for ranking, not addition.)\n')
        for size, path, saved in comps:
            out.write('{:>12}  {}\n'.format(_fmt(size) if size >= 0 else 'ERROR', path))
        out.write('\nEMBEDDED VFS FILES\n')
        for size, path in vfs:
            out.write('{:>12}  {}\n'.format(_fmt(size), path))
        out.write('\nLOCKED OPERATORS (uncompressed estimate where available)\n')
        for size, path, detail in locked:
            out.write('{:>12}  {}  {}\n'.format(_fmt(size), path, detail))
        out.write('\nLARGE DAT TEXT\n')
        for size, path, detail in dats:
            out.write('{:>12}  {}  {}\n'.format(_fmt(size), path, detail))
    print('TOE size audit ->', REPORT)
    return REPORT


apply()
