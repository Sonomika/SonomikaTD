"""Remove obsolete diagnostic storage payloads and save the release .toe."""

pm = op('/project1/performance_mode')
removed = []
for key in ('old_live_probe', 'live_probe2', 'tmp_bind_test'):
    try:
        if key in pm.storage:
            pm.unstore(key)
            removed.append(key)
    except Exception:
        pass

logic = pm.op('logic')
try:
    logic.module.reload_scripts()
except Exception:
    pass

target = r'C:/Users/ridle/OneDrive/Documents Backup/1_Cursor/TouchDesigner/SonomikaTD/SonomikaTD.toe'
project.save(target)
print('Removed release debug storage:', removed)
print('Saved:', target)
