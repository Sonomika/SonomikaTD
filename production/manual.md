# Sonomika Manual

Sonomika is a TouchDesigner performance VJ tool that makes running many TOX files easy.

## Getting Started

Open the Sonomika `.toe` file in TouchDesigner and switch to **Perform Mode** (select the `perform` operator and press **F1**). Day-to-day use does not require opening the network editor — everything lives in the Perform window.

If you do open the network: **perform** is the UI, **project1** holds the grid engine, **settings** (at project root `/settings`) is the parameter COMP behind the Settings panel, and **out1** / **SonomikaTD** are video outputs.

## What You See

- **Cells** are the slots where you load videos or TOX effects.
- **Rows** are visual layers. The bottom row is the base video row. Rows above it are usually FX rows.
- **Columns** are performance positions. Selecting a column changes what is active across the grid.
- **Selected Cell** shows controls for the currently selected video or TOX, plus **Cell** and **Global** tabs for stacking extra effects.
- **Scene bar** — numbered scene buttons above the grid; each scene has its own grid layout and global FX stack.
- **Settings** contains canvas, sets, OSC, grid OSC, pulse, audio, MIDI, fade, performance, and about controls.
- **Performance bar** shows GPU memory, frame time, and FPS.

## Loading Videos And TOX Effects

Drag a video file or `.tox` file onto a cell.

Videos usually go on the bottom base row. TOX effects usually go on rows above the base row so they can process what is below them. Some TOX files generate their own visuals, so they may still work without an input.

Right-click a loaded cell to open the cell menu:

- **Reload** — re-read the same file from disk (keeps session parameters when possible).
- **Relink** — pick a new path if the file moved or was renamed; Sonomika updates the cell and restores last-known parameters / map binds when it can.
- **Edit TOX** — open the `.tox` in a separate TouchDesigner process (TOX cells only).
- **Render Scale** / **Freeze** — performance controls for that cell.
- **Copy** / **Cut** / **Paste** / **Delete** — clipboard and clear.

If a cell still points at a file that is no longer on disk, the name strip under the thumbnail shows the missing file's name in red with a red **!** badge. Use **Relink** to point it at the new location, or re-open a performance set that still has saved parameter state for that cell.

## Rows And Columns

### Rows

Right-click a **row label** (L1, L2, …) on the left side of the grid.

- **Add Row Above** — inserts a new empty FX row above that row.
- **Delete Row** — removes the row and shifts rows below it up.

The bottom row (L1) is the base video row and **cannot be deleted**. You can have between 4 and 9 rows total.

### Columns

Right-click a **column header** at the top of the grid.

- **Insert Column** — adds a new empty column before the one you clicked, shifting existing columns to the right.
- **Copy Column** / **Paste Column** — duplicate a column's loaded cells to another column.
- **Delete Column** — clears all cells in that column (the column slot stays; content is removed).

Click a column header to select that performance column during a show.

## Scenes

The **scene bar** above the grid holds separate layouts (up to **32** scenes). Each scene keeps its own cells, row/column sizes, and **Global** FX stack.

- Click a **scene number** to switch to that scene.
- Click **+** to add a new scene.
- **Drag a scene button** onto another scene number to **reorder** scenes.
- Right-click a scene button for **Duplicate Scene** or **Delete Scene**.

Scenes are for switching between different setups during a show. Use **Settings -> Sets** to save and load the whole project to disk.

## Stacked Effects (Cell And Global)

Below the grid, the **Selected Cell** panel has two tabs for chaining multiple TOX effects.

### Cell tab (per-cell FX)

Select a loaded **TOX** cell, then open the **Cell** tab.

- The **source** row is the main effect loaded in the grid cell.
- Drag another `.tox` onto the **Cell** tab to add a stacked effect on that cell (up to 8).
- Stacked effects only work on **TOX cells**, not video cells.

**Change order** — drag an effect's **row header** onto another row header to reorder the chain. Drag the source row onto a stacked row (or the reverse) to **swap** them.

**Per-effect controls** — click a row header to expand/collapse its parameters. Use the bypass toggle to disable one step without removing it. Right-click a row for **Reload**, **Relink**, **Edit TOX**, **Copy**, **Cut**, **Paste**, or **Delete**.

Effects run in list order: source first, then each stacked effect below it in the panel.

### Global tab (program-wide FX)

Open the **Global** tab to add effects that process the **full composed output** after the grid (up to 8).

- Drag a `.tox` onto the **Global** tab to add an effect.
- Drag **row headers** to reorder the global chain.
- Use expand, bypass, and right-click menu the same way as **Cell** tab effects.

Global FX is stored **per scene** — switching scenes can load a different global stack.

## Basic Performance Workflow

1. Set the canvas size in **Settings -> Canvas**.
2. Load videos into the bottom row.
3. Right-click a row label and choose **Add Row Above** when you need more FX layers.
4. Load TOX effects into FX rows.
5. Select columns while performing (click column headers, or use MIDI/OSC).
6. Adjust heavy cells with Render Scale or Freeze.
7. Save the setup as a performance set.

## Cell Controls

### Render Scale

Render Scale makes a cell process at a lower resolution, then scales it back up for the final output. This is useful for heavy effects.

- `100%` gives full quality.
- `75%` is a good default for many FX.
- `67%`, `50%`, and `25%` are faster but softer.

Use lower values for heavy TOX effects, high resolution videos, or cells that are not visually sharp/detail-critical.

### Freeze

Freeze pauses a cell where possible.

For videos, Freeze holds the current frame. For TOX effects, Sonomika tries to pause internal animation/source nodes without freezing the whole column. Frozen cells show a small black `F` badge with white text.

## Settings

The Perform **Settings** panel is driven by the **`/settings`** COMP at the project root (not inside `project1`). After upgrading an older project, pulse **Reload Scripts (Dev)** on **About** once so paths and panels heal correctly.

### About

**Install a package**

1. Choose a ZIP with **Install Package File**.
2. Press **Install Package**.
3. Check **Install Status**.

**Make a package from your current set**

1. Save or open the set you want to package.
2. Open **Settings -> About** and press **Make Package**.
3. Check **Package Status**. The finished ZIP is saved in the `packages`
   folder.

### Canvas

Use **Settings -> Canvas** to choose the main output resolution.

- **Canvas Preset** — built-in sizes: `1920x1080` (landscape), `1080x1920` (portrait), and `1080x1080` (square). Choosing a preset updates **Canvas Width** and **Canvas Height** immediately.
- **Canvas Width** / **Canvas Height** — set a custom size directly, or fine-tune after picking a preset.
- **Background Color** — letterbox/fill color when content does not match the canvas aspect.
- **Save Canvas Size** — stores the current width and height as a reusable custom preset (it appears in the preset menu).

### Sets

Performance sets save the grid state, loaded cells, and relevant settings. Use them to prepare different shows, scenes, or performance layouts.

### OSC

Use **Settings -> OSC** to receive OSC from other apps and hardware.

- **OSC Active** — turn incoming OSC on or off.
- **OSC Port** / **IP** — listen address (default port `7000`, IP `127.0.0.1` for same-machine apps).
- **Last Address** / **Last Value** — debug readouts for the most recent message.

Slots **1**–**8** map incoming addresses to normalized values:

- **N Address** — OSC path to listen for (for example `/live/track1/volume`).
- **N Min** / **N Max** — output range after mapping (incoming `0`–`1` is scaled to this range).
- **N Value** — live mapped result. Link TOX custom parameters or CHOP exports to these values with expressions.

Recommended maxforlive device to send parameter OSC from Ableton https://resolume.com/blog/8717

### GrdOSC

Use **Settings -> GrdOSC** to trigger the grid from OSC (for example Ableton Live clip-launch pads or a custom controller).

- **Grid OSC Active** — turn grid triggering on or off.
- **OSC Port** / **IP** — where Sonomika listens for grid messages (defaults match the **OSC** tab).
- **Address Prefix** — path prefix for grid addresses (default `/live`).
- **Simple** — reference list of per-column addresses, e.g. `/live/col1`, `/live/col2`, … Sending a bang or a value `≥ 0.5` to `/live/colN` selects column `N` across all rows.
- **Advanced** — reference for per-row routing, e.g. `/live/col1_L2_col2_L4` assigns layer 2 to column 1 and layer 4 to column 2.
- **Last Address** — debug readout for the last grid OSC message.

Use **Simple** addresses when every row should follow the same column. Use **Advanced** when FX rows need different column sources.

Recommended maxforlive device to send OSC from Ableton for the Grid https://structurevoid.gumroad.com/l/void-cue-2-osc


### Pulse

Use **Settings -> Pulse** for tempo-synced rhythmic outputs — useful for driving effects or sending OSC to external tools.

- **Active** — master on/off for the pulse engine.
- **Custom BPM** — when off, pulses follow TouchDesigner timeline tempo; when on, use **BPM** below.
- **BPM** — manual tempo when **Custom BPM** is on.

Six pulse slots (**1**–**6**), each with:

- **N Active** — enable this slot.
- **N Division** — rhythmic interval (`1/32` through `8 Bars`).
- **N Skip %** — probability to skip a hit (adds variation).
- **N LFO** — when on, oscillates smoothly between **N Min** and **N Max** over the division; when off, sends short pulse hits.
- **N Min** / **N Max** — output range for the slot.
- **N Value** — live readout.

When a slot fires, Sonomika also sends OSC to `/sonomika/pulse1` … `/sonomika/pulse6` on the **OSC** tab IP/port. Turn on **Active** and at least one slot **N Active** to hear or see output.

### Audio

Use **Settings -> Audio** for live input analysis. When the Audio tab is open, an **Audio Spectrum** strip sits above the settings controls (always visible on this tab). Spectrum animation cooks while **Audio Active** is on; analysis CHOPs stay live at full rate when Active.

**Device / analysis**

- **Input Device** — audio capture device (matches TouchDesigner audio device list).
- **Refresh Audio Input** — restart capture and rescan devices if input stops streaming (no app restart needed).
- **Audio Active** — turn analysis on or off. When off, the spectrum strip stays visible but greyed out.
- **Gain** — input boost.

**Spectrum strip**

- Drag the **Low** and **High** band blocks left/right to move them; drag edges to change width.
- Drag the horizontal threshold grips on each band (and Peak) to set sensitivity.
- Side meters show live **Low** / **High** / **Peak** levels and trigger flashes.

**Outputs (map these into effects)**

- **Low** / **High** / **Peak** — continuous `0`–`1` levels.
- **Low Trigger** / **High Trigger** / **Peak Trigger** — gate outputs when the level crosses the threshold.
- **Reverse Low / High / Peak Trigger** — invert each trigger gate.
- **Low / High / Peak Threshold** — numeric threshold values (same as the spectrum grips).

**Driving an effect parameter**

Drag **Low**, **High**, **Peak**, or a **Trigger** readout from the Audio settings onto a Pulse slot or TOX parameter, then click **Bind**. That links the `0`–`1` audio value live — no expressions to paste.

Start with **Audio Active** on, pick your **Input Device**, then adjust **Gain** and thresholds on the spectrum while watching the side meters and **Low** / **High** / **Peak** readouts.

### MIDI

Use **Dialogs -> MIDI Device Mapper** in TouchDesigner to create a MIDI mapper. Then open **Settings -> Midi**, select the same MIDI device ID, choose a template, set **Takeover Mode**, and press **Load Template**.

**Takeover Mode** controls how MIDI knobs interact with on-screen sliders when values do not match:

- **None** — knob position jumps the slider immediately (absolute mapping).
- **Pickup** — knob must cross the current slider value before it takes control (no jump on touch).
- **Value Scaling** — knob moves the slider smoothly toward the knob position each tick (default for new sets).

Built-in templates:

When MIDI is working, the **Received** field updates as you press pads or turn knobs.

To make a custom MIDI setup, use `templates/midi/README.md` as the guide. A good workflow is to note the controller's MIDI notes and CC indices in TouchDesigner's MIDI Device Mapper, then ask ChatGPT to create a Sonomika MIDI template JSON using that guide. Save the new `.json` file in `templates/midi/`, reload scripts if needed, then select the template and press **Load Template**.

### Fade

Use **Settings -> Fade** to control crossfades when switching content during a performance.

- **Fade** — master on/off for all crossfading.
- **Crossfade Cells** — smooth blend when a layer row switches which column it reads from (for example, changing source on an FX row).
- **Crossfade Column** — smooth blend when you select a different performance column across the grid.
- **Crossfade Duration (sec)** — how long column crossfades take (default `1.0`; range `0.05`–`10`).

Turn **Fade** off for instant cuts. For live shows, start with column crossfade on and a duration around `0.5`–`1.5` seconds, then adjust to taste.

### Performance

- **All Cell Render Scale** changes the render scale of existing loaded cells.
- **FX render scale** sets the default render scale for new TOX cells loaded into FX rows.
- **Thumbnail FPS** controls how often cell previews update.
- **Thumbnail Quality** controls preview resolution without changing the main output.

Good starting values:

- Thumbnail FPS: `5`
- Thumbnail Quality: `75%`
- FX render scale: `75%`

## Tips For Better Performance

Please note Sonomika is already tuned for performance.

- Lower Render Scale on heavy TOX cells first.
- Use **FX render scale** so new FX cells start lighter.
- Lower Thumbnail FPS if the interface feels heavy.
- Lower Thumbnail Quality if previews are using too much GPU.
- Freeze cells that do not need to keep moving.
- Keep full `100%` scale only where the image needs to stay sharp.

## Troubleshooting

### A Cell Looks Soft Or Low Resolution

Check the cell Render Scale. Set it back to `100%` if you need full quality. Also check **FX render scale**, because new FX cells may start below full resolution.

### A Heavy Effect Slows Down The Project

Lower that cell's Render Scale first. If it is still heavy, lower Thumbnail FPS or Thumbnail Quality, then freeze cells that do not need to animate.

### MIDI Is Not Working

Check that the controller is mapped in TouchDesigner's MIDI Device Mapper. Make sure the same mapper ID is selected in **Settings -> Midi -> MIDI Device**, a template is selected, and **Load Template** has been pressed.

### OSC Or Grid OSC Is Not Working

Check **OSC Active** or **Grid OSC Active** is on, the port matches your sending app, and firewall rules allow UDP on that port. Watch **Last Address** / **Last Value** (OSC) or **Last Address** (GrdOSC) while sending test messages. For grid control, addresses must start with your **Address Prefix** (default `/live`).

### Pulse Or Audio Readouts Stay Flat

For **Pulse**, turn on **Active**, enable at least one slot, and make sure TouchDesigner transport is playing (or turn on **Custom BPM**). For **Audio**, turn on **Audio Active**, select the correct **Input Device**, and raise **Gain** if levels are low. Open the **Audio** settings tab so you can see the spectrum meters. If readouts stay flat while audio is playing, press **Refresh Audio Input**.

### A Cell Shows “missing”

The stored path no longer points at a readable file (moved folder, renamed TOX, external drive offline). Right-click the cell → **Relink** and choose the new file. Re-opening a performance **Set** can also restore saved parameter state after Relink. Stacked **Cell** / **Global** effects have the same **Relink** item in their right-click menus.

### A TOX Does Not Follow Render Scale

Some TOX files have fixed internal resolutions. TOX files work best when their internal TOPs follow the input resolution or use custom resolution settings linked to the input.

## Making Effects For Sonomika

Use bundled TOX as a guide.

TOX files run best in Sonomika when they follow the incoming resolution and avoid unnecessary cooking.

- Make the final output TOP follow the input resolution where possible.
- Avoid hard-coded internal resolutions unless the effect really needs them.
- If you use `fitTOP`, `resolutionTOP`, `scriptTOP`, or render TOPs, make their width/height follow the input or expose resolution controls.
- Keep Script TOP work light. Cache static drawings, avoid rebuilding large NumPy images every frame, and use GPU TOPs for compositing when possible.
- Pause or gate animation drivers cleanly. Effects that use timers, LFOs, noise, feedback, or execute DATs should tolerate being paused.
- Bypass or disable unused branches so inactive parts of a TOX do not keep cooking.
- Expose useful custom parameters with clear names so they appear nicely in the Selected Cell panel.
- Test the TOX at `100%`, `75%`, `50%`, and frozen state to make sure it still behaves correctly.
