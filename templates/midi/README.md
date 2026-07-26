# MIDI mapping guide

JSON templates in this folder define how **notes** and **control changes (CC)** from your controller map to the Sonomika performance grid. Load them from `/settings` → **Midi** → **Template** (the mapping applies as soon as you pick an entry).

After editing a template or Python mapping code, run **About → Reload Scripts (Dev)** on `/settings`. After adding or renaming `.json` files, use **Refresh Templates** on the Midi tab (or reload scripts) so the menu updates.

---

## Setup in TouchDesigner

1. **Dialogs → MIDI Device Mapper** — create a mapper for your controller. Note the **ID** (row index in `/local/midi/device`).
2. Open **`/settings`** → **Midi** tab.
3. **MIDI Device** — choose the same mapper ID.
4. **Takeover Mode** — `None` (immediate), `Pickup` (wait until knob crosses slider), or `Value Scaling` (smooth catch-up, default for new sets).
5. **Template** — pick a `.json` file from this folder. The mapping loads immediately when the selection changes.
6. Play a pad or turn a knob — **Received** and **Value** should update. If not, check the mapper ID and that the device is sending on the channel you mapped.

**Takeover Mode** (Settings → Midi) applies to all CC mappings (opacity, `map:`, `par:`). Use **Pickup** when switching cells/scenes so knobs do not jump sliders; use **None** for direct absolute control.

Templates are discovered from every matching folder under the project (e.g. `templates/midi/` and bundled copies). All `.json` files are merged by name; if the same name exists in more than one place, the newer file wins.

Add new `.json` files to a `templates/midi/` folder. They appear in the **Template** menu after **Refresh Templates** or a script reload. Menu labels come from the filename (without `.json`); underscores are shown as spaces. The optional `description` field in JSON is for humans only and is not shown in the menu.

---

## Template file format

Each file is one JSON object:

| Field | Required | Description |
|-------|----------|-------------|
| `description` | No | Notes for humans only |
| `mappings` | Yes* | List of note → target entries |
| `cc_mappings` | No | List of CC → target entries (recommended for knobs) |

\*At least one of `mappings` or `cc_mappings` must contain valid entries.

Each mapping entry is an object:

```json
{
  "note": "61",
  "cc": "2",
  "channel": "1",
  "target": "L4_col1",
  "min": 0,
  "max": 1
}
```

- Use **`note`** for pads/keys (note-on, velocity &gt; 0).
- Use **`cc`** (or `controller`) for knobs/faders.
- **`channel`** — optional; `1` = MIDI channel 1. Omit or use `*` for any channel.
- **`target`** — what to control (see tables below).
- **`min` / `max`** — optional; only used for **CC** targets that scale a numeric value (opacity, `par:…`, `map:`).

You can put CC entries in `mappings` instead of `cc_mappings`, but `cc_mappings` keeps pad and knob sections separate.

**Limits:** up to 32 note mappings and 16 CC mappings per template (first valid entries win).

---

## Grid row labels (L4, L3, …)

Rows are labeled **L4** (top) down to **L1** (bottom) for the default 4-layer grid. **L4** is not “layer index 4” in the engine — it is the **top visible row** label.

| Target pattern | Action |
|----------------|--------|
| `L4_col1` … `L4_col8` | Assign **layer L4** to column 1…8 (loads/triggers that cell on that layer) |
| `L3_col5` | Same for layer **L3**, column 5 |
| `L2_col1` | Layer **L2**, column 1 |
| `L1_col8` | Layer **L1**, column 8 |

Alternate separators work: `L4_col1`, `L4:col1`, `L4-col1`.

**Column only** (no layer in target):

| Target | Action |
|--------|--------|
| `col1` … `col16` | Select column **1…16** (all layers follow column focus rules in the composition) |

**Scenes:**

| Target | Action |
|--------|--------|
| `scene1` … `scene8` | Switch to scene 1…8 (`scene9` capped by project scene count) |

---

## Note matching (`note` field)

The incoming note number must match the template entry. All of these are equivalent for note 61 on channel 1:

| `note` value | Matches |
|--------------|---------|
| `"61"` | Note 61 |
| `"Note61"` / `"note61"` | Note 61 |
| `"1:61"` | Channel 1, note 61 |

Optional **`channel`** on the entry filters by MIDI channel (e.g. `"1"`). Channel 1 may also arrive as `0` in some TD paths.

Notes only fire on **note-on** with value &gt; 0 (velocity or equivalent).

---

## CC matching (`cc` field)

Use the **controller index** from TouchDesigner’s MIDI Device Mapper / MIDI console. This is often the **Index** column, not always the same as “CC number” printed on generic MIDI charts.

| `cc` value | Matches |
|------------|---------|
| `"2"` | Controller index 2 |
| `"CC2"` / `"cc2"` | Controller index 2 |
| `"1:2"` | Channel 1, index 2 |
| `"*:2"` | Index 2 on any channel |

Optional **`channel`** on the entry (e.g. `"1"`) restricts to that channel.

---

## CC targets (knobs / faders)

MIDI values **0–127** are normalized to 0–1, then scaled to **`min`**–**max`**. If `min`/`max` are omitted, parameter targets use the par’s **normMin** / **normMax**; otherwise **0**–**1**.

### Row opacity

| Target | Action |
|--------|--------|
| `L4_opacity` | Layer **L4** row opacity slider (0–1) |
| `L3_opacity` | Layer **L3** |
| `L2_opacity` | Layer **L2** |
| `L1_opacity` | Layer **L1** |

Variants like `L4:opacity` or `L4_opacity` both resolve the row from the `L4` token.

### Map Controller dials (`map:`)

Drives the **Map Controller** sliders (bottom of the Cell / Global params column). Bind targets on the dials first (drop a parameter onto a map slot).

| Target | Action |
|--------|--------|
| `map:1` … `map:8` | Dial **1…8** on whichever bank is active for the current tab and selection |
| `map:cell:1` … `map:cell:8` | Cell bank dial **1…8** (selected layer + column) |
| `map:global:1` … `map:global:8` | Global bank dial **1…8** |

Aliases: `map1`, `map_3`, `map_dial:5`, `map:layer:2` (same as `map:cell:2`).

Example (active bank):

```json
{
  "cc": "72",
  "channel": "1",
  "target": "map:1",
  "min": 0,
  "max": 1
}
```

Example (fixed Cell / Global banks):

```json
{
  "cc": "2",
  "channel": "1",
  "target": "map:cell:1",
  "min": 0,
  "max": 1
}
```

### Clip / TOX parameters (`par:` / `param:`)

Drives a parameter on the **video** or **tox** operator inside the cell slot. Use names from the grid **cell params** panel for that clip.

| Target | Cell used |
|--------|-----------|
| `par:Speed` | **Selected** layer + **selected** column |
| `par:L4:Speed` | Layer **L4**, **selected** column |
| `par:col3:Speed` | **Selected** layer, column **3** |
| `par:L4_col3:Speed` | Layer **L4**, column **3** |

Example:

```json
{
  "cc": "2",
  "channel": "1",
  "target": "par:Speed",
  "min": 0,
  "max": 2
}
```

Select the cell in the grid before turning the knob when using `par:…` without `L4_colN`.

### Settings parameters

| Target | Action |
|--------|--------|
| `settings:Mididevice` | Sets par **Mididevice** on `/settings` (name is case-insensitive) |

---

## Common layout patterns

Shipped templates are examples for typical pad grids (e.g. 4×8 controllers). Open any template’s JSON and read its `description` for note/CC numbers on that hardware. Patterns you will see:

### Layer × column pad grid

Four rows of eight pads: each pad assigns one **layer** at one **column**.

| Row | Typical note base (+1 per column) | Example targets |
|-----|-----------------------------------|-----------------|
| L4 | 61 | `L4_col1` … `L4_col8` |
| L3 | 53 | `L3_col1` … `L3_col8` |
| L2 | 45 | `L2_col1` … `L2_col8` |
| L1 | 37 | `L1_col1` … `L1_col8` |

Often paired with four knobs driving row opacity (`L4_opacity` … `L1_opacity`) on low CC indices (e.g. 2–5 on channel 1). Confirm indices in **Received** while turning each knob.

### Columns and scenes pad grid

Same physical pad layout, different targets:

| Row | Typical notes | Targets |
|-----|---------------|---------|
| L4 | 61–68 | `col1` … `col8` |
| L3 | 53–60 | `col9` … `col16` |
| L2 | — | (often unmapped) |
| L1 | 37–44 | `scene1` … `scene8` |

**Knobs — active bank:** eight controllers (often high CC indices such as 72–79 on channel 1) → `map:1` … `map:8`. Whichever Map Controller tab is open receives the MIDI.

**Knobs — split Cell / Global banks:** lower indices (e.g. 2–9) → `map:cell:1` … `map:cell:8`; another bank (e.g. 10–17 or 72–79 depending on your mapper) → `map:global:1` … `map:global:8`. Use this when you want cell and global dials wired independently regardless of the active tab.

Always verify CC indices in **Dialogs → MIDI Device Mapper** or the **Received** field; mapper layouts differ from printed MIDI charts.

---

## Create your own template

1. Copy an existing `.json` in this folder and rename it.
2. Open **Dialogs → MIDI Device Mapper** or the **MIDI** CHOP/DAT console and note **note numbers** and **CC indices** for each control.
3. Edit `mappings` / `cc_mappings` with those numbers and the **target** strings from the tables above.
4. **Refresh Templates** (or reload scripts) → select your template in the menu.
5. Test **Received** while pressing each control; adjust `note`/`cc`/`channel` until the grid behavior matches.

Minimal starter:

```json
{
  "description": "Pads trigger column 1 on L4; knob 7 drives selected clip Speed.",
  "mappings": [
    { "note": "36", "channel": "1", "target": "L4_col1" }
  ],
  "cc_mappings": [
    { "cc": "7", "channel": "1", "target": "par:Speed", "min": 0, "max": 2 }
  ]
}
```

---

## Troubleshooting

| Problem | Things to check |
|---------|------------------|
| Nothing in **Received** | Wrong **MIDI Device** ID; mapper not active; cable/driver |
| Received but no grid change | Wrong template selected; wrong `note`/`cc` number; `channel` mismatch |
| One knob moves several sliders | Duplicate CC targets in template; only one CC entry per controller index |
| `par:…` does nothing | No clip in that cell; par name typo; cell not selected when using `par:Name` only |
| Template missing from menu | File not under a `templates/midi/` folder; not `.json`; run **Refresh Templates** or reload scripts |
| Template not found on load | Menu entry must match the file stem (no `.json` in the menu) |

Mapping logic lives in `SonomikaTD/scripts/performance_grid/logic/17_osc_mapping.py` if you need behavior beyond what JSON targets support.
