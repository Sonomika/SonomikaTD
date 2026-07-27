"""Repair packaged audio input initialization and spectrum presentation."""

pm = op('/project1/performance_mode')
logic = pm.op('logic')
logic.module.reload_scripts()
mod = logic.module

mod.configure_audio_analysis()
mod._refresh_audio_device_menu(force=True)
mod._apply_audio_device()
mod._sync_audio_active()

view = pm.op('ui/audio_panel/audio_spectrogram')
if view is not None:
    stale = view.op('spect_view')
    if stale is not None:
        stale.destroy()
    mod._sync_spectrogram_display(view, force=True)
mod._sync_audio_spectrum_for_settings_tab(force=True)

project.save(project.file)
print('Release audio repaired and saved:', project.file)
