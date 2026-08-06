PANEL_EXEC = r'''def _root():
    return parent()

def _logic():
    r = _root()
    return r.op('logic').module if r else None

def _panel_target(owner):
    """Resolve scene bar / transport buttons when click hits label_text child."""
    p = owner
    for _ in range(8):
        if p is None:
            break
        n = getattr(p, 'name', '')
        if n.startswith('scene_btn_'):
            try:
                return 'scene', int(n.split('_')[2])
            except Exception:
                pass
        if n == 'scene_add':
            return 'scene_add', None
        if n == 'scene_to_start':
            return 'scene_to_start', None
        if n == 'scene_play':
            return 'scene_play', None
        if n == 'scene_pause':
            return 'scene_pause', None
        if n == 'bpm_up':
            return 'bpm_up', None
        if n == 'bpm_down':
            return 'bpm_down', None
        if n in ('scene_bpm', 'bpm_value'):
            return 'bpm_value', None
        if n == 'open_effects_folder':
            return 'open_effects_folder', None
        if n == 'params_tab_layer':
            return 'params_tab_layer', None
        if n == 'params_tab_global':
            return 'params_tab_global', None
        if n == 'global_fx_panel':
            return 'global_fx_panel', None
        if n == 'layer_fx_panel':
            return 'layer_fx_panel', None
        if n == 'map_control_expand' or n == 'map_control_hdr':
            return 'map_control_expand', None
        if n.startswith('map_dial_') and n.endswith('_range_min'):
            try:
                return 'map_dial_range_min', int(n.replace('map_dial_', '').replace('_range_min', ''))
            except Exception:
                pass
        if n.startswith('map_dial_') and n.endswith('_range_max'):
            try:
                return 'map_dial_range_max', int(n.replace('map_dial_', '').replace('_range_max', ''))
            except Exception:
                pass
        if n.startswith('map_dial_') and n.endswith('_knob'):
            try:
                return 'map_dial_knob', int(n.replace('map_dial_', '').replace('_knob', ''))
            except Exception:
                pass
        if n.startswith('map_dial_') and n.endswith('_bind_value'):
            try:
                return 'map_dial_bind', int(n.replace('map_dial_', '').replace('_bind_value', ''))
            except Exception:
                pass
        if n.startswith('map_dial_') and n.endswith('_bind_label'):
            try:
                return 'map_dial_bind', int(n.replace('map_dial_', '').replace('_bind_label', ''))
            except Exception:
                pass
        if n.startswith('map_dial_') and n.endswith('_bind') and not n.endswith('_bind_value'):
            try:
                return 'map_dial_bind', int(n.replace('map_dial_', '').replace('_bind', ''))
            except Exception:
                pass
        if n.startswith('gfx_bypass_'):
            try:
                return 'gfx_bypass', int(n.split('_')[-1])
            except Exception:
                pass
        if n.startswith('gfx_expand_'):
            try:
                return 'gfx_expand', int(n.split('_')[-1])
            except Exception:
                pass
        if n.startswith('gfx_row_hdr_'):
            try:
                return 'gfx_row_hdr', int(n.split('_')[-1])
            except Exception:
                pass
        if n.startswith('lfx_bypass_'):
            try:
                return 'lfx_bypass', int(n.split('_')[-1])
            except Exception:
                pass
        if n == 'lfx_bypass_source':
            return 'lfx_bypass', None
        if n.startswith('lfx_expand_'):
            sfx = n.replace('lfx_expand_', '')
            if sfx == 'source':
                return 'lfx_expand', 'source'
            try:
                return 'lfx_expand', int(sfx)
            except Exception:
                pass
        if n.startswith('lfx_row_hdr_'):
            sfx = n.replace('lfx_row_hdr_', '')
            if sfx == 'source':
                return 'lfx_row_hdr', 'source'
            try:
                return 'lfx_row_hdr', int(sfx)
            except Exception:
                pass
        if n in ('audio_band_view', 'audio_band_strip'):
            return 'audio_band_view', None
        if n in ('band_shade_bass', 'band_handle_bass_lo', 'band_handle_bass_hi', 'band_tag_bass', 'band_hit_bass', 'band_thresh_hit_bass'):
            if n == 'band_thresh_hit_bass':
                return 'band_thresh_hit_bass', None
            return n if n != 'band_hit_bass' else 'band_shade_bass', None
        if n in ('band_shade_high', 'band_handle_high_lo', 'band_handle_high_hi', 'band_tag_high', 'band_hit_high', 'band_thresh_hit_high'):
            if n == 'band_thresh_hit_high':
                return 'band_thresh_hit_high', None
            return n if n != 'band_hit_high' else 'band_shade_high', None
        if n == 'thresh_slider_bass':
            return 'thresh_slider_bass', None
        if n == 'thresh_slider_high':
            return 'thresh_slider_high', None
        if n in ('thresh_slider_peak', 'peak_thresh_bar'):
            return 'thresh_slider_peak', None
        if n == 'hist_freeze':
            return 'audio_hist_freeze', None
        if n == 'rev':
            try:
                key = p.fetch('audio_trig_reverse')
            except Exception:
                key = None
            if key in ('low', 'high', 'peak'):
                return 'audio_trig_reverse', key
            parent_name = getattr(p.parent(), 'name', '') if p.parent() is not None else ''
            if parent_name == 'meter_low':
                return 'audio_trig_reverse', 'low'
            if parent_name == 'meter_high':
                return 'audio_trig_reverse', 'high'
            if parent_name == 'meter_peak':
                return 'audio_trig_reverse', 'peak'
        if n in ('fill', 'thumb', 'tag', 'hit'):
            try:
                if getattr(p.parent(), 'name', '') == 'peak_thresh_bar':
                    return 'thresh_slider_peak', None
            except Exception:
                pass
        try:
            p = p.parent()
        except Exception:
            break
    return None, None


def _audio_band_view(owner):
    p = owner
    for _ in range(10):
        if p is None:
            break
        if getattr(p, 'name', '') == 'audio_band_view':
            return p
        try:
            p = p.parent()
        except Exception:
            break
    return None


def _audio_hist_uv(panel, owner):
    """Mouse position in spectrogram view space (0-1).

    Prefer view.panel.insideu/insidev — those track the cursor over children.
    Never map from a child overlay's live x/y: during band drag the shade/tag
    moves under the cursor, so local→view remapping cancels the gesture.
    """
    oname = getattr(owner, 'name', '') if owner is not None else ''
    # Peak column: read v from the stationary full-height hit child.
    if oname == 'peak_thresh_bar':
        hit = None
        try:
            hit = owner.op('hit')
        except Exception:
            hit = None
        for src_panel in (
            (hit.panel if hit is not None else None),
            (owner.panel if owner is not None else None),
        ):
            if src_panel is None:
                continue
            for attr in ('v', 'insidev'):
                try:
                    return 0.5, max(0.0, min(1.0, float(getattr(src_panel, attr))))
                except Exception:
                    pass
        try:
            if getattr(panel, 'name', '') == 'v':
                return 0.5, max(0.0, min(1.0, float(panel)))
        except Exception:
            pass
        return 0.5, 0.5

    view = _audio_band_view(owner)
    if view is not None:
        try:
            u = float(view.panel.insideu)
            v = float(view.panel.insidev)
            return (
                max(0.0, min(1.0, u)),
                max(0.0, min(1.0, v)),
            )
        except Exception:
            pass
        try:
            return (
                max(0.0, min(1.0, float(view.panel.u))),
                max(0.0, min(1.0, float(view.panel.v))),
            )
        except Exception:
            pass

    # Fallback: event panel only (no child→view remap).
    try:
        source = owner.panel if owner is not None else panel
    except Exception:
        source = panel
    try:
        try:
            return float(source.insideu), float(source.insidev)
        except Exception:
            return float(source.u), float(source.v)
    except Exception:
        return 0.5, 0.5


def _interactive_owner(owner):
    """Resolve clicks on displayed TOP children back to the interactive container."""
    p = owner
    for _ in range(8):
        if p is None:
            break
        n = getattr(p, 'name', '')
        if n.startswith('map_dial_'):
            parts = n.split('_')
            if len(parts) >= 3 and parts[2].isdigit():
                return p
        if n in (
            'rowlabel',
            'rowopacity',
            'opacity_fader',
            'opacity_groove',
            'opacity_fill',
            'opacity_thumb',
            'grid_vscroll',
            'icon_view',
            'audio_band_view',
            'band_shade_bass',
            'band_shade_high',
            'band_handle_bass_lo',
            'band_handle_bass_hi',
            'band_handle_high_lo',
            'band_handle_high_hi',
            'band_tag_bass',
            'band_tag_high',
            'band_hit_bass',
            'band_hit_high',
            'band_thresh_hit_bass',
            'band_thresh_hit_high',
            'thresh_slider_bass',
            'thresh_slider_high',
            'thresh_slider_peak',
            'peak_thresh_bar',
            'rev',
            'scene_bpm',
            'bpm_value',
            'bpm_up',
            'bpm_down',
        ):
            if n.endswith('_knob') and n.startswith('map_dial_'):
                return p
            if n in ('map_knob_groove', 'map_knob_fill', 'map_knob_thumb'):
                q = p
                for _ in range(6):
                    if q is None:
                        break
                    qname = getattr(q, 'name', '')
                    if qname.startswith('map_dial_') and qname.endswith('_knob'):
                        return q
                    try:
                        q = q.parent()
                    except Exception:
                        break
            if n in ('opacity_fader', 'opacity_groove', 'opacity_fill', 'opacity_thumb'):
                q = p
                for _ in range(6):
                    if q is None:
                        break
                    if getattr(q, 'name', '') == 'opacity_fader':
                        return q
                    try:
                        q = q.parent()
                    except Exception:
                        break
            return p
        if n.startswith('cell_') or n.startswith('colhdr_'):
            return p
        try:
            p = p.parent()
        except Exception:
            break
    return owner


def _coords(owner):
    owner = _interactive_owner(owner)
    n = owner.name
    if n == 'rowlabel':
        p = owner.parent()
        if p is not None and p.name.startswith('row_'):
            try:
                return int(p.name.split('_')[1]), None
            except Exception:
                pass
    if n in ('rowopacity', 'opacity_fader'):
        p = owner
        while p is not None:
            if p.name.startswith('row_'):
                try:
                    return int(p.name.split('_')[1]), 'opacity'
                except Exception:
                    pass
            try:
                p = p.parent()
            except Exception:
                break
    if n.startswith('cell_'):
        p = n.split('_')
        if len(p) == 3:
            return int(p[1]), int(p[2])
    if n.startswith('colhdr_'):
        p = n.split('_')
        if len(p) == 2:
            return None, int(p[1])
    return None, None


def _open_row_menu(owner, layer):
    logic = _logic()
    if logic is None or layer is None:
        return
    items = ['Add Row Above', 'Delete Row']
    disabled = []
    try:
        if logic.num_layers() >= logic.max_layers():
            disabled.append('Add Row Above')
        if logic.num_layers() <= logic.min_layers():
            disabled.append('Delete Row')
        elif layer == logic.base_layer():
            disabled.append('Delete Row')
    except Exception:
        pass

    def _menu_choice(info):
        choice = info.get('item', '')
        if choice == 'Add Row Above':
            logic.add_row_above(layer)
        elif choice == 'Delete Row':
            logic.delete_row(layer)

    try:
        op.TDResources.PopMenu.Open(
            items=items,
            callback=_menu_choice,
            disabledItems=disabled,
            dividersAfterItems=['Add Row Above'],
        )
    except Exception as exc:
        print('Row menu error:', exc)


def _open_cell_menu(owner, layer, col):
    logic = _logic()
    if logic is None:
        return
    clip_type, path = logic.get_cell(layer, col)
    clip = logic.get_clipboard()
    has_clip = bool(clip.get('path'))
    current_scale = 100
    try:
        current_scale = int(logic.get_cell_render_scale(layer, col))
    except Exception:
        pass
    render_items = []
    for pct in (100, 75, 67, 50, 25):
        label = 'Render Scale {}%'.format(pct)
        if pct == current_scale:
            label += ' (current)'
        render_items.append(label)
    frozen = False
    try:
        frozen = bool(logic.get_cell_frozen(layer, col))
    except Exception:
        pass
    freeze_item = 'Unfreeze Cell' if frozen else 'Freeze Cell'
    items = [
        'Reload', 'Relink', 'Edit TOX', 'Open Source Folder',
    ] + render_items + [freeze_item, 'Copy', 'Cut', 'Paste', 'Delete']
    disabled = []
    if not path:
        disabled.extend(['Reload', 'Relink', 'Edit TOX', 'Open Source Folder', 'Copy', 'Cut'])
        disabled.extend(render_items)
        disabled.append(freeze_item)
    elif clip_type != 'tox':
        disabled.append('Edit TOX')
    if not has_clip:
        disabled.append('Paste')

    def _menu_choice(info):
        choice = info.get('item', '')
        if choice == 'Reload':
            logic.reload_cell(layer, col)
        elif choice == 'Relink':
            def _relink():
                if hasattr(logic, 'relink_cell'):
                    logic.relink_cell(layer, col)
            try:
                run(_relink, delayFrames=1, fromOP=_root())
            except Exception:
                _relink()
        elif choice == 'Edit TOX':
            if hasattr(logic, 'edit_tox_cell'):
                logic.edit_tox_cell(layer, col)
        elif choice == 'Open Source Folder':
            if hasattr(logic, 'open_cell_source_folder'):
                logic.open_cell_source_folder(layer, col)
        elif choice.startswith('Render Scale '):
            try:
                pct = int(choice.replace('Render Scale ', '').split('%')[0])
                logic.set_cell_render_scale(layer, col, pct)
            except Exception as exc:
                print('Render scale error:', exc)
        elif choice in ('Freeze Cell', 'Unfreeze Cell'):
            try:
                logic.set_cell_frozen(layer, col, choice == 'Freeze Cell')
            except Exception as exc:
                print('Freeze error:', exc)
        elif choice == 'Copy':
            logic.copy_cell(layer, col)
        elif choice == 'Cut':
            logic.cut_cell(layer, col)
        elif choice == 'Paste':
            logic.paste_cell(layer, col)
        elif choice == 'Delete':
            logic.delete_cell(layer, col)

    try:
        op.TDResources.PopMenu.Open(
            items=items,
            callback=_menu_choice,
            disabledItems=disabled,
            dividersAfterItems=[
                'Open Source Folder',
                'Render Scale 25%', 'Render Scale 25% (current)',
                freeze_item,
                'Cut', 'Paste', 'Delete',
            ],
        )
    except Exception as exc:
        print('Cell menu error:', exc)


def _open_cell_fx_menu(fx_id):
    logic = _logic()
    if logic is None:
        return
    try:
        root = logic._root()
        layer = int(float(root.par.Selectedlayer.eval()))
        col = int(float(root.par.Selectedcol.eval()))
        is_source = str(fx_id) == 'source'
        fx_id = None if is_source else int(fx_id)
    except Exception:
        return

    items = ['Reload', 'Relink', 'Edit TOX', 'Copy', 'Cut', 'Paste', 'Delete']
    disabled = []
    try:
        ctype, path = logic.get_cell(layer, col)
        if not path:
            disabled.extend(['Reload', 'Relink', 'Edit TOX', 'Copy', 'Cut'])
        elif ctype != 'tox' and is_source:
            disabled.append('Edit TOX')
        elif not is_source:
            entry = logic._cell_fx_entry(layer, col, fx_id)
            if not entry or not entry.get('path'):
                disabled.extend(['Reload', 'Relink', 'Edit TOX', 'Copy', 'Cut'])
        if not logic.get_fx_clipboard().get('path'):
            disabled.append('Paste')
        if path and (not logic.cell_accepts_stacked_fx(layer, col) or len(logic._cell_fx_list(layer, col)) >= logic.CELL_FX_MAX):
            disabled.append('Paste')
    except Exception:
        disabled.extend(['Reload', 'Relink', 'Edit TOX', 'Copy', 'Cut', 'Paste'])

    def _menu_choice(info):
        choice = info.get('item', '')
        row_id = 'source' if is_source else fx_id
        if choice == 'Reload':
            if hasattr(logic, 'reload_cell_fx'):
                logic.reload_cell_fx(layer, col, row_id)
        elif choice == 'Relink':
            def _relink():
                if hasattr(logic, 'relink_cell_fx'):
                    logic.relink_cell_fx(layer, col, row_id)
            try:
                run(_relink, delayFrames=1, fromOP=_root())
            except Exception:
                _relink()
        elif choice == 'Edit TOX':
            if hasattr(logic, 'edit_tox_cell_fx'):
                logic.edit_tox_cell_fx(layer, col, row_id)
        elif choice == 'Copy':
            logic.copy_cell_fx(layer, col, row_id)
        elif choice == 'Cut':
            logic.cut_cell_fx(layer, col, row_id)
        elif choice == 'Paste':
            logic.paste_cell_fx(layer, col, row_id)
        elif choice == 'Delete':
            if is_source:
                if logic._cell_fx_list(layer, col):
                    logic.promote_cell_fx_to_source(layer, col)
                else:
                    logic.delete_cell(layer, col)
            else:
                logic.remove_cell_fx(layer, col, fx_id)

    try:
        op.TDResources.PopMenu.Open(
            items=items,
            callback=_menu_choice,
            disabledItems=disabled,
            dividersAfterItems=['Edit TOX', 'Cut', 'Paste'],
        )
    except Exception as exc:
        print('Cell FX menu error:', exc)


def _open_global_fx_menu(fx_id):
    logic = _logic()
    if logic is None or fx_id is None:
        return
    try:
        fx_id = int(fx_id)
    except Exception:
        return

    items = ['Reload', 'Relink', 'Edit TOX', 'Copy', 'Cut', 'Paste', 'Delete']
    disabled = []
    try:
        entry = logic._global_fx_entry(fx_id)
        if not entry or not entry.get('path'):
            disabled.extend(['Reload', 'Relink', 'Edit TOX', 'Copy', 'Cut'])
        if not logic.get_fx_clipboard().get('path') or len(logic._GLOBAL_FX) >= logic.GLOBAL_FX_MAX:
            disabled.append('Paste')
    except Exception:
        disabled.extend(['Reload', 'Relink', 'Edit TOX', 'Copy', 'Cut', 'Paste'])

    def _menu_choice(info):
        choice = info.get('item', '')
        if choice == 'Reload':
            if hasattr(logic, 'reload_global_fx'):
                logic.reload_global_fx(fx_id)
        elif choice == 'Relink':
            def _relink():
                if hasattr(logic, 'relink_global_fx'):
                    logic.relink_global_fx(fx_id)
            try:
                run(_relink, delayFrames=1, fromOP=_root())
            except Exception:
                _relink()
        elif choice == 'Edit TOX':
            if hasattr(logic, 'edit_tox_global_fx'):
                logic.edit_tox_global_fx(fx_id)
        elif choice == 'Copy':
            logic.copy_global_fx(fx_id)
        elif choice == 'Cut':
            logic.cut_global_fx(fx_id)
        elif choice == 'Paste':
            logic.paste_global_fx(fx_id)
        elif choice == 'Delete':
            logic.remove_global_fx(fx_id)

    try:
        op.TDResources.PopMenu.Open(
            items=items,
            callback=_menu_choice,
            disabledItems=disabled,
            dividersAfterItems=['Edit TOX', 'Cut', 'Paste'],
        )
    except Exception as exc:
        print('Global FX menu error:', exc)


def _open_fx_panel_menu(kind):
    logic = _logic()
    if logic is None:
        return
    disabled = []
    try:
        if not logic.get_fx_clipboard().get('path'):
            disabled.append('Paste')
        elif kind == 'global_fx_panel':
            if len(logic._GLOBAL_FX) >= logic.GLOBAL_FX_MAX:
                disabled.append('Paste')
        else:
            root = logic._root()
            layer = int(float(root.par.Selectedlayer.eval()))
            col = int(float(root.par.Selectedcol.eval()))
            ctype, path = logic.get_cell(layer, col)
            if path and (not logic.cell_accepts_stacked_fx(layer, col) or len(logic._cell_fx_list(layer, col)) >= logic.CELL_FX_MAX):
                disabled.append('Paste')
    except Exception:
        disabled.append('Paste')

    def _menu_choice(info):
        if info.get('item', '') != 'Paste':
            return
        if kind == 'global_fx_panel':
            logic.paste_global_fx()
            return
        try:
            root = logic._root()
            layer = int(float(root.par.Selectedlayer.eval()))
            col = int(float(root.par.Selectedcol.eval()))
            logic.paste_cell_fx(layer, col)
        except Exception:
            pass

    try:
        op.TDResources.PopMenu.Open(
            items=['Paste'],
            callback=_menu_choice,
            disabledItems=disabled,
        )
    except Exception as exc:
        print('FX panel menu error:', exc)


def _open_scene_menu(scene):
    logic = _logic()
    if logic is None or scene is None:
        return
    items = ['Duplicate Scene', 'Delete Scene']
    disabled = []
    try:
        if logic.num_scenes() >= logic.max_scenes():
            disabled.append('Duplicate Scene')
        if logic.num_scenes() <= logic.min_scenes():
            disabled.append('Delete Scene')
    except Exception:
        pass

    def _menu_choice(info):
        choice = info.get('item', '')
        if choice == 'Duplicate Scene':
            logic.duplicate_scene(scene)
        elif choice == 'Delete Scene':
            logic.delete_scene(scene)

    try:
        op.TDResources.PopMenu.Open(
            items=items,
            callback=_menu_choice,
            disabledItems=disabled,
            dividersAfterItems=['Duplicate Scene'],
        )
    except Exception as exc:
        print('Scene menu error:', exc)


def _open_column_menu(owner, col):
    logic = _logic()
    if logic is None or col is None:
        return
    items = ['Insert Column', 'Copy Column', 'Paste Column', 'Delete Column']
    disabled = []
    try:
        if not logic.column_has_clips(col):
            disabled.extend(['Copy Column', 'Delete Column'])
        clip = logic.get_column_clipboard()
        if not clip.get('cells'):
            disabled.append('Paste Column')
    except Exception:
        pass

    def _menu_choice(info):
        choice = info.get('item', '')
        if choice == 'Insert Column':
            logic.insert_column(col)
        elif choice == 'Copy Column':
            logic.copy_column(col)
        elif choice == 'Paste Column':
            logic.paste_column(col)
        elif choice == 'Delete Column':
            logic.delete_column(col)

    try:
        op.TDResources.PopMenu.Open(
            items=items,
            callback=_menu_choice,
            disabledItems=disabled,
            dividersAfterItems=['Insert Column', 'Paste Column', 'Delete Column'],
        )
    except Exception as exc:
        print('Column menu error:', exc)


def _slider_value(owner):
    for name in ('u', 'insideu', 'mouseu'):
        try:
            value = float(getattr(owner.panel, name))
            if 0.0 <= value <= 1.0:
                return value
        except Exception:
            pass
    try:
        return max(0.0, min(1.0, float(owner.panel.u)))
    except Exception:
        return 1.0


def _opacity_fader_target(owner):
    p = owner
    for _ in range(8):
        if p is None:
            break
        if getattr(p, 'name', '') == 'opacity_fader':
            return p
        if getattr(p, 'name', '') == 'rowopacity':
            try:
                return p.op('opacity_fader')
            except Exception:
                return None
        try:
            p = p.parent()
        except Exception:
            break
    return None


def _panel_lselect(panel):
    if panel is None:
        return False
    for name in ('val', 'value'):
        try:
            return float(getattr(panel, name)) > 0.0
        except Exception:
            pass
    try:
        return float(panel) > 0.0
    except Exception:
        pass
    try:
        return bool(panel.lselect)
    except Exception:
        return False


def _owner_lselect(owner):
    target = _opacity_fader_target(owner) or owner
    try:
        return bool(target.panel.lselect)
    except Exception:
        return False


def _opacity_slider_value_from_panel(panel):
    """Mouse Y while held. Release-time v changes are ignored elsewhere."""
    if panel is None:
        return None
    try:
        pname = getattr(panel, 'name', '')
    except Exception:
        pname = ''
    if pname in ('v', 'insidev', 'mousev'):
        for name in ('val', 'value'):
            try:
                value = float(getattr(panel, name))
                if 0.0 <= value <= 1.0:
                    return value
            except Exception:
                pass
    try:
        owner_panel = panel.owner.panel
    except Exception:
        owner_panel = None
    if owner_panel is not None:
        for name in ('v', 'insidev', 'mousev'):
            try:
                value = float(getattr(owner_panel, name))
                if 0.0 <= value <= 1.0:
                    return value
            except Exception:
                pass
    for name in ('v', 'insidev', 'mousev'):
        try:
            value = float(getattr(panel, name))
            if 0.0 <= value <= 1.0:
                return value
        except Exception:
            pass
    return None


def _opacity_slider_value(owner, panel=None):
    target = _opacity_fader_target(owner)
    if panel is not None:
        value = _opacity_slider_value_from_panel(panel)
        if value is not None:
            return value
    if target is None:
        return 1.0
    for name in ('v', 'insidev', 'mousev'):
        try:
            value = float(getattr(target.panel, name))
            if 0.0 <= value <= 1.0:
                return value
        except Exception:
            pass
    return 1.0


_OPACITY_LAST_CLICK = {}
_OPACITY_SKIP_DRAG = set()
_OPACITY_DBL_CLICK_SEC = 0.4
_CELL_LAST_CLICK = {}
_CELL_DBL_CLICK_SEC = 0.4


def _panel_now():
    try:
        return float(absTime.seconds)
    except Exception:
        import time
        return time.time()


def _opacity_skip_drag(layer):
    try:
        return int(layer) in _OPACITY_SKIP_DRAG
    except Exception:
        return False


def _handle_cell_double_click(layer, col):
    try:
        layer, col = int(layer), int(col)
    except Exception:
        return False
    now = _panel_now()
    key = (layer, col)
    last = _CELL_LAST_CLICK.get(key)
    _CELL_LAST_CLICK[key] = now
    if last is None or (now - last) > _CELL_DBL_CLICK_SEC:
        return False
    logic = _logic()
    if logic is not None and hasattr(logic, 'focus_cell_params'):
        logic.focus_cell_params(layer, col)
        return True
    if logic is not None and hasattr(logic, '_update_cell_params_ui'):
        try:
            logic._update_cell_params_ui(layer, col, force=True)
            return True
        except TypeError:
            logic._update_cell_params_ui(layer, col)
            return True
    return False


def _handle_opacity_double_click(layer):
    """Double-click row opacity fader to reset that row to 100%."""
    try:
        layer = int(layer)
    except Exception:
        return False
    now = _panel_now()
    last = _OPACITY_LAST_CLICK.get(layer)
    _OPACITY_LAST_CLICK[layer] = now
    if last is None or (now - last) > _OPACITY_DBL_CLICK_SEC:
        return False
    logic = _logic()
    if logic is not None:
        if hasattr(logic, 'set_layer_opacity_interactive'):
            logic.set_layer_opacity_interactive(layer, 1.0, mouse_drag=False)
        elif hasattr(logic, 'set_layer_opacity'):
            logic.set_layer_opacity(layer, 1.0)
    _OPACITY_SKIP_DRAG.add(layer)
    return True


def _handle_opacity_drag(owner, panel_owner=None, panel=None):
    if panel is not None and not _owner_lselect(panel_owner or owner):
        return False
    logic = _logic()
    if logic is None:
        return False
    layer, col = _coords(owner)
    if col != 'opacity' or layer is None:
        return False
    if _opacity_skip_drag(layer):
        return False
    if hasattr(logic, 'clear_midi_takeover_sync'):
        logic.clear_midi_takeover_sync()
    try:
        value = 1.0
        if hasattr(logic, 'opacity_slider_value_from_panel'):
            value = logic.opacity_slider_value_from_panel(panel, owner)
        else:
            value = _opacity_slider_value(panel_owner or owner, panel=panel)
        logic.set_layer_opacity_interactive(
            layer,
            value,
            mouse_drag=True,
        )
    except Exception as exc:
        print('Layer opacity set failed:', exc)
    return True


def _handle_map_dial_drag(owner, panel_owner=None, panel=None, dial_idx=None):
    if dial_idx is None:
        kind, dial_idx = _panel_target(owner)
        if kind != 'map_dial_knob':
            return False
    if panel is not None and not _owner_lselect(panel_owner or owner):
        return False
    logic = _logic()
    if logic is None:
        return False
    try:
        if hasattr(logic, 'map_dial_value_from_panel'):
            val = logic.map_dial_value_from_panel(panel, owner, dial_idx)
            if val is not None and hasattr(logic, 'set_map_dial_value_interactive'):
                logic.set_map_dial_value_interactive(dial_idx, val)
                return True
            if val is not None and hasattr(logic, 'set_map_dial_value'):
                logic.set_map_dial_value(dial_idx, val, light=True, from_midi=True)
                return True
    except Exception as exc:
        print('Map dial set failed:', exc)
    return False


def _panel_get(owner, names, default=0.0):
    for name in names:
        try:
            return float(getattr(owner.panel, name))
        except Exception:
            pass
    return float(default)


def _panel_set(owner, names, value):
    for name in names:
        try:
            setattr(owner.panel, name, value)
            return True
        except Exception:
            pass
    return False


def _sync_fixed_row_scroll(owner):
    if owner is None or getattr(owner, 'name', '') not in ('grid', 'grid_vscroll'):
        return False
    try:
        logic = _logic()
        if getattr(owner, 'name', '') == 'grid':
            ui = owner.parent().parent()
            value = _panel_get(owner, ('scrollv', 'scrolly', 'v'), 0.0)
        else:
            ui = owner.parent()
            value = 1.0 - _panel_get(owner, ('v', 'scrollv', 'scrolly'), 1.0)
            value = max(0.0, min(1.0, value))
        if logic is not None and hasattr(logic, 'sync_grid_vertical_scroll'):
            logic.sync_grid_vertical_scroll(value)
            return True
        if getattr(owner, 'name', '') == 'grid_vscroll':
            stack = ui.op('grid_stack') if ui is not None else None
            grid = stack.op('grid') if stack is not None else None
            if grid is not None:
                _panel_set(grid, ('scrollv', 'scrolly', 'v'), value)
        gutter = ui.op('grid_gutter') if ui is not None else None
        rows = gutter.op('fixed_rows') if gutter is not None else None
        if rows is None:
            return False
        _panel_set(rows, ('scrollv', 'scrolly', 'v'), value)
        return True
    except Exception as exc:
        print('Fixed row scroll sync failed:', exc)
        return False


def _sync_grid_horizontal_scroll(owner):
    if owner is None or getattr(owner, 'name', '') != 'grid_stack':
        return False
    try:
        grid = owner.op('grid')
        if grid is None:
            return False
        value = _panel_get(owner, ('scrollu', 'scrollx', 'u'), 0.0)
        _panel_set(grid, ('scrollu', 'scrollx', 'u'), value)
        return True
    except Exception as exc:
        print('Grid horizontal scroll sync failed:', exc)
        return False


def onOffToOn(panel):
    logic = _logic()
    if logic is None:
        return
    owner = _interactive_owner(panel.owner)
    pname = getattr(panel, 'name', '')
    # TD may fire the generic 'select' value instead of lselect/rselect when both
    # are monitored — remap so right-click still opens context menus.
    if pname == 'select':
        try:
            src = panel.owner.panel if panel.owner is not None else None
            if src is not None and bool(src.rselect):
                pname = 'rselect'
            elif src is not None and bool(src.lselect):
                pname = 'lselect'
        except Exception:
            pass

    if pname == 'lselect':
        kind, scene = _panel_target(owner)
        if kind == 'scene':
            logic.switch_scene(scene)
            return
        if kind == 'scene_add':
            logic.add_scene()
            return
        if kind == 'scene_to_start':
            logic.goto_timeline_start()
            return
        if kind == 'scene_play':
            logic.play_column()
            return
        if kind == 'scene_pause':
            logic.pause_column()
            return
        if kind in ('bpm_up', 'bpm_down'):
            fine = False
            try:
                fine = bool(panel.shift)
            except Exception:
                pass
            delta = 1.0 if kind == 'bpm_up' else -1.0
            if hasattr(logic, 'adjust_project_tempo'):
                logic.adjust_project_tempo(delta, fine=fine)
            return
        if kind == 'bpm_value':
            fine = False
            try:
                fine = bool(panel.shift)
            except Exception:
                pass
            if hasattr(logic, 'adjust_project_tempo'):
                try:
                    v = float(panel.v)
                except Exception:
                    v = 0.5
                logic.adjust_project_tempo(1.0 if v >= 0.5 else -1.0, fine=fine)
            return
        if kind == 'open_effects_folder':
            if hasattr(logic, 'open_effects_folder'):
                logic.open_effects_folder()
            return
        if kind == 'params_tab_layer':
            if hasattr(logic, 'set_params_tab'):
                logic.set_params_tab('layer')
            return
        if kind == 'params_tab_global':
            if hasattr(logic, 'set_params_tab'):
                logic.set_params_tab('global')
            return
        if kind == 'map_control_expand':
            if hasattr(logic, 'toggle_map_control_expanded'):
                logic.toggle_map_control_expanded()
            return
        if kind == 'gfx_bypass':
            if hasattr(logic, '_set_global_fx_bypass') and scene is not None:
                entry = logic._global_fx_entry(scene)
                logic._set_global_fx_bypass(scene, not (entry and entry.get('bypass')))
            return
        if kind == 'gfx_expand':
            if hasattr(logic, '_toggle_global_fx_expanded') and scene is not None:
                logic._toggle_global_fx_expanded(scene)
            return
        if kind == 'gfx_row_hdr':
            if hasattr(logic, '_toggle_global_fx_expanded') and scene is not None:
                logic._toggle_global_fx_expanded(scene)
            return
        if kind in ('lfx_bypass', 'lfx_expand', 'lfx_row_hdr'):
            try:
                r = logic._root()
                layer = int(float(r.par.Selectedlayer.eval()))
                col = int(float(r.par.Selectedcol.eval()))
            except Exception:
                return
            if kind == 'lfx_bypass' and scene is not None:
                entry = logic._cell_fx_entry(layer, col, scene)
                logic._set_cell_fx_bypass(layer, col, scene, not (entry and entry.get('bypass')))
            elif kind in ('lfx_expand', 'lfx_row_hdr'):
                logic._toggle_cell_fx_expanded(layer, col, scene if scene is not None else 'source')
            return
        if kind == 'audio_band_view':
            u, v = _audio_hist_uv(panel, owner)
            if hasattr(logic, 'handle_audio_hist_interact'):
                logic.handle_audio_hist_interact(u, v=v, pick_edge=True)
            return
        if kind == 'audio_trig_reverse':
            if hasattr(logic, 'toggle_audio_trigger_reverse') and scene in ('low', 'high', 'peak'):
                logic.toggle_audio_trigger_reverse(scene)
            return
        if kind == 'audio_hist_freeze':
            if hasattr(logic, 'toggle_audio_hist_freeze'):
                logic.toggle_audio_hist_freeze()
            return
        if kind in (
            'band_shade_bass', 'band_shade_high',
            'band_handle_bass_lo', 'band_handle_bass_hi',
            'band_handle_high_lo', 'band_handle_high_hi',
            'band_tag_bass', 'band_tag_high',
            'band_hit_bass', 'band_hit_high',
            'band_thresh_hit_bass', 'band_thresh_hit_high',
        ):
            if hasattr(logic, 'handle_audio_hist_interact'):
                try:
                    mode = None
                    if kind == 'band_handle_bass_lo':
                        mode = 'bass_lo'
                    elif kind == 'band_handle_bass_hi':
                        mode = 'bass_hi'
                    elif kind == 'band_handle_high_lo':
                        mode = 'high_lo'
                    elif kind == 'band_handle_high_hi':
                        mode = 'high_hi'
                    elif kind in ('band_tag_bass', 'band_thresh_hit_bass'):
                        mode = 'thresh_bass'
                    elif kind in ('band_tag_high', 'band_thresh_hit_high'):
                        mode = 'thresh_high'
                    elif kind in ('band_shade_bass', 'band_hit_bass'):
                        mode = 'band_bass'
                    elif kind in ('band_shade_high', 'band_hit_high'):
                        mode = 'band_high'
                    if mode is not None and mode.startswith('thresh_'):
                        band_key = 'bass' if mode == 'thresh_bass' else 'high'
                        # Grab-offset begin — axis locks on first move (u or v).
                        grab_u, grab_v = _audio_hist_uv(panel, owner)
                        if hasattr(logic, '_begin_band_thresh_drag'):
                            logic._begin_band_thresh_drag(
                                band_key, grab_v=grab_v, grab_u=grab_u,
                            )
                        else:
                            logic._AUDIO_HIST_DRAG['mode'] = mode
                            logic._AUDIO_HIST_DRAG['axis'] = None
                            logic._AUDIO_HIST_DRAG['thresh_grab_thr'] = (
                                logic._audio_threshold_for_band(band_key)
                                if hasattr(logic, '_audio_threshold_for_band') else 0.5
                            )
                            logic._AUDIO_HIST_DRAG['thresh_grab_v'] = grab_v
                            logic._AUDIO_HIST_DRAG['start_uv'] = (grab_u, grab_v)
                            if hasattr(logic, '_expand_band_thresh_capture'):
                                logic._expand_band_thresh_capture(band_key)
                        return
                    if mode is not None:
                        logic._AUDIO_HIST_DRAG['mode'] = mode
                        logic._AUDIO_HIST_DRAG['axis'] = 'u'
                        logic._AUDIO_HIST_DRAG.pop('thresh_grab_v', None)
                        logic._AUDIO_HIST_DRAG.pop('thresh_grab_thr', None)
                    u, v = _audio_hist_uv(panel, owner)
                    logic.handle_audio_hist_interact(u, v=v, pick_edge=True)
                except Exception:
                    pass
            return
        if kind == 'thresh_slider_bass':
            try:
                logic._AUDIO_HIST_DRAG['mode'] = 'thresh_bass'
            except Exception:
                pass
            if hasattr(logic, 'handle_audio_hist_interact'):
                try:
                    u, v = _audio_hist_uv(panel, owner)
                    logic.handle_audio_hist_interact(u, v=v, pick_edge=False)
                except Exception:
                    pass
            return
        if kind == 'thresh_slider_high':
            try:
                logic._AUDIO_HIST_DRAG['mode'] = 'thresh_high'
            except Exception:
                pass
            if hasattr(logic, 'handle_audio_hist_interact'):
                try:
                    u, v = _audio_hist_uv(panel, owner)
                    logic.handle_audio_hist_interact(u, v=v, pick_edge=False)
                except Exception:
                    pass
            return
        if kind == 'thresh_slider_peak':
            try:
                logic._AUDIO_HIST_DRAG['mode'] = 'thresh_peak'
                bar = owner if getattr(owner, 'name', '') == 'peak_thresh_bar' else None
                if bar is None and hasattr(logic, '_peak_thresh_bar_from_ui'):
                    bar = logic._peak_thresh_bar_from_ui()
                logic._AUDIO_HIST_DRAG['peak_bar_op'] = bar
                logic._AUDIO_HIST_DRAG['last_thresh_px'] = None
                logic._AUDIO_HIST_DRAG.pop('thresh_grab_v', None)
                logic._AUDIO_HIST_DRAG.pop('thresh_grab_thr', None)
                u, v = _audio_hist_uv(panel, owner)
                # Absolute: click/drag height on the stationary hit layer sets threshold.
                logic.handle_audio_hist_interact(u, v=v, pick_edge=False)
            except Exception:
                pass
            return
        if owner is not None and getattr(owner, 'name', '') == 'grid_vscroll':
            _sync_fixed_row_scroll(owner)
            return
        layer, col = _coords(owner)
        if col == 'opacity' and layer is not None:
            if _handle_opacity_double_click(layer):
                return
            _handle_opacity_drag(owner, panel.owner, panel)
            return
        kind, dial_idx = _panel_target(owner)
        if kind == 'map_dial_knob' and dial_idx is not None:
            if hasattr(logic, 'block_map_dial_midi'):
                logic.block_map_dial_midi(dial_idx)
            if hasattr(logic, 'clear_midi_takeover_sync'):
                logic.clear_midi_takeover_sync()
            _handle_map_dial_drag(owner, panel.owner, panel, dial_idx)
            return
        if layer is not None and col is not None:
            double_clicked = _handle_cell_double_click(layer, col)
            shift = False
            try:
                shift = bool(panel.shift)
            except Exception:
                pass
            if shift:
                logic.composition_assign_layer_cell(layer, col, toggle=True)
            else:
                logic.trigger_cell(layer, col)
            if double_clicked and hasattr(logic, 'focus_cell_params'):
                logic.focus_cell_params(layer, col)
        elif col is not None:
            logic.trigger_column(col)
        return

    if pname == 'rselect':
        logic = _logic()
        dial_idx = None
        if logic is not None and hasattr(logic, '_map_dial_index_from_comp'):
            dial_idx = logic._map_dial_index_from_comp(owner)
        if dial_idx is not None and logic is not None and hasattr(logic, 'open_map_dial_menu'):
            try:
                logic.open_map_dial_menu(dial_idx)
            except Exception as exc:
                print('Map dial menu failed:', exc)
            return
        kind, scene = _panel_target(owner)
        if kind == 'scene':
            _open_scene_menu(scene)
            return
        if kind == 'gfx_row_hdr':
            _open_global_fx_menu(scene)
            return
        if kind == 'lfx_row_hdr':
            _open_cell_fx_menu(scene)
            return
        if kind in ('global_fx_panel', 'layer_fx_panel'):
            _open_fx_panel_menu(kind)
            return
        layer, col = _coords(owner)
        if col == 'opacity':
            return
        if owner is not None and getattr(owner, 'name', '') == 'rowlabel':
            _open_row_menu(owner, layer)
            return
        if layer is None and col is not None:
            _open_column_menu(owner, col)
            return
        if layer is not None and col is not None:
            _open_cell_menu(owner, layer, col)
        return


def onOnToOff(panel):
    """Mouse release — commit opacity param; do not re-read panel v."""
    try:
        if getattr(panel, 'name', '') != 'lselect':
            return
        owner = _interactive_owner(panel.owner)
        oname = getattr(owner, 'name', '') if owner is not None else ''
        if oname in (
            'audio_band_view',
            'band_shade_bass', 'band_shade_high',
            'band_handle_bass_lo', 'band_handle_bass_hi',
            'band_handle_high_lo', 'band_handle_high_hi',
            'band_tag_bass', 'band_tag_high',
            'band_hit_bass', 'band_hit_high',
            'band_thresh_hit_bass', 'band_thresh_hit_high',
            'thresh_slider_bass', 'thresh_slider_high',
            'thresh_slider_peak', 'peak_thresh_bar',
        ):
            logic = _logic()
            if logic is not None and hasattr(logic, 'clear_audio_hist_drag'):
                logic.clear_audio_hist_drag()
            return
        kind, dial_idx = _panel_target(owner)
        if kind == 'map_dial_knob' and dial_idx is not None:
            logic = _logic()
            if logic is not None and hasattr(logic, 'unblock_map_dial_midi'):
                try:
                    logic.unblock_map_dial_midi(dial_idx)
                except Exception:
                    pass
            if logic is not None and hasattr(logic, 'commit_map_dial_drag'):
                try:
                    logic.commit_map_dial_drag(dial_idx)
                except Exception:
                    pass
            if logic is not None and hasattr(logic, '_paint_map_dial'):
                try:
                    logic._paint_map_dial(dial_idx)
                except Exception:
                    pass
            return
        layer, col = _coords(owner)
        if col != 'opacity' or layer is None:
            return
        try:
            _OPACITY_SKIP_DRAG.discard(int(layer))
        except Exception:
            pass
        logic = _logic()
        if logic is not None and hasattr(logic, 'commit_layer_opacity_drag'):
            logic.commit_layer_opacity_drag(layer)
    except Exception:
        pass


def onValueChange(panel, prev):
    try:
        pname = str(getattr(panel, 'name', '') or '')
        raw_owner = panel.owner
        if raw_owner is not None and getattr(raw_owner, 'name', '') == 'settings_params':
            logic = _logic()
            if logic is not None:
                if pname in ('pageindex', 'page'):
                    # Spectrum/Active click settling: restore pre-click tab if TD stole it.
                    try:
                        import time
                        until = float(getattr(logic, '_AUDIO_PAGE_PRESERVE_UNTIL', 0) or 0)
                        want = getattr(logic, '_AUDIO_PAGE_PRESERVE_IDX', None)
                        if want is not None and float(time.time()) < until:
                            try:
                                cur = int(float(raw_owner.par.pageindex.eval()))
                            except Exception:
                                cur = None
                            if cur is not None and int(cur) != int(want):
                                raw_owner.par.pageindex = int(want)
                            return
                    except Exception:
                        pass
                    if hasattr(logic, '_sync_audio_spectrum_for_settings_tab'):
                        logic._sync_audio_spectrum_for_settings_tab(force=True)
                if hasattr(logic, '_apply_canvas_settings_change'):
                    logic._apply_canvas_settings_change(pname, panel)
                elif pname.startswith('Pulse') and hasattr(logic, '_apply_pulse_settings_change'):
                    logic._apply_pulse_settings_change(pname)
            return
        owner = _interactive_owner(raw_owner)
        layer, col = _coords(owner)
        if col == 'opacity' and layer is not None and pname in ('v', 'insidev', 'mousev'):
            _handle_opacity_drag(owner, panel.owner, panel)
            return
        kind, dial_idx = _panel_target(owner)
        if kind == 'map_dial_knob' and dial_idx is not None and pname in ('v', 'insidev', 'mousev'):
            _handle_map_dial_drag(owner, panel.owner, panel, dial_idx)
            return
        if pname in ('scrollv', 'scrolly', 'v'):
            if owner is not None and getattr(owner, 'name', '') in ('grid', 'grid_vscroll'):
                _sync_fixed_row_scroll(owner)
            return
        if pname in ('scrollu', 'scrollx', 'u') and _sync_grid_horizontal_scroll(owner):
            return
        if pname == 'wheel' and owner is not None:
            oname = getattr(owner, 'name', '')
            kind, dial_idx = _panel_target(owner)
            if kind in ('map_dial_range_min', 'map_dial_range_max') and dial_idx is not None:
                logic = _logic()
                if logic is not None and hasattr(logic, 'adjust_map_dial_range_field'):
                    fine = False
                    try:
                        fine = bool(panel.shift)
                    except Exception:
                        pass
                    try:
                        wheel = float(panel.wheel)
                    except Exception:
                        wheel = 0.0
                    if wheel != 0.0:
                        which = 'min' if kind == 'map_dial_range_min' else 'max'
                        logic.adjust_map_dial_range_field(dial_idx, which, wheel, fine=fine)
                return
            if oname == 'bpm_value':
                logic = _logic()
                if logic is not None and hasattr(logic, 'adjust_project_tempo'):
                    fine = False
                    try:
                        fine = bool(panel.shift)
                    except Exception:
                        pass
                    try:
                        wheel = float(panel.wheel)
                    except Exception:
                        wheel = 0.0
                    if wheel != 0.0:
                        logic.adjust_project_tempo(1.0 if wheel > 0.0 else -1.0, fine=fine)
                return
        if owner is None:
            return
        if pname not in ('u', 'v', 'insidev', 'mousev'):
            return
        # lselect may be on a child (peak hit) while interactive owner is the parent.
        pressed = False
        try:
            pressed = bool(owner.panel.lselect)
        except Exception:
            pressed = False
        if not pressed:
            try:
                pressed = bool(panel.owner.panel.lselect)
            except Exception:
                pressed = False
        if not pressed:
            return
        oname = getattr(owner, 'name', '')
        if oname in (
            'audio_band_view',
            'band_shade_bass', 'band_shade_high',
            'band_handle_bass_lo', 'band_handle_bass_hi',
            'band_handle_high_lo', 'band_handle_high_hi',
            'band_tag_bass', 'band_tag_high',
            'band_hit_bass', 'band_hit_high',
            'band_thresh_hit_bass', 'band_thresh_hit_high',
            'thresh_slider_bass', 'thresh_slider_high',
            'thresh_slider_peak', 'peak_thresh_bar',
        ):
            logic = _logic()
            if logic is not None and hasattr(logic, 'handle_audio_hist_interact'):
                # Peak / dedicated thresh sliders are vertical-only.
                if oname in (
                    'peak_thresh_bar', 'thresh_slider_peak',
                    'thresh_slider_bass', 'thresh_slider_high',
                ) and pname == 'u':
                    return
                # u and v each fire valueChange — once axis is locked, drop the
                # other so Low/High never move sideways and change height together.
                axis = None
                try:
                    axis = logic._AUDIO_HIST_DRAG.get('axis')
                except Exception:
                    axis = None
                if axis == 'v' and pname == 'u':
                    return
                if axis == 'u' and pname in ('v', 'insidev', 'mousev'):
                    return
                u, v = _audio_hist_uv(panel, owner)
                if pname in ('v', 'insidev', 'mousev') and oname not in (
                    'band_thresh_hit_bass', 'band_thresh_hit_high',
                    'band_tag_bass', 'band_tag_high',
                ):
                    try:
                        v = max(0.0, min(1.0, float(panel)))
                    except Exception:
                        pass
                try:
                    view = _audio_band_view(owner)
                    vw = max(1, int(view.par.w.eval()) if view else 400)
                    vh = max(1, int(view.par.h.eval()) if view else 200)
                    if oname == 'peak_thresh_bar':
                        try:
                            vh = max(1, int(owner.par.h.eval()))
                        except Exception:
                            pass
                    uu = max(0.0, min(1.0, float(u)))
                    vv = max(0.0, min(1.0, float(v)))
                    if axis == 'v' or oname in (
                        'peak_thresh_bar', 'thresh_slider_peak',
                        'thresh_slider_bass', 'thresh_slider_high',
                    ):
                        px_key = ('v', int(vv * vh))
                    elif axis == 'u':
                        px_key = ('u', int(uu * vw))
                    else:
                        px_key = (int(uu * vw), int(vv * vh))
                    if logic._AUDIO_HIST_DRAG.get('last_px') == px_key:
                        return
                except Exception:
                    pass
                logic.handle_audio_hist_interact(u, v=v, pick_edge=False)
            return
    except Exception as exc:
        print('Panel value change error:', exc)


def whileOn(panel):
    try:
        pname = getattr(panel, 'name', '')
        if pname != 'lselect':
            return
        raw_owner = panel.owner
        owner = _interactive_owner(raw_owner)
        if owner is None:
            return
        oname = getattr(owner, 'name', '') if owner is not None else ''
        raw_name = getattr(raw_owner, 'name', '') if raw_owner is not None else ''
        # Peak: while pressed, sample hit.v every cook (click works; drag needs this).
        if oname == 'peak_thresh_bar' or raw_name == 'hit':
            logic = _logic()
            if logic is None or not hasattr(logic, 'handle_audio_hist_interact'):
                return
            bar = owner if oname == 'peak_thresh_bar' else None
            if bar is None and raw_name == 'hit':
                try:
                    bar = raw_owner.parent()
                except Exception:
                    bar = None
            if bar is None:
                return
            try:
                logic._AUDIO_HIST_DRAG['mode'] = 'thresh_peak'
                logic._AUDIO_HIST_DRAG['peak_bar_op'] = bar
            except Exception:
                pass
            hit = None
            try:
                hit = bar.op('hit')
            except Exception:
                hit = None
            v = None
            for src in ((hit.panel if hit is not None else None), bar.panel):
                if src is None:
                    continue
                for attr in ('v', 'insidev', 'mousev'):
                    try:
                        v = max(0.0, min(1.0, float(getattr(src, attr))))
                        break
                    except Exception:
                        pass
                if v is not None:
                    break
            if v is None:
                return
            logic.handle_audio_hist_interact(0.5, v=v, pick_edge=False)
            return
        # Low/High horizontal bar — up/down threshold, left/right band move.
        if oname in ('band_thresh_hit_bass', 'band_thresh_hit_high'):
            logic = _logic()
            if logic is None or not hasattr(logic, 'handle_audio_hist_interact'):
                return
            band_key = 'bass' if oname == 'band_thresh_hit_bass' else 'high'
            try:
                if not logic._AUDIO_HIST_DRAG.get('thresh_capture_expanded'):
                    grab_u, grab_v = _audio_hist_uv(panel, owner)
                    if hasattr(logic, '_begin_band_thresh_drag'):
                        logic._begin_band_thresh_drag(
                            band_key, grab_v=grab_v, grab_u=grab_u,
                        )
                    else:
                        logic._AUDIO_HIST_DRAG['mode'] = (
                            'thresh_bass' if band_key == 'bass' else 'thresh_high'
                        )
                        logic._AUDIO_HIST_DRAG['axis'] = None
                else:
                    logic._AUDIO_HIST_DRAG['mode'] = (
                        'thresh_bass' if band_key == 'bass' else 'thresh_high'
                    )
                logic._AUDIO_HIST_DRAG['band_thresh_hit_op'] = owner
            except Exception:
                pass
            u, v = _audio_hist_uv(panel, owner)
            logic.handle_audio_hist_interact(u, v=v, pick_edge=False)
            return
        # Low/High body — sideways band move.
        if oname in ('band_hit_bass', 'band_hit_high', 'band_shade_bass', 'band_shade_high'):
            logic = _logic()
            if logic is None or not hasattr(logic, 'handle_audio_hist_interact'):
                return
            try:
                logic._AUDIO_HIST_DRAG['mode'] = (
                    'band_bass' if oname in ('band_hit_bass', 'band_shade_bass') else 'band_high'
                )
                logic._AUDIO_HIST_DRAG['axis'] = 'u'
            except Exception:
                pass
            u, v = _audio_hist_uv(panel, owner)
            logic.handle_audio_hist_interact(u, v=v, pick_edge=False)
            return
        # Edge grips — resize width.
        if oname in (
            'band_handle_bass_lo', 'band_handle_bass_hi',
            'band_handle_high_lo', 'band_handle_high_hi',
        ):
            logic = _logic()
            if logic is None or not hasattr(logic, 'handle_audio_hist_interact'):
                return
            try:
                mode = {
                    'band_handle_bass_lo': 'bass_lo',
                    'band_handle_bass_hi': 'bass_hi',
                    'band_handle_high_lo': 'high_lo',
                    'band_handle_high_hi': 'high_hi',
                }.get(oname)
                if mode:
                    logic._AUDIO_HIST_DRAG['mode'] = mode
            except Exception:
                pass
            u, v = _audio_hist_uv(panel, owner)
            logic.handle_audio_hist_interact(u, v=v, pick_edge=False)
            return
        layer, col = _coords(owner)
        if col == 'opacity' and layer is not None:
            if _opacity_skip_drag(layer):
                return
            _handle_opacity_drag(owner, panel.owner, panel)
            return
        kind, dial_idx = _panel_target(owner)
        if kind == 'map_dial_knob' and dial_idx is not None:
            _handle_map_dial_drag(owner, panel.owner, panel, dial_idx)
            return
    except Exception as exc:
        print('Panel while-on error:', exc)
'''
