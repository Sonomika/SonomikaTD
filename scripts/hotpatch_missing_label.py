"""Surgical hotpatch: keep missing clip paths + show red 'missing' labels.

Safer than full logic DAT rebuild. Run inside TouchDesigner via MCP/Textport:

    exec(open(project.folder + '/scripts/hotpatch_missing_label.py', encoding='utf-8').read())
"""
import os
import re


def _patch_logic_text(logic):
    text = logic.text
    # Remove experimental relocation helper if present.
    text2 = re.sub(
        r"\ndef _relocated_asset_candidates\(path\):.*?(?=\ndef _resolve_stored_asset_path\()",
        "\n",
        text,
        count=1,
        flags=re.S,
    )
    # Replace resolve that drops missing paths (returns '').
    pattern = re.compile(
        r"def _resolve_stored_asset_path\(path\):\n"
        r"    path = str\(path or ''\)\.strip\(\)\.replace\('\\\\', '/'\)\n"
        r"    if not path:\n"
        r"        return ''\n"
        r"    resolved = _norm_asset_path\(path\)\n"
        r"    return resolved if resolved and os\.path\.isfile\(resolved\) else ''\n"
    )
    replacement = (
        "def _resolve_stored_asset_path(path):\n"
        "    \"\"\"Resolve a set clip path. Keep the original when missing so UI can show 'missing'.\"\"\"\n"
        "    path = str(path or '').strip().replace('\\\\', '/')\n"
        "    if not path:\n"
        "        return ''\n"
        "    resolved = _norm_asset_path(path)\n"
        "    if resolved and os.path.isfile(resolved):\n"
        "        return resolved\n"
        "    # File gone — keep the stored path so the cell stays assigned and labels\n"
        "    # can show \"missing\" instead of silently dropping the clip on set open.\n"
        "    return path\n"
    )
    text3, n = pattern.subn(replacement, text2, count=1)
    # Clip display name: mark missing files.
    clip_pat = re.compile(
        r"def _clip_display_name\(clip_type, path\):\n"
        r"    \"\"\"Short name stored in clip_matrix label column\.\"\"\"\n"
        r"    name = _file_display_name\(path, clip_type\)\n"
        r"    return name\[:40\] if name else chr\(183\)\n"
    )
    clip_rep = (
        "def _clip_display_name(clip_type, path):\n"
        "    \"\"\"Short name stored in clip_matrix label column.\"\"\"\n"
        "    if path and _asset_file_missing(path, clip_type):\n"
        "        return 'missing'\n"
        "    name = _file_display_name(path, clip_type)\n"
        "    return name[:40] if name else chr(183)\n"
    )
    text4, n2 = clip_pat.subn(clip_rep, text3, count=1)
    # Import label branch: prefer missing over stale set labels.
    old_label = (
        "                label = str(row.get('label', '')).strip()\n"
        "                if _is_bad_display_name(label):\n"
        "                    label = _file_display_name(fpath, ctype)\n"
        "                if idx is not None and not _is_bad_display_name(label):\n"
        "                    tbl[idx, 'label'] = label\n"
    )
    new_label = (
        "                if idx is not None:\n"
        "                    if _asset_file_missing(fpath, ctype):\n"
        "                        tbl[idx, 'label'] = 'missing'\n"
        "                    else:\n"
        "                        label = str(row.get('label', '')).strip()\n"
        "                        if _is_bad_display_name(label):\n"
        "                            label = _file_display_name(fpath, ctype)\n"
        "                        if not _is_bad_display_name(label):\n"
        "                            tbl[idx, 'label'] = label\n"
    )
    n3 = 0
    if old_label in text4:
        text4 = text4.replace(old_label, new_label, 1)
        n3 = 1
    changed = (text4 != logic.text)
    if changed:
        logic.text = text4
    return {'resolve': n, 'clip': n2, 'label': n3, 'changed': changed}


def _hotpatch_module(mod):
    def _resolve_stored_asset_path(path):
        path = str(path or '').strip().replace('\\', '/')
        if not path:
            return ''
        resolved = mod._norm_asset_path(path)
        if resolved and os.path.isfile(resolved):
            return resolved
        return path

    def _clip_display_name(clip_type, path):
        if path and mod._asset_file_missing(path, clip_type):
            return 'missing'
        name = mod._file_display_name(path, clip_type)
        return name[:40] if name else chr(183)

    def _cell_display_name(layer, col):
        clip_type, path = mod._get(int(layer), int(col))
        if not path:
            return chr(183)
        if mod._asset_file_missing(path, clip_type):
            return 'missing'
        name = mod._matrix_cell_label(layer, col)
        if mod._is_bad_display_name(name):
            name = mod._file_display_name(path, clip_type)
        if mod._is_bad_display_name(name):
            name = mod._live_cell_display_name(layer, col, clip_type)
        if mod._is_bad_display_name(name):
            name = chr(183)
        return name[:40]

    original_wire_tox = getattr(
        mod, '_missing_safe_original_wire_tox', mod._wire_tox
    )

    def _wire_tox(slot, path, layer=None, col=None, force_reload=False):
        if mod._asset_file_missing(path, 'tox'):
            if layer is not None and col is not None:
                mod._reset_slot_media(int(layer), int(col))
            else:
                tox = slot.op('tox') if slot is not None else None
                if tox is not None:
                    try:
                        tox.par.externaltox = ''
                    except Exception:
                        pass
                    tox.allowCooking = False
            return False
        return original_wire_tox(
            slot, path, layer, col, force_reload=force_reload
        )

    mod._missing_safe_original_wire_tox = original_wire_tox
    mod._resolve_stored_asset_path = _resolve_stored_asset_path
    mod._clip_display_name = _clip_display_name
    mod._cell_display_name = _cell_display_name
    mod._wire_tox = _wire_tox


def apply():
    pm = op('/project1/performance_mode')
    logic = pm.op('logic')
    info = _patch_logic_text(logic)
    mod = logic.module
    _hotpatch_module(mod)
    print('patch_info', info)
    tbl = mod._table()
    missing = []
    if tbl is not None:
        for idx in range(1, tbl.numRows):
            try:
                clip_type = str(tbl[idx, 'type']).strip()
                path = str(tbl[idx, 'path']).strip()
                if path and mod._asset_file_missing(path, clip_type):
                    tbl[idx, 'label'] = 'missing'
                    if clip_type.lower() == 'tox':
                        try:
                            if int(tbl[idx, 'scene']) == mod._active_scene():
                                mod._reset_slot_media(
                                    int(tbl[idx, 'layer']),
                                    int(tbl[idx, 'col']),
                                )
                        except Exception:
                            pass
                    missing.append((
                        int(tbl[idx, 'scene']),
                        int(tbl[idx, 'layer']),
                        int(tbl[idx, 'col']),
                        path,
                    ))
            except Exception:
                pass
    try:
        mod._refresh_ui(full=True)
    except Exception:
        pass
    print('missing_cells', len(missing))
    for scene, layer, col, path in missing:
        print('  scene {} row {} col {} -> {}'.format(scene, layer, col, path))
    print('hotpatch_missing_label OK — save the .toe to keep DAT text')
    return True


apply()
