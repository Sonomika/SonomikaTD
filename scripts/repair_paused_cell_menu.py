"""Apply paused right-click fix to the open SonomikaTD release."""

pm = op('/project1/performance_mode')
logic = pm.op('logic')
logic.module.reload_scripts()
mod = logic.module

# Re-apply the current transport state using the new UI-safe implementation.
mod._set_global_transport_playing(mod.global_transport_playing())

panel_exec = pm.op('panel_exec')
if panel_exec is not None:
    panel_exec.allowCooking = True
    try:
        panel_exec.par.active = True
    except Exception:
        pass

project.save()
print('Paused cell right-click repaired and saved')
