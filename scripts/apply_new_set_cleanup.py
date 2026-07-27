"""Reload the New Set fix and purge stale TOX contents from empty grid slots."""

logic = op('/project1/performance_mode/logic')
mod = logic.module
mod.reload_scripts()
mod = logic.module

cleaned = []
for layer in range(1, mod.MAX_LAYERS + 1):
    for col in range(1, mod._num_cols() + 1):
        clip_type, path = mod._get(layer, col)
        if str(path or '').strip():
            continue
        slot = mod._slot(layer, col)
        # Always clear locks/cached frames in empty slots, even when their TOX
        # shell is already empty.
        mod._reset_slot_media(layer, col, hard=False)
        tox = slot.op('tox') if slot is not None else None
        if tox is None:
            continue
        has_stale_contents = False
        try:
            children = [child.name for child in tox.children]
            has_stale_contents = any(name not in ('black', 'out1') for name in children)
        except Exception:
            pass
        try:
            has_stale_contents = has_stale_contents or bool(
                str(tox.par.externaltox.eval()).strip()
            )
        except Exception:
            pass
        if has_stale_contents:
            mod._reset_slot_media(layer, col, hard=True)
            cleaned.append((layer, col))

mod._refresh_ui(full=True)
project.save(
    r'C:/Users/ridle/OneDrive/Documents Backup/1_Cursor/TouchDesigner/SonomikaTD/SonomikaTD.toe'
)
print('Purged stale TOX networks from empty slots:', cleaned)
