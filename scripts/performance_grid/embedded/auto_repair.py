AUTO_REPAIR = r'''# Heal FX feeds periodically; never reload builder or onInit here (preserves grid).
_repair_tick = 0

def onStart():
    # Intentionally empty: reloading builder or running onInit here resets grid/playback.
    pass

def onFrameStart(frame):
    global _repair_tick
    try:
        parent().op('logic').module._tick_column_xfade()
    except Exception:
        pass
    try:
        parent().op('logic').module._update_perf_readouts()
    except Exception:
        pass
    try:
        parent().op('logic').module._update_scene_bpm_display()
    except Exception:
        pass
    try:
        parent().op('logic').module._update_audio_readouts()
    except Exception:
        pass
    try:
        parent().op('logic').module._tick_cell_performance_controls()
    except Exception:
        pass
    _repair_tick += 1
    if _repair_tick % 45 != 0:
        return
    try:
        parent().op('logic').module.heal_osc_callbacks_if_needed()
    except Exception:
        pass
    try:
        parent().op('logic').module._auto_heal_active_column()
    except Exception:
        pass
'''
