"""Restore Logo.tox, embed its image, and remove development-machine paths."""
import os

ROOT = r'C:/Users/ridle/OneDrive/Documents Backup/1_Cursor/TouchDesigner/SonomikaTD'
ORIGINAL = ROOT + '/tmp/logo_restore/logo_original.tox'
IMAGE = ROOT + '/assets/sonomika_logo.png'
TARGETS = [
    ROOT + '/tox/Factory/logo.tox',
    ROOT + '/release/tox/logo.tox',
]
REPORT = ROOT + '/output/logo_tox_portability.txt'
VFS_KEY = 'assets/sonomika_logo.png'


def _is_disk_absolute(value):
    value = str(value or '').strip().replace('\\', '/')
    return (
        len(value) > 2 and value[1] == ':' and value[2] == '/'
    ) or value.startswith('//')


def _repair(target, index):
    host = op('/project1')
    wrapper = host.create('baseCOMP', '__logo_restore_{}'.format(index))
    wrapper.loadTox(ORIGINAL)
    comps = [node for node in wrapper.children if getattr(node, 'isCOMP', False)]
    actual = comps[0] if len(comps) == 1 else wrapper

    original_image = ''
    try:
        original_image = str(actual.par.Imagefile.eval()).strip()
    except Exception:
        pass

    for item in actual.vfs.find(pattern=VFS_KEY):
        item.destroy()
    actual.vfs.addFile(IMAGE, overrideName=VFS_KEY)

    # Evaluate the VFS owner dynamically so the address remains correct when
    # the TOX is loaded into any grid slot or renamed.
    image_expr = "me.owner.vfs['{}'].virtualPath".format(VFS_KEY)
    try:
        actual.par.Imagefile.expr = image_expr
        actual.par.Imagefile.mode = ParMode.EXPRESS
    except Exception:
        pass

    logo_file = actual.op('logo_file')
    if logo_file is not None:
        try:
            logo_file.par.file.bindExpr = 'parent().par.Imagefile'
            logo_file.par.file.mode = ParMode.BIND
            logo_file.par.reloadpulse.pulse()
        except Exception:
            pass

    cleared = []
    for node in [actual] + list(actual.findChildren(maxDepth=99)):
        for par in node.pars():
            try:
                value = str(par.eval()).strip().strip('"').replace('\\', '/')
            except Exception:
                continue
            if not _is_disk_absolute(value):
                continue
            cleared.append('{}:{}={}'.format(node.path, par.name, value))
            try:
                par.val = ''
            except Exception:
                pass

    # Remove development-only input fixtures if present.
    removed_nodes = []
    for node in list(actual.findChildren(maxDepth=99)):
        if node.name.startswith('__test'):
            removed_nodes.append(node.path)
            node.destroy()

    actual.save(target)
    size = os.path.getsize(target)
    wrapper.destroy()
    return original_image, cleared, removed_nodes, size


rows = []
for i, target in enumerate(TARGETS):
    rows.append((target,) + _repair(target, i))

with open(REPORT, 'w', encoding='utf-8') as out:
    for target, original, cleared, removed_nodes, size in rows:
        out.write('{}\n'.format(target))
        out.write('  original Imagefile: {}\n'.format(original))
        out.write('  embedded key: {}\n'.format(VFS_KEY))
        out.write('  saved bytes: {}\n'.format(size))
        for item in cleared:
            out.write('  cleared disk path: {}\n'.format(item))
        for item in removed_nodes:
            out.write('  removed test node: {}\n'.format(item))

print('Portable Logo.tox saved. Report:', REPORT)
