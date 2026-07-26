"""Upgrade / repair particle_flowfields Manual Beat.

Run inside TouchDesigner (Textport or MCP), e.g.:

    import sys
    sys.path.insert(0, r'.../SonomikaTD/scripts')
    from tox_tools.particle_flowfields_beat import apply_to_project
    apply_to_project()

Beat may be pulsed from the UI or bound to kick (e.g. Audiooutkick). Envelope
uses rising-edge detection so a held-high kick does not retrigger every frame.
"""
from __future__ import annotations

import os

ENV_EXPR = (
    "0 if (absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9)) < 0 else "
    "((absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9))/0.1) if "
    "(absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9)) < 0.1 else "
    "(max(0, 1.0 - ((absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9))-0.1)/0.5) "
    "if (absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9)) < 0.6 else 0)"
)

MOTION = r'''layout(location=0) out vec4 final_color0;
layout(location=1) out vec4 final_color1;
layout(location=2) out vec4 final_color2;

uniform vec3 resolution;
uniform vec4 colz;
uniform vec4 trigger;
uniform vec4 centre;
uniform vec4 sim; // x=tmult y=turbulencemult z=videocolor

float res = resolution.x;
float increment = 1.0/resolution.x;
float speed = 0.01;
float tmult = sim.x;
float turbulencemult = sim.y;
float videocolor = sim.z;

vec3 videoColourAt(vec3 position) {
	vec2 vuv = fract(position.xy * 0.35 + 0.5);
	return texture(sTD2DInputs[7], vuv).rgb;
}

vec3 baseColour(vec3 position) {
	if (videocolor > 0.5) {
		return videoColourAt(position);
	}
	return clamp(colz.rgb, 0.0, 1.0);
}

void main()
{
	vec3 position, normals, color;

	if(vUV.t > 1.0-increment )
	{
		position = texture(sTD2DInputs[4],vec2(vUV.s,0.0)).rgb;
		normals = texture(sTD2DInputs[6],vec2(vUV.s,0.0)).rgb;
		color = baseColour(position);
	}
	else
	{
		double offx = (increment * res) + vUV.s;
		double offy = (float(offx > 1) / res) + vUV.t;
		position = texture(sTD2DInputs[1],vec2(offx,offy)).rgb;
		normals = texture(sTD2DInputs[2],vec2(offx,offy)).rgb;
		color = texture(sTD2DInputs[5],vec2(offx,offy)).rgb;

		vec3 turn = vec3(cos(position.y * tmult), sin(position.z * tmult), sin(position.x * tmult));

		float lu = -1.0 * (float(position.r >0.0) * -1.0) * position.r;
		float lv = -1.0 * (float(position.b >0.0) * -1.0) * position.b;
		float lz = -1.0 * (float(position.g >0.0) * -1.0) * position.g;
		vec2 texCoord1 = vec2(mod(lu,1.0), mod(lv,1.0));
		vec2 texCoord2 = vec2(mod(lz,1.0), mod(lu,1.0));

		vec3 velocity = texture(sTD2DInputs[0], texCoord1 ).rgb * turbulencemult + turn ;
		velocity += texture(sTD2DInputs[3], texCoord2 ).rgb + (normals/ 2.0) ;

		position += normalize(velocity)* speed * max(trigger.x, 0.0);
		normals = normalize( normals +((velocity - 0.5) / 3.0));
		color -= increment * 1.35;
		color = max(color, vec3(0.0));
	}

	final_color0 = vec4(position.rgb,1.0);
	final_color1 = vec4(normals,1.0);
	final_color2 = vec4(color,1.0);
}
'''

PE_TEXT = '''def _sync_beat_ui(root):
	mode = str(root.par.Beatmode.eval()) if hasattr(root.par, 'Beatmode') else 'off'
	# Beat Division is BPM-only; Beat button is Manual-only.
	if hasattr(root.par, 'Beatdiv'):
		root.par.Beatdiv.enable = (mode == 'bpm')
	if hasattr(root.par, 'Beat'):
		root.par.Beat.enable = (mode == 'pulse')
	# Keep user binds (e.g. kick -> Beat). Rising-edge logic handles held highs.


def onOffToOn(par):
	return


def onOnToOff(par):
	return


def onValueChange(par, prev):
	if par.name == 'Beatmode':
		_sync_beat_ui(me.parent())
	return


def onPulse(par):
	root = me.parent()
	if par.name == 'Beat':
		if str(root.par.Beatmode.eval()) == 'pulse':
			root.store('pulse_beat_t', absTime.seconds - 0.05)
		return
	if par.name != 'Reset':
		return
	p1 = root.op('flowfields/particles1')
	if p1 is None:
		return
	for fbname in ('feedback1', 'feedback2', 'feedback3'):
		fb = p1.op(fbname)
		if fb is None:
			continue
		for pname in ('reset', 'resetpulse', 'clear'):
			p = getattr(fb.par, pname, None)
			if p is not None:
				try:
					p.pulse()
					break
				except Exception:
					pass
'''

EX_TEXT = '''def onStart():
	return


def onCreate():
	return


def onExit():
	return


def onFrameStart(frame):
	root = me.parent()
	if not hasattr(root.par, 'Beatmode'):
		return
	if str(root.par.Beatmode.eval()) != 'pulse':
		return

	# Rising-edge only — UI pulse and kick bind. No retrigger while held high.
	pc = root.op('flowfields/motion/pulse_par')
	cur = 0.0
	if pc is not None:
		try:
			if pc.numChans:
				cur = float(pc[0])
		except Exception:
			cur = 0.0
	try:
		if hasattr(root.par, 'Beat') and root.par.Beat.eval():
			cur = max(cur, 1.0)
	except Exception:
		pass
	prev = float(root.fetch('pulse_flip_prev', 0.0))
	if cur > 0.5 and prev <= 0.5:
		root.store('pulse_beat_t', absTime.seconds - 0.05)
	root.store('pulse_flip_prev', cur)
	return


def onFrameEnd(frame):
	return
'''

CE_TEXT = '''def onOffToOn(channel, sampleIndex, val, prev):
	root = me.parent(3)
	if str(root.par.Beatmode.eval()) != 'pulse':
		return
	root.store('pulse_beat_t', absTime.seconds - 0.05)
	root.store('pulse_flip_prev', 0.0)


def onOnToOff(channel, sampleIndex, val, prev):
	return


def onWhileOn(channel, sampleIndex, val, prev):
	return


def onWhileOff(channel, sampleIndex, val, prev):
	return


def onValueChange(channel, sampleIndex, val, prev):
	if val <= 0.5 or prev > 0.5:
		return
	root = me.parent(3)
	if str(root.par.Beatmode.eval()) != 'pulse':
		return
	root.store('pulse_beat_t', absTime.seconds - 0.05)
	root.store('pulse_flip_prev', 0.0)
'''

DEFAULT_SAVE_PATHS = (
    r'tox\Factory\particle_flowfields.tox',
    r'release\tox\particle_flowfields.tox',
)


def _repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, '..', '..'))


def _clear_beat_bind(wrap):
    # Intentionally keep user binds (kick -> Beat). Rising-edge handles hold.
    if not hasattr(wrap.par, 'Beat'):
        return 'no Beat'
    p = wrap.par.Beat
    was = str(getattr(p, 'bindExpr', '') or '')
    mode_name = str(getattr(p.mode, 'name', p.mode))
    if was.strip() or mode_name == 'BIND':
        return 'kept bind %r' % was
    return 'bind ok'


def _destroy_stale_beat_pars(wrap):
    for name in ('Beatdrive', 'Flipdir', 'Pulsemode', 'Pulsediv', 'Pulsebeat', 'Pulseslot'):
        p = getattr(wrap.par, name, None)
        if p is None:
            continue
        try:
            p.destroy()
        except Exception:
            try:
                p.enable = False
            except Exception:
                pass


def setup_flowfields_beat(wrap):
    """Repair one particle_flowfields COMP instance."""
    info = []
    page = None
    for pg in wrap.customPages:
        if pg.name == 'Flowfields':
            page = pg
            break
    if page is None:
        page = wrap.appendCustomPage('Flowfields')

    if getattr(wrap.par, 'Beatmode', None) is None:
        m = page.appendMenu('Beatmode', label='Beat Sync')[0]
        m.menuNames = ['off', 'bpm', 'pulse']
        m.menuLabels = ['Off', 'BPM', 'Manual Beat']
        m.val = 'off'
        m.default = 'off'
        info.append('added Beatmode')
    else:
        wrap.par.Beatmode.label = 'Beat Sync'
        try:
            wrap.par.Beatmode.menuLabels = ['Off', 'BPM', 'Manual Beat']
        except Exception:
            pass

    if getattr(wrap.par, 'Beatdiv', None) is None:
        d = page.appendFloat('Beatdiv', label='Beat Division')[0]
        d.val = 1
        d.default = 1
        d.min = 0.25
        d.max = 8
        d.clampMin = True
        d.clampMax = True

    _destroy_stale_beat_pars(wrap)

    if getattr(wrap.par, 'Beat', None) is None:
        page.appendPulse('Beat', label='Beat')
        info.append('created Beat pulse')
    else:
        wrap.par.Beat.label = 'Beat'

    info.append(_clear_beat_bind(wrap))

    mot = wrap.op('flowfields/motion')
    p1 = wrap.op('flowfields/particles1')
    if not mot or not p1:
        info.append('MISSING motion/particles')
        return info

    gl = p1.op('glsl1')
    pm = p1.op('particleMotion')
    rm = mot.op('REPLACE_ME')
    tr = mot.op('trigger1')
    math2 = mot.op('math2')

    wrap.store('pulse_beat_t', -1e9)
    wrap.store('beat_btn_prev', False)
    wrap.store('pulse_flip_prev', 0.0)

    pm.text = MOTION
    try:
        gl.par.reinitshaders.pulse()
    except Exception:
        pass

    pc = mot.op('pulse_par') or mot.create('parameterCHOP', 'pulse_par')
    pc.par.ops = wrap.path
    pc.par.parameters = 'Beat'
    pc.par.custom = True
    if hasattr(pc.par, 'timeslice'):
        pc.par.timeslice = True

    beat_env = mot.op('beat_env') or mot.create('constantCHOP', 'beat_env')
    beat_env.par.const0name = 'trig'
    beat_env.par.const0value.expr = ENV_EXPR
    if hasattr(beat_env.par, 'timeslice'):
        beat_env.par.timeslice = True

    bus = mot.op('trig_bus') or mot.create('constantCHOP', 'trig_bus')
    bus.par.const0name = 'trig'
    bus.par.const0value.expr = (
        "(op('beat_env')[0] + op('pulse_par')[0]*0) if parent(3).par.Beatmode == 'pulse' "
        "else op('trigger1')[0]"
    )
    if hasattr(bus.par, 'timeslice'):
        bus.par.timeslice = True

    if tr:
        for ic in tr.inputConnectors:
            for c in list(ic.connections):
                c.disconnect()
        if rm:
            rm.outputConnectors[0].connect(tr.inputConnectors[0])
    if math2:
        for ic in math2.inputConnectors:
            for c in list(ic.connections):
                c.disconnect()
        bus.outputConnectors[0].connect(math2.inputConnectors[0])

    if rm:
        rm.par.frequency.expr = (
            "(op('/settings').par.Pulsebpm if op('/settings') else 120) / 60.0 / "
            "max(parent(3).par.Beatdiv, 0.25) "
            "if parent(3).par.Beatmode == 'bpm' else (0 if parent(3).par.Beatmode == 'pulse' else 1)"
        )
        if hasattr(rm.par, 'amp'):
            rm.par.amp.expr = "0 if parent(3).par.Beatmode == 'pulse' else 1"

    gl.par.vec1valuex.expr = "max(op('../motion/trig_bus')[0]*4.0, 0.7)"
    gl.par.vec4valuex.expr = (
        "(max((op('/settings').par.Pulsebpm if op('/settings') else 120)/40.0, 0.5) "
        "if parent(3).par.Beatmode != 'off' else 3.0)"
    )

    pe = wrap.op('parexec_reset') or wrap.create('parameterexecuteDAT', 'parexec_reset')
    pe.par.fromop = wrap.path
    try:
        pe.par.op = wrap.path
    except Exception:
        pass
    pe.par.pars = 'Reset Beat Beatmode'
    pe.par.onpulse = True
    pe.par.valuechange = True
    pe.par.active = True
    pe.text = PE_TEXT

    ex = wrap.op('pulse_frame_exec') or wrap.create('executeDAT', 'pulse_frame_exec')
    ex.par.framestart = True
    try:
        ex.par.active = True
    except Exception:
        pass
    ex.text = EX_TEXT

    ce = mot.op('pulse_chopexec') or mot.create('chopexecuteDAT', 'pulse_chopexec')
    ce.par.chop = pc
    ce.par.offtoon = True
    ce.par.valuechange = True
    ce.text = CE_TEXT

    try:
        pe.module._sync_beat_ui(wrap)
    except Exception:
        pass

    info.append(
        'ok Beatmode=%s bind=%r'
        % (
            wrap.par.Beatmode.eval(),
            str(getattr(wrap.par.Beat, 'bindExpr', '') or ''),
        )
    )
    return info


def _flowfields_candidates(root):
    out = []
    for o in root.findChildren(maxDepth=12):
        if not getattr(o, 'isCOMP', False):
            continue
        if not o.op('flowfields'):
            continue
        if hasattr(o.par, 'Videocolor') or o.name == 'particle_flowfields' or 'flowfield' in o.name.lower():
            out.append(o)
    return out


def apply_to_project(save_paths=None, root=None):
    """Apply fix to all flowfields instances; optionally save canonical tox."""
    if root is None:
        root = op('/project1')
    if root is None:
        raise RuntimeError('TouchDesigner root not found')

    results = []
    seen = set()
    for wrap in _flowfields_candidates(root):
        if wrap.path in seen:
            continue
        seen.add(wrap.path)
        results.append('=== ' + wrap.path)
        results.append('\n'.join(setup_flowfields_beat(wrap)))

    canonical = root.op('particle_flowfields')
    repo = _repo_root()
    if save_paths is None:
        save_paths = [os.path.join(repo, rel) for rel in DEFAULT_SAVE_PATHS]
    if canonical is not None:
        for path in save_paths:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                canonical.save(path)
                results.append('saved %s (%d bytes)' % (path, os.path.getsize(path)))
            except Exception as exc:
                results.append('save failed %s: %s' % (path, exc))

    return results


if __name__ == '__main__':
    for line in apply_to_project():
        print(line)
