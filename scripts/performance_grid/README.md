# performance_grid

Modular Python for a performance grid. TouchDesigner still receives **assembled text** for `logic`, `panel_exec`, and drag-drop DATs — edit the `.py` files here, then reload.

## Layout

| Path | Role |
|------|------|
| `embedded/` | Scripts pasted into panelexecute / text / execute DATs |
| `logic/` | Runtime module (concatenated into `logic` DAT) |
| `builder/` | Network build, patch, reload API |
| `constants_builder.py` | Grid UI / builder constants |
| `paths.py` | `SONOMIKA_TD_ROOT`, reload path discovery |
| `assemble.py` | Builds `LOGIC`, `PANEL_EXEC`, … strings |
| `entry.py` | Single import surface for `build_simple_grid.py` |

## Edit workflow

1. Change files under `logic/` or `embedded/` (not the 6k-line monolith).
2. In TouchDesigner: **Maintenance → Reload Scripts** on `/settings`, or Textport (once after upgrading reload, then pulse works):

```python
exec(open(r'.../SonomikaTD/scripts/reload_performance.py', encoding='utf-8').read())
```

Use the **TouchDesigner** Textport (Alt+T), not system Python (`python >>>`). Reload re-assembles `logic` from disk. Look for `reload_now OK` in the Textport.

## Re-split from monolith (optional)

If `scripts/build_simple_grid.py` was edited as one file:

```bash
python SonomikaTD/scripts/performance_grid/extract_monolith.py
```

Then fix any bad split boundaries (see `builder/helpers_ui.py` / `helpers_settings.py`).

## Entry points

- `SonomikaTD/scripts/build_simple_grid.py` — canonical
- `scripts/build_simple_grid.py` — shim that imports this package

## MIDI

JSON templates and a full mapping reference (notes, CC, targets, controller layouts, troubleshooting) are in **[`SonomikaTD/templates/midi/README.md`](../../templates/midi/README.md)**.

Quick path: **Dialogs → MIDI Device Mapper** → `/settings` **Midi** tab → pick **MIDI Device** + **MIDI Template** → **Load Template**. Built-in templates: `pad_grid_8x4`, `columns_scenes` for Ableton Move (Schwung MIDI controller). Implementation: `logic/17_osc_mapping.py`.

**Grid cells:** right-click a loaded cell → **Reload** (re-read TOX/video from disk), copy/cut/paste/delete. Parameters appear in the bottom **Selected Cell** panel when the cell is selected.
