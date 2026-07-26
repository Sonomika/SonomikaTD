# Run once in TouchDesigner Textport (>>> prompt, NOT python >>>):
#
# exec(open(r'C:\Users\ridle\OneDrive\Documents Backup\1_Cursor\TouchDesigner\SonomikaTD\scripts\fix_settings_root.py', encoding='utf-8').read())

import os
import sys

ROOT = r'C:\Users\ridle\OneDrive\Documents Backup\1_Cursor\TouchDesigner\SonomikaTD'
SCRIPTS = op('/').fetch('sonomika_scripts_dir', '') or os.path.join(ROOT, 'scripts')
SCRIPTS = os.path.normpath(str(SCRIPTS))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

for key in list(sys.modules.keys()):
    if key == 'performance_grid' or key.startswith('performance_grid.'):
        del sys.modules[key]


def _find_settings():
    for path in ('/settings', '/project1/settings'):
        try:
            s = op(path)
            if s is not None:
                return s
        except Exception:
            pass
    try:
        legacy = op('/sonomika_infra/settings')
        if legacy is not None:
            return legacy
    except Exception:
        pass
    try:
        for ch in op('/').findChildren(depth=4):
            if ch.name == 'settings' and ch.isCOMP:
                return ch
    except Exception:
        pass
    return None


def _move_to_root(node):
    root = op('/')
    if node is None or root is None:
        return None
    try:
        if node.parent() == root:
            return node
        copied = root.copy(node, name=node.name, includeDocked=True)
        try:
            node.destroy()
        except Exception:
            pass
        return copied or root.op(node.name)
    except Exception as exc:
        print('move failed:', node.path, exc)
        return node


print('--- fix_settings_root ---')
s = _find_settings()
print('found settings:', s.path if s else 'NOT FOUND')

if s is None:
    print('ERROR: no settings COMP in project.')
    print('Try: Maintenance -> Reload Scripts, or rebuild from build_simple_grid.py')
else:
    s = _move_to_root(s)
    print('settings now at:', s.path if s else 'move failed')

    pick = op('/program_pick') or op('/sonomika_infra/program_pick')
    if pick is not None:
        _move_to_root(pick)
        print('program_pick at:', op('/program_pick').path if op('/program_pick') else pick.path)

    infra = op('/sonomika_infra')
    if infra is not None and len(infra.children) == 0:
        try:
            infra.destroy()
            print('removed empty sonomika_infra')
        except Exception:
            pass

    try:
        from performance_grid.td_runtime import patch_dat_scripts_from_disk, remember_scripts_dir
        remember_scripts_dir(SCRIPTS, td_op=op)
        patch_dat_scripts_from_disk(td_op=op)
        print('patched DAT scripts from disk')
    except Exception as exc:
        print('patch skipped:', exc)

    s = op('/settings') or _find_settings()
    pm = op('/project1/performance_mode')
    ui = pm.op('ui') if pm else None
    panel = ui.op('settings_params') if ui else None
    if s is not None and panel is not None:
        panel.par.op = ''
        panel.par.op = s.path
        panel.par.enable = True
        panel.par.custom = True
        panel.par.display = True
        print('settings_params ->', panel.par.op.eval())
    else:
        print('WARN: panel=', panel, 'settings=', s)

    try:
        mod = pm.op('logic').module
        if hasattr(mod, 'restore_root_settings_layout'):
            mod.restore_root_settings_layout(reposition=False)
        if hasattr(mod, '_heal_legacy_infra_path_refs'):
            print('healed expr refs:', mod._heal_legacy_infra_path_refs())
        if hasattr(mod, 'heal_perf_tab'):
            mod.heal_perf_tab()
        if hasattr(mod, '_refresh_settings_params_panel'):
            mod._refresh_settings_params_panel()
        print('logic heal OK')
    except Exception as exc:
        print('logic heal:', exc)

print('--- done ---')
