# SonomikaTD

Performance launcher for TouchDesigner: layer/column grid, canvas presets, column crossfade, and effect TOX slots.

For performance and day-to-day use, see [manual.md](manual.md). For making TOX effects that work well in Sonomika, see **Making Effects** in [manual.md](manual.md). MIDI mapping reference: [templates/midi/README.md](templates/midi/README.md).

---

## Project layout

```
SonomikaTD/
  run_in_td.py              # TouchDesigner bootstrap (Textport entry)
  scripts/
    build_simple_grid.py    # Thin entry (imports performance_grid/)
    performance_grid/       # Modular builder + runtime logic
      embedded/             # TD DAT scripts (panel, drag-drop, …)
      logic/                # Runtime (assembled into logic DAT)
      builder/              # Network build / patch / reload
    patch_*.py              # Effect TOX helpers
  templates/midi/           # MIDI mapping templates
  tox/                      # Effect + performance TOX assets
  mcp/                      # TouchDesigner MCP server (optional, for Cursor)
```

| Path | Role |
|------|------|
| `scripts/build_simple_grid.py` | Main builder entry |
| `scripts/performance_grid/logic/` | Runtime logic (assembled into `logic` DAT) |
| `scripts/performance_grid/embedded/` | TouchDesigner DAT scripts |
| `scripts/performance_grid/builder/` | Network build, patch, reload API |
| `templates/midi/` | MIDI mapping templates |
| `tox/` | Effect + performance TOX assets |

Edit workflow detail: [scripts/performance_grid/README.md](scripts/performance_grid/README.md).

---

## Quick start (TouchDesigner)

1. Open your `.toe` project.
2. One-time build from the Textport (Alt+T, `>>>` prompt — not system Python):

```python
exec(open(r'C:/path/to/SonomikaTD/run_in_td.py').read())
build_simple_grid(open_perform=True)
```

After the project is built once, **`auto_repair`** reloads `build_simple_grid.py` from disk when TouchDesigner starts (or when the perform network starts).

---

## Moving the project folder

Edit `SONOMIKA_ROOT` at the top of `run_in_td.py`, or set the environment variable before loading:

```python
import os
os.environ['SONOMIKA_TD_ROOT'] = r'D:/your/path/SonomikaTD'
exec(open(r'D:/your/path/SonomikaTD/run_in_td.py').read())
```

---

## Reloading scripts

After editing `.py` files under `scripts/performance_grid/`:

1. **`/settings`** → **About** → pulse **Reload Scripts (Dev)** in Perform mode, or
2. TouchDesigner Textport:

```python
reload_performance_scripts()
# or
op('/project1/performance_mode/logic').module.reload_scripts()
```

Reload updates the cell menu (copy, cut, paste, delete), logic, drag-drop handlers, and settings tabs without resetting the loaded grid when possible.

For MIDI template changes: reload scripts if needed, then use **Refresh Templates** on the **Midi** tab (or change **Template** to re-apply).

Alternative entry (see [scripts/performance_grid/README.md](scripts/performance_grid/README.md)):

```python
exec(open(r'C:/path/to/SonomikaTD/scripts/reload_performance.py', encoding='utf-8').read())
```

---

## Runtime maintenance

The `auto_repair` execute DAT keeps playback healthy during a show (column crossfade timing, performance readouts, periodic column heal). It does **not** reload Python source from disk — use **Reload Scripts (Dev)** or the Textport commands above when you change scripts.

If drag-drop or UI wiring breaks after an upgrade, run once from the Textport:

```python
repair_performance_drops()
```

---

## Settings (`/settings` COMP)

Brief overview — full detail in [manual.md](manual.md):

- **Canvas** — width/height, presets, Apply
- **Columns / Fade** — crossfade on/off, duration
- **Midi** — device, template, takeover mode, debug readouts
- **Performance** — render scale, thumbnails

---

## MCP (Cursor IDE)

Optional: import `mcp/touchdesigner-mcp-td/mcp_webserver_base.tox` into `/project1`, then use Cursor's TouchDesigner MCP tools. The `.mcpb` bundle is in `mcp/`.
