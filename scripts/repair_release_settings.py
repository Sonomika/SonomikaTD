"""Remove stray URL COMP and rebuild/heal all /settings tabs."""
import os
import sys

REPORT = os.path.join(project.folder, 'output', 'settings_tab_repair.txt').replace('\\', '/')
stray_path = '/https___github_com_aaronmylespereira_TD_Toxes'
stray = op(stray_path)
removed = False
if stray is not None:
    stray.destroy()
    removed = True

pm = op('/project1/performance_mode')
logic = pm.op('logic')
try:
    logic.module.reload_scripts()
except Exception:
    pass

for key in list(sys.modules.keys()):
    if key == 'performance_grid' or key.startswith('performance_grid.'):
        del sys.modules[key]

from performance_grid.builder import helpers_settings

settings = helpers_settings._build_settings(pm)
mod = logic.module
for fn_name in (
    'configure_osc_input',
    'configure_midi_input',
    'configure_pulse_engine',
    'configure_audio_analysis',
    'heal_canvas_tab',
    'heal_fade_tab',
    'heal_perf_tab',
):
    fn = getattr(mod, fn_name, None)
    if fn is None:
        continue
    try:
        if fn_name == 'configure_pulse_engine':
            fn(reset_sync=False)
        else:
            fn()
    except Exception as exc:
        print(fn_name, 'warning:', exc)

try:
    mod._refresh_settings_params_panel()
except Exception:
    pass

pages = [page.name for page in settings.customPages]
expected = ['Canvas', 'Sets', 'OSC', 'Grid OSC', 'Pulse', 'Audio', 'Midi', 'Fade', 'Perf', 'About']
missing = [name for name in expected if name not in pages]

with open(REPORT, 'w', encoding='utf-8') as out:
    out.write('Removed stray URL COMP: {}\n'.format(removed))
    out.write('Settings pages: {}\n'.format(', '.join(pages)))
    out.write('Missing expected pages: {}\n'.format(', '.join(missing) or 'none'))

target = r'C:/Users/ridle/OneDrive/Documents Backup/1_Cursor/TouchDesigner/SonomikaTD/SonomikaTD.toe'
project.save(target)
print('Removed stray URL COMP:', removed)
print('Settings pages:', pages)
print('Missing expected pages:', missing)
print('Saved:', target)
