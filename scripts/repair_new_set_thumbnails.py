"""Apply New Set thumbnail clearing fix to the open release."""

pm = op('/project1/performance_mode')
logic = pm.op('logic')
logic.module.reload_scripts()
mod = logic.module
mod._reset_empty_grid_previews()
mod._refresh_ui(full=True)
project.save()
print('New Set thumbnail reset repaired and saved')
