"""Build particle_words.tox from particle_flowfields base.

Particles swarm and settle into letters / words from a Text parameter.
Beat pulse briefly scatters, then they reform.
"""
from __future__ import annotations

import os

ENV_EXPR = (
    "0 if (absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9)) < 0 else "
    "((absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9))/0.08) if "
    "(absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9)) < 0.08 else "
    "(max(0, 1.0 - ((absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9))-0.08)/0.35) "
    "if (absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9)) < 0.43 else 0)"
)

MOTION = r'''layout(location=0) out vec4 final_color0;
layout(location=1) out vec4 final_color1;
layout(location=2) out vec4 final_color2;

uniform vec3 resolution;
uniform vec4 colz;
uniform vec4 trigger; // x = beat scatter 0..1  y = seconds
uniform vec4 centre;
uniform vec4 sim; // x=form strength  y=turbulence  z=videocolor

float res = resolution.x;
float increment = 1.0 / resolution.x;
float form = max(sim.x, 0.5);
float turb = max(sim.y, 0.0);
float videocolor = sim.z;
float scatter = clamp(trigger.x, 0.0, 1.0);

float hash21(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

vec3 hash33(vec2 p) {
	return vec3(hash21(p), hash21(p + 19.7), hash21(p + 41.3));
}

// Text is ~2:1; map particle world (-1.3..1.3) onto the glyph frame
vec2 worldToTextUV(vec3 position) {
	return clamp(position.xy * vec2(0.38, 0.72) + 0.5, 0.0, 1.0);
}

vec3 textToWorld(vec2 uv) {
	return vec3((uv - 0.5) / vec2(0.38, 0.72), 0.0);
}

float textSampleRaw(vec2 uv) {
	vec4 t = texture(sTD2DInputs[8], clamp(uv, 0.0, 1.0));
	return max(t.r, max(t.g, max(t.b, t.a)));
}

// Thicken strokes so letter interiors are fillable / readable
float textSample(vec2 uv) {
	float e = 2.0 / 512.0;
	float m = 0.0;
	for (int j = -2; j <= 2; j++) {
		for (int i = -2; i <= 2; i++) {
			m = max(m, textSampleRaw(uv + vec2(float(i), float(j)) * e));
		}
	}
	return m;
}

vec2 textGrad(vec2 uv) {
	float e = 2.0 / 512.0;
	float dx = textSample(uv + vec2(e, 0.0)) - textSample(uv - vec2(e, 0.0));
	float dy = textSample(uv + vec2(0.0, e)) - textSample(uv - vec2(0.0, e));
	return vec2(dx, dy);
}

vec2 pickTextUV(vec2 id, float salt) {
	vec2 tuv = vec2(hash21(id + salt), hash21(id + salt + 1.7));
	for (int i = 0; i < 12; i++) {
		if (textSample(tuv) > 0.35) {
			return tuv;
		}
		tuv = fract(tuv * vec2(7.13, 5.79) + vec2(hash21(id + float(i) + salt), hash21(id * 1.9 + float(i))));
	}
	return tuv;
}

vec3 videoColourAt(vec3 position) {
	vec2 vuv = fract(position.xy * 0.35 + 0.5);
	return texture(sTD2DInputs[7], vuv).rgb;
}

vec3 baseColour(vec3 position, float inside) {
	vec3 ink = clamp(colz.rgb, 0.05, 1.0);
	ink = mix(ink * 0.35, ink * 1.35, inside);
	if (videocolor > 0.5) {
		return mix(ink, videoColourAt(position), 0.4);
	}
	return ink;
}

void main()
{
	vec3 position, velocity, color;

	if (vUV.t > 1.0 - increment)
	{
		vec2 id = vUV.st;
		vec2 tuv = pickTextUV(id, floor(trigger.y * 2.0) * 0.01);
		float hit = step(0.35, textSample(tuv));
		position = textToWorld(tuv);
		position.z = (hash21(id + 4.4) - 0.5) * 0.02;
		velocity = vec3(0.0);
		color = baseColour(position, hit);

		// Always birth onto the word (readable fill); beat adds extra scramble births
		float birth = hit * (0.65 + step(0.2, scatter) * 0.35);
		birth = max(birth, step(0.4, scatter) * step(hash21(id + 9.0), 0.5));
		position = mix(vec3(0.0, -20.0, 0.0), position, birth);
		velocity = mix(vec3(0.0), velocity, birth);
		color = mix(vec3(0.0), color, birth);
	}
	else
	{
		float offx = (increment * res) + vUV.s;
		float offy = (float(offx > 1.0) / res) + vUV.t;
		position = texture(sTD2DInputs[1], vec2(offx, offy)).rgb;
		velocity = texture(sTD2DInputs[2], vec2(offx, offy)).rgb;
		color = texture(sTD2DInputs[5], vec2(offx, offy)).rgb;

		float alive = step(-10.0, position.y);
		vec2 uv = worldToTextUV(position);
		float field = textSample(uv);
		vec2 g = textGrad(uv);
		float gLen = max(length(g), 0.0001);
		float inside = smoothstep(0.2, 0.55, field);

		// Hard home onto glyph when outside; freeze when inside
		vec2 homeUV = pickTextUV(vUV.st + position.xy, 3.3);
		vec3 home = textToWorld(homeUV);
		float snap = (1.0 - inside) * (0.55 + form * 0.25) * (1.0 - scatter);
		position.xy = mix(position.xy, home.xy, snap * alive);

		uv = worldToTextUV(position);
		field = textSample(uv);
		inside = smoothstep(0.2, 0.55, field);
		g = textGrad(uv);
		gLen = max(length(g), 0.0001);

		vec2 attract = (g / gLen) * mix(1.1, 0.05, inside) * form;
		vec3 turbVel = (texture(sTD2DInputs[0], fract(uv)).rgb - 0.5) * turb;

		vec3 targetVel = vec3(attract, 0.0);
		targetVel += turbVel * (0.05 + scatter * 1.8);
		targetVel.xy += (hash33(vUV.st + trigger.y).xy - 0.5) * scatter * 1.2;
		// Outside letters: yank back hard
		targetVel.xy += (home.xy - position.xy) * (1.0 - inside) * form * 0.8 * (1.0 - scatter);

		velocity = mix(velocity, targetVel, mix(0.45, 0.2, inside));
		velocity *= mix(0.82, 0.55, inside * (1.0 - scatter));
		velocity.z *= 0.85;

		position += velocity * 0.04 * alive;
		// Final pin: if still outside after move, snap again
		uv = worldToTextUV(position);
		field = textSample(uv);
		inside = smoothstep(0.25, 0.6, field);
		position.xy = mix(position.xy, home.xy, step(field, 0.25) * (1.0 - scatter) * 0.85 * alive);

		color = mix(color, baseColour(position, inside), 0.35);
		color *= mix(0.92, 0.995, inside);
		color = max(color, vec3(0.0));

		float kill = max(step(position.y, -1.7), step(max(color.r, max(color.g, color.b)), 0.025));
		// Cull persistent off-glyph particles (keeps silhouette clean)
		kill = max(kill, step(field, 0.12) * (1.0 - scatter) * step(hash21(vUV.st + position.xy), 0.35));
		position = mix(position, vec3(0.0, -20.0, 0.0), kill);
		velocity = mix(velocity, vec3(0.0), kill);
		color = mix(color, vec3(0.0), kill);
	}

	final_color0 = vec4(position, 1.0);
	final_color1 = vec4(velocity, 1.0);
	final_color2 = vec4(color, 1.0);
}
'''

PE_TEXT = '''def _sync_beat_ui(root):
	mode = str(root.par.Beatmode.eval()) if hasattr(root.par, 'Beatmode') else 'off'
	if hasattr(root.par, 'Beatdiv'):
		root.par.Beatdiv.enable = (mode == 'bpm')
	if hasattr(root.par, 'Beat'):
		root.par.Beat.enable = (mode == 'pulse')


def _sync_word_text(root):
	tt = root.op('word_text')
	if tt is None:
		p1 = root.op('flowfields/particles1')
		tt = p1.op('word_text') if p1 is not None else None
	if tt is None:
		return
	word = 'SONOMIKA'
	if hasattr(root.par, 'Word'):
		try:
			word = str(root.par.Word.eval())
		except Exception:
			word = str(root.par.Word)
	if not word.strip():
		word = 'SONOMIKA'
	tt.par.text = word
	size = 180.0
	if hasattr(root.par, 'Fontsize'):
		try:
			size = float(root.par.Fontsize.eval())
		except Exception:
			pass
	for pn in ('fontsizex', 'fontsizey'):
		p = getattr(tt.par, pn, None)
		if p is not None:
			try:
				p.val = size
			except Exception:
				pass


def onOffToOn(par):
	return


def onOnToOff(par):
	return


def onValueChange(par, prev):
	root = me.parent()
	if par.name == 'Beatmode':
		_sync_beat_ui(root)
	if par.name in ('Word', 'Fontsize'):
		_sync_word_text(root)
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


def _beat_signal(root):
	p = getattr(root.par, 'Beat', None)
	if p is None:
		return 0.0
	be = str(getattr(p, 'bindExpr', '') or '').strip()
	if be and str(getattr(p.mode, 'name', p.mode)) == 'BIND':
		try:
			if '.par.' in be and be.startswith('op('):
				path = be.split('op(', 1)[1]
				path = path.split(')', 1)[0].strip().strip("'").strip('"')
				pname = be.split('.par.', 1)[1].strip()
				src = op(path)
				if src is not None and hasattr(src.par, pname):
					return float(getattr(src.par, pname).eval())
		except Exception:
			pass
		try:
			return 1.0 if p.eval() else 0.0
		except Exception:
			return 0.0
	pc = root.op('flowfields/motion/pulse_par')
	cur = 0.0
	if pc is not None:
		try:
			if pc.numChans:
				cur = float(pc[0])
		except Exception:
			cur = 0.0
	try:
		if p.eval():
			cur = max(cur, 1.0)
	except Exception:
		pass
	return cur


def onFrameStart(frame):
	root = me.parent()
	if not hasattr(root.par, 'Beatmode'):
		return
	if str(root.par.Beatmode.eval()) != 'pulse':
		return
	cur = _beat_signal(root)
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
    r'tox\Factory\particle_words.tox',
    r'release\tox\particle_words.tox',
)


def _repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, '..', '..'))


def _ensure_word_params(wrap):
    page = None
    for pg in wrap.customPages:
        if pg.name.lower() in ('flowfields', 'words', 'word'):
            page = pg
            break
    if page is None:
        page = wrap.appendCustomPage('Words')

    if not hasattr(wrap.par, 'Word'):
        p = page.appendStr('Word', label='Word / Letters')
        p.val = 'SONOMIKA'
        p.default = 'SONOMIKA'
    else:
        try:
            wrap.par.Word.page = page
        except Exception:
            pass

    if not hasattr(wrap.par, 'Fontsize'):
        p = page.appendFloat('Fontsize', label='Font Size')
        p.normMin = 40
        p.normMax = 280
        p.min = 24
        p.max = 400
        p.default = 180
        p.val = 180
    if not hasattr(wrap.par, 'Form'):
        p = page.appendFloat('Form', label='Form Strength')
        p.normMin = 0
        p.normMax = 3
        p.min = 0
        p.max = 5
        p.default = 2.2
        p.val = 2.2


def _ensure_word_tops(p1, wrap):
    """Text lives on the WRAP (not inside particles1) so slot 128px cascades can't blank it."""
    tt = wrap.op('word_text') or wrap.create('textTOP', 'word_text')
    word = 'SONOMIKA'
    if hasattr(wrap.par, 'Word'):
        try:
            word = str(wrap.par.Word.eval()) or 'SONOMIKA'
        except Exception:
            word = 'SONOMIKA'
    size = 180.0
    if hasattr(wrap.par, 'Fontsize'):
        try:
            size = max(float(wrap.par.Fontsize.eval()), 120.0)
            wrap.par.Fontsize.val = size
        except Exception:
            pass

    tt.par.text = word
    for name, val in (
        ('fontsizex', size),
        ('fontsizey', size),
        ('resolutionw', 1024),
        ('resolutionh', 512),
        ('outputresolution', 'custom'),
        ('bgcolorr', 0),
        ('bgcolorg', 0),
        ('bgcolorb', 0),
        ('bgalpha', 1),
        ('fontcolorr', 1),
        ('fontcolorg', 1),
        ('fontcolorb', 1),
        ('fontalpha', 1),
    ):
        p = getattr(tt.par, name, None)
        if p is None:
            continue
        try:
            p.val = val
        except Exception:
            try:
                setattr(tt.par, name, val)
            except Exception:
                pass

    for pname in ('alignx', 'aligny'):
        p = getattr(tt.par, pname, None)
        if p is None:
            continue
        for val in ('center', 'Center', 1):
            try:
                p.val = val
                break
            except Exception:
                continue

    for font in ('Arial Black', 'Impact', 'Arial', 'Verdana'):
        try:
            tt.par.font = font
            break
        except Exception:
            continue
    try:
        tt.par.typeface = 'Bold'
    except Exception:
        pass

    fit = wrap.op('word_fit') or wrap.create('resolutionTOP', 'word_fit')
    try:
        fit.par.outputresolution = 'custom'
        fit.par.resolutionw = 1024
        fit.par.resolutionh = 512
    except Exception:
        pass
    for fitmode in ('fill', 'fitbest', 'fitoutside', 2, 1):
        try:
            fit.par.fit = fitmode
            break
        except Exception:
            continue

    try:
        tt.outputConnectors[0].connect(fit)
    except Exception:
        try:
            fit.inputConnectors[0].connect(tt)
        except Exception:
            pass

    # Proxy inside particles1 so relative paths stay simple if needed
    sel = p1.op('word_sel') or p1.create('selectTOP', 'word_sel')
    try:
        sel.par.top = fit.path
    except Exception:
        try:
            sel.par.select = fit.path
        except Exception:
            pass

    # Remove broken inner text TOPs that get crushed to 128px black in slots
    for dead in ('word_text', 'word_fit'):
        old = p1.op(dead)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass

    return fit


def apply_words(wrap, save_paths=None):
    info = []
    if wrap is None:
        return ['missing wrap']

    _ensure_word_params(wrap)

    if hasattr(wrap.par, 'Credit'):
        wrap.par.Credit = 'Sonomika particle words — particles form letters & words'
    if hasattr(wrap.par, 'Videocolor'):
        wrap.par.Videocolor.val = False
    if hasattr(wrap.par, 'Showsource'):
        wrap.par.Showsource.val = False
    if hasattr(wrap.par, 'Mix'):
        wrap.par.Mix.val = 1.0
    if hasattr(wrap.par, 'Fontsize'):
        try:
            if float(wrap.par.Fontsize.eval()) < 140:
                wrap.par.Fontsize.val = 180
        except Exception:
            pass
    if hasattr(wrap.par, 'Form'):
        try:
            wrap.par.Form.val = max(float(wrap.par.Form.eval()), 2.0)
        except Exception:
            pass
    if hasattr(wrap.par, 'Particles'):
        try:
            if int(wrap.par.Particles.eval()) < 480:
                wrap.par.Particles.val = 640
            else:
                wrap.par.Particles.val = max(int(wrap.par.Particles.eval()), 640)
        except Exception:
            pass
    if hasattr(wrap.par, 'Bright'):
        try:
            wrap.par.Bright.val = max(float(wrap.par.Bright.eval()), 3.5)
        except Exception:
            pass
    if hasattr(wrap.par, 'Pointsize'):
        try:
            wrap.par.Pointsize.val = max(float(wrap.par.Pointsize.eval()), 2.2)
        except Exception:
            pass
    if hasattr(wrap.par, 'Spread'):
        try:
            # Spread maps to residual turbulence — keep low for readable type
            wrap.par.Spread.val = min(float(wrap.par.Spread.eval()), 0.35)
        except Exception:
            pass

    bg = wrap.op('black_bg')
    if bg is not None:
        bg.par.colorr = 0.01
        bg.par.colorg = 0.015
        bg.par.colorb = 0.04

    wrap.store('pulse_beat_t', -1e9)
    wrap.store('pulse_flip_prev', 0.0)

    mot = wrap.op('flowfields/motion')
    p1 = wrap.op('flowfields/particles1')
    if mot is None or p1 is None:
        return ['missing motion/particles1']

    word_fit = _ensure_word_tops(p1, wrap)
    word_sel = p1.op('word_sel')

    pm = p1.op('particleMotion')
    gl = p1.op('glsl1')
    if pm is None or gl is None:
        return ['missing particleMotion/glsl1']

    pm.text = MOTION

    # Wire via selectTOP inside particles1 (direct wrap→glsl connect is rejected)
    try:
        if len(gl.inputConnectors) > 8 and word_sel is not None:
            try:
                gl.inputConnectors[8].disconnect()
            except Exception:
                pass
            gl.inputConnectors[8].connect(word_sel)
            info.append('wired word_sel -> glsl in8')
    except Exception as e:
        info.append('wire in8 ' + str(e))

    gl.par.vec1valuex.expr = "op('../motion/trig_bus')[0]"
    try:
        gl.par.vec1valuey.expr = 'absTime.seconds'
    except Exception:
        pass

    try:
        gl.par.vec4valuex.expr = 'parent(3).par.Form'
        # very low idle turbulence from Spread
        gl.par.vec4valuey.expr = 'max(0.02, min(parent(3).par.Spread, 1.0) * 0.12)'
        gl.par.vec4valuez.expr = '1.0 if parent(3).par.Videocolor else 0.0'
    except Exception as e:
        info.append('sim expr ' + str(e))

    pc = mot.op('pulse_par') or mot.create('parameterCHOP', 'pulse_par')
    pc.par.ops = wrap.path
    try:
        pc.par.parameters = 'Beat'
        pc.par.custom = True
    except Exception:
        pass
    if hasattr(pc.par, 'timeslice'):
        pc.par.timeslice = True

    beat_env = mot.op('beat_env') or mot.create('constantCHOP', 'beat_env')
    beat_env.par.const0name = 'trig'
    beat_env.par.const0value.expr = ENV_EXPR
    if hasattr(beat_env.par, 'timeslice'):
        beat_env.par.timeslice = True

    bus = mot.op('trig_bus') or mot.create('constantCHOP', 'trig_bus')
    bus.par.const0name = 'trig'
    # Beat scatter only — idle must be 0 so letters stay locked
    bus.par.const0value.expr = (
        "(op('beat_env')[0]) if parent(3).par.Beatmode == 'pulse' "
        "else op('trigger1')[0]"
    )
    if hasattr(bus.par, 'timeslice'):
        bus.par.timeslice = True

    pe = wrap.op('parexec_reset') or wrap.create('parameterexecuteDAT', 'parexec_reset')
    pe.par.fromop = wrap.path
    try:
        pe.par.op = wrap.path
    except Exception:
        pass
    pe.par.pars = 'Reset Beat Beatmode Word Fontsize'
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
    try:
        ce.par.offtoon = True
        ce.par.valuechange = True
    except Exception:
        pass
    ce.text = CE_TEXT

    if hasattr(wrap.par, 'Beatmode'):
        try:
            wrap.par.Beatmode.val = 'pulse'
        except Exception:
            pass
    if hasattr(wrap.par, 'Beat'):
        wrap.par.Beat.enable = True
    if hasattr(wrap.par, 'Beatdiv'):
        wrap.par.Beatdiv.enable = False

    try:
        pe.module._sync_beat_ui(wrap)
        pe.module._sync_word_text(wrap)
    except Exception as e:
        info.append('sync ' + str(e))

    info.append('words motion installed')

    if save_paths:
        wrap.par.externaltox = ''
        for path in save_paths:
            try:
                wrap.save(path)
                info.append('saved ' + path)
            except Exception as e:
                info.append('save fail ' + path + ' ' + str(e))
        wrap.par.externaltox = save_paths[0].replace('\\', '/')
        # prefer repo-relative
        try:
            wrap.par.externaltox = 'tox/factory/particle_words.tox'
        except Exception:
            pass
    return info


def apply_to_project(save=True):
    root = op('/project1')
    wrap = root.op('particle_words')
    if wrap is None:
        return ['missing /project1/particle_words — load flowfields tox first']
    paths = None
    if save:
        base = _repo_root()
        paths = [os.path.join(base, p) for p in DEFAULT_SAVE_PATHS]
    return apply_words(wrap, paths)
