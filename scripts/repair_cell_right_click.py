"""Restore cell left/right-click routing in the open performance grid."""
import os

pm = op('/project1/performance_mode')
logic = pm.op('logic')
logic.module.reload_scripts()
mod = logic.module

mod._refresh_panel_exec_panels()
pe = pm.op('panel_exec')
if pe is None:
    raise RuntimeError('Missing performance_mode/panel_exec')

pe.par.active = True
pe.par.panelvalue = 'lselect rselect u v insidev mousev scrollu scrollx wheel'
pe.par.offtoon = True
pe.par.ontooff = True
pe.par.valuechange = True
pe.par.whileon = True

grid = pm.op('ui/grid_stack/grid')
cells = []
if grid is not None:
    for layer in range(1, mod._num_layers() + 1):
        row = grid.op('row_{}'.format(layer))
        if row is None:
            continue
        for col in range(1, mod._num_cols() + 1):
            cell = row.op('cell_{}_{}'.format(layer, col))
            if cell is None:
                continue
            cells.append(cell.path)
            try:
                cell.par.enable = True
                cell.par.clickthrough = False
            except Exception:
                pass

monitored = str(pe.par.panels.eval())
missing = [path for path in cells if path not in monitored]
if missing:
    pe.par.panels = (monitored + ' ' + ' '.join(missing)).strip()

report = os.path.join(
    r'C:/Users/ridle/OneDrive/Documents Backup/1_Cursor/TouchDesigner/SonomikaTD',
    'output', 'cell_right_click_repair.txt',
).replace('\\', '/')
with open(report, 'w', encoding='utf-8') as out:
    out.write('cells: {}\n'.format(len(cells)))
    out.write('missing cells added: {}\n'.format(len(missing)))
    out.write('panelvalue: {}\n'.format(pe.par.panelvalue.eval()))
    out.write('active: {}\n'.format(pe.par.active.eval()))

project.save(project.file)
print('Cell right-click repaired:', report)
