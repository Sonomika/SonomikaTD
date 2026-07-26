"""Build / upgrade particle_fireworks.tox from flowfields base.

Each Manual Beat / kick rising edge launches a new firework burst.
"""
from __future__ import annotations

import os

ENV_EXPR = (
    "0 if (absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9)) < 0 else "
    "((absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9))/0.1) if "
    "(absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9)) < 0.1 else "
    "(max(0, 1.0 - ((absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9))-0.1)/0.45) "
    "if (absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9)) < 0.55 else 0)"
)

# Fireworks particle sim (same 3-target GLSL multi layout as flowfields).
# birth row (top UV strip) + aging buffer below.
# Per pulse: a few rocket lanes climb as thin trails, then one-shot into dense shells.
MOTION = r'''layout(location=0) out vec4 final_color0;
layout(location=1) out vec4 final_color1;
layout(location=2) out vec4 final_color2;

uniform vec3 resolution;
uniform vec4 colz;
uniform vec4 trigger; // x = pulse envelope 0..1  y = seconds
uniform vec4 centre;
uniform vec4 sim; // x=spread y=gravity z=videocolor

float res = resolution.x;
float increment = 1.0 / resolution.x;
float spread = max(sim.x, 0.35);
float gravity = mix(0.011, 0.030, clamp(sim.y, 0.0, 1.0));
float videocolor = sim.z;
float pulse = clamp(trigger.x, 0.0, 1.0);

float hash21(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

vec3 hash33(vec2 p) {
	return vec3(hash21(p), hash21(p + 19.7), hash21(p + 41.3));
}

vec3 fireworkHue(float seed) {
	float h = fract(seed * 7.13);
	vec3 c = 0.55 + 0.45 * cos(6.28318 * (vec3(0.0, 0.33, 0.67) + h));
	return mix(c, vec3(1.0, 0.88, 0.55), step(0.82, h));
}

vec3 videoColourAt(vec3 position) {
	vec2 vuv = fract(position.xy * 0.35 + 0.5);
	return texture(sTD2DInputs[7], vuv).rgb;
}

void main()
{
	vec3 position, velocity, color;

	if (vUV.t > 1.0 - increment)
	{
		// Cluster many particles onto a few rocket lanes so the climb reads as a line,
		// then the same cluster fills a dense shell on burst.
		vec2 id = vUV.st;
		float pulseId = floor(trigger.y * 17.0);
		float nRockets = 5.0;
		float lane = floor(hash21(id + pulseId * 0.13 + 3.1) * nRockets);
		float rocketSeed = lane + pulseId * 10.0;

		float launch = step(0.08, pulse) * step(hash21(id + 7.7), 0.88);

		float x = (hash21(vec2(rocketSeed, 1.7)) - 0.5) * 2.35 * spread;
		// hairline jitter so the trail has thickness without looking like a cloud
		x += (hash21(id + 8.2) - 0.5) * 0.028;
		position = vec3(x, -1.28, (hash21(id + 1.1) - 0.5) * 0.04);

		float climb = 0.88 + hash21(vec2(rocketSeed, 2.8)) * 0.70;
		velocity = vec3(
			(hash21(id + 4.4) - 0.5) * 0.035,
			climb + (hash21(id + 5.5) - 0.5) * 0.04,
			(hash21(id + 6.6) - 0.5) * 0.025
		);

		// Warm dim trail; keep lum < 1.2 so apex latch can one-shot the burst
		vec3 hue = fireworkHue(hash21(vec2(rocketSeed, 9.9)));
		color = mix(vec3(1.0, 0.72, 0.32), hue, 0.35) * (0.45 + 0.35 * pulse);

		position = mix(vec3(0.0, -20.0, 0.0), position, launch);
		velocity = mix(vec3(0.0), velocity, launch);
		color = mix(vec3(0.0), color, launch);

		if (videocolor > 0.5) {
			color = mix(color, videoColourAt(position), 0.2);
		}
	}
	else
	{
		float offx = (increment * res) + vUV.s;
		float offy = (float(offx > 1.0) / res) + vUV.t;
		position = texture(sTD2DInputs[1], vec2(offx, offy)).rgb;
		velocity = texture(sTD2DInputs[2], vec2(offx, offy)).rgb;
		color = texture(sTD2DInputs[5], vec2(offx, offy)).rgb;

		float alive = step(-10.0, position.y);
		float lum = max(color.r, max(color.g, color.b));
		float climbing = step(0.16, velocity.y) * alive;

		// One-shot burst: only while still a rocket (dim trail), near apex, high enough
		float canBurst = alive * step(0.04, lum) * (1.0 - step(1.15, lum));
		float atApex = step(velocity.y, 0.15) * step(-0.06, velocity.y) * step(0.18, position.y);
		float exploding = atApex * canBurst * (1.0 - climbing);

		vec2 id = vUV.st + position.xy * 0.71;
		vec3 rnd = hash33(id + floor(position.xy * 40.0)) * 2.0 - 1.0;
		// Chrysanthemum shell — filled sphere with slight upward bias
		float speed = 0.42 + hash21(id) * 1.35;
		vec3 burst = normalize(rnd + vec3(0.0001)) * speed;
		burst.y = abs(burst.y) * 0.72 + 0.10;

		velocity.y -= gravity;
		// hold the line while climbing; open hard on the explode frame
		velocity *= mix(0.9975, 0.90, exploding);
		velocity = mix(velocity, burst, exploding);

		vec3 shellHue = fireworkHue(hash21(id + 2.2)) * (1.55 + hash21(id + 0.4) * 0.55);
		color = mix(color, shellHue, exploding);
		color = mix(color, color * vec3(1.05, 0.9, 0.6), climbing * 0.12);

		position += velocity * 0.033 * alive;

		// sparks linger / fall; rockets stay brighter while climbing
		float fade = mix(0.991, 0.978, 1.0 - climbing);
		color *= fade;
		color = max(color, vec3(0.0));

		float kill = max(step(position.y, -1.55), step(max(color.r, max(color.g, color.b)), 0.014));
		kill *= (1.0 - exploding);
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


def _beat_signal(root):
	"""Float 0..1 from Beat UI / bind (kick). Parameter CHOP misses Pulse binds."""
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


def _repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, '..', '..'))


def apply_fireworks(wrap, save_paths=None):
    """Retarget a loaded flowfields-based COMP into fireworks."""
    info = []
    if wrap is None:
        return ['missing wrap']

    # params
    if hasattr(wrap.par, 'Credit'):
        wrap.par.Credit = 'Sonomika particle fireworks — pulse launches a burst'
    # reuse Spread as horizontal launch spread; Bright/Trail keep meaning
    if hasattr(wrap.par, 'Videocolor'):
        wrap.par.Videocolor.val = False
    if hasattr(wrap.par, 'Showsource'):
        wrap.par.Showsource.val = False
    if hasattr(wrap.par, 'Mix'):
        wrap.par.Mix.val = 1.0
    if hasattr(wrap.par, 'Particles'):
        try:
            if int(wrap.par.Particles.eval()) < 400:
                wrap.par.Particles.val = 480
        except Exception:
            pass

    # night sky clear color on black_bg if present
    bg = wrap.op('black_bg')
    if bg is not None:
        bg.par.colorr = 0.01
        bg.par.colorg = 0.02
        bg.par.colorb = 0.06

    wrap.store('pulse_beat_t', -1e9)
    wrap.store('pulse_flip_prev', 0.0)

    mot = wrap.op('flowfields/motion')
    p1 = wrap.op('flowfields/particles1')
    if mot is None or p1 is None:
        return ['missing motion/particles1']

    pm = p1.op('particleMotion')
    gl = p1.op('glsl1')
    if pm is None or gl is None:
        return ['missing particleMotion/glsl1']

    pm.text = MOTION
    try:
        gl.par.reinitshaders.pulse()
    except Exception:
        pass

    # trigger: envelope + time seconds on y
    mode = gl.par.vec1valuex.mode
    gl.par.vec1valuex.expr = "max(op('../motion/trig_bus')[0], 0.0)"
    gl.par.vec1valuex.mode = mode
    try:
        gl.par.vec1valuey.expr = 'absTime.seconds'
    except Exception:
        try:
            gl.par.vec1valuey.expr = "absTime.seconds"
        except Exception:
            pass

    # sim uniforms: spread, gravity(from Trail inverted-ish), videocolor
    # flowfields used vec4 sim - keep same slots via existing expressions where possible
    try:
        # x spread from Spread par
        gl.par.vec4valuex.expr = 'parent(3).par.Spread'
        # y gravity amount from Trail (higher trail => slower fade feel; map gently)
        gl.par.vec4valuey.expr = '1.0 - max(min(parent(3).par.Trail, 1), 0) * 0.5'
        gl.par.vec4valuez.expr = '1.0 if parent(3).par.Videocolor else 0.0'
    except Exception as e:
        info.append('sim expr ' + str(e))

    # beat bus same as flowfields
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
    bus.par.const0value.expr = (
        "(op('beat_env')[0] + op('pulse_par')[0]*0) if parent(3).par.Beatmode == 'pulse' "
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
    try:
        ce.par.offtoon = True
        ce.par.valuechange = True
    except Exception:
        pass
    ce.text = CE_TEXT

    # default beat mode pulse — required for Beat button / kick bind
    if hasattr(wrap.par, 'Beatmode'):
        try:
            wrap.par.Beatmode.val = 'pulse'
        except Exception:
            try:
                wrap.par.Beatmode = 'pulse'
            except Exception:
                pass
    if hasattr(wrap.par, 'Beat'):
        wrap.par.Beat.enable = True
    if hasattr(wrap.par, 'Beatdiv'):
        wrap.par.Beatdiv.enable = False
    try:
        pe.module._sync_beat_ui(wrap)
    except Exception:
        pass

    info.append('fireworks motion installed')

    if save_paths:
        wrap.par.externaltox = ''
        for path in save_paths:
            try:
                wrap.save(path)
                info.append('saved ' + path)
            except Exception as e:
                info.append('save fail ' + path + ' ' + str(e))
        wrap.par.externaltox = save_paths[0]
    return info
