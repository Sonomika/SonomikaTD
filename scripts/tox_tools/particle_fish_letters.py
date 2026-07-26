"""Build particle_fish_letters.tox from particle_flowfields.

Tiny particles swim slowly inside a Word silhouette (letter itself invisible).
Beat / kick rising edge = school swims away, then reforms.
Port of sandbox/particle_words fish-in-letters behaviour.
"""
from __future__ import annotations

import os

ENV_EXPR = (
    "0 if (absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9)) < 0 else "
    "((absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9))/0.12) if "
    "(absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9)) < 0.12 else "
    "(max(0, 1.0 - ((absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9))-0.12)/0.9) "
    "if (absTime.seconds - parent(3).fetch('pulse_beat_t', -1e9)) < 1.02 else 0)"
)

# Slow interior swim. Input 8 = wrap-level word mask via word_sel.
MOTION = r'''layout(location=0) out vec4 final_color0;
layout(location=1) out vec4 final_color1;
layout(location=2) out vec4 final_color2;

uniform vec3 resolution;
uniform vec4 colz;
uniform vec4 trigger; // x = scatter envelope  y = seconds
uniform vec4 centre;
uniform vec4 sim; // x=swim  y=meander  z=videocolor

float res = resolution.x;
float increment = 1.0 / resolution.x;
float swim = clamp(sim.x, 0.05, 2.0);
float meander = clamp(sim.y, 0.0, 1.0);
float videocolor = sim.z;
float scatter = clamp(trigger.x, 0.0, 1.0);
float tsec = trigger.y;

float hash21(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

vec3 hash33(vec2 p) {
	return vec3(hash21(p), hash21(p + 19.7), hash21(p + 41.3));
}

vec2 worldToTextUV(vec3 position) {
	return clamp(position.xy * vec2(0.36, 0.70) + 0.5, 0.0, 1.0);
}

vec3 textToWorld(vec2 uv) {
	return vec3((uv - 0.5) / vec2(0.36, 0.70), 0.0);
}

float textSampleRaw(vec2 uv) {
	vec4 s = texture(sTD2DInputs[8], clamp(uv, 0.0, 1.0));
	return max(s.r, max(s.g, max(s.b, s.a)));
}

float textSample(vec2 uv) {
	// slight thicken so thin glyph strokes still hold fish
	float e = 1.5 / 512.0;
	float m = 0.0;
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
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

vec2 pickInteriorUV(vec2 id, float salt) {
	vec2 uv = vec2(hash21(id + salt), hash21(id + salt + 2.1));
	for (int i = 0; i < 16; i++) {
		if (textSample(uv) > 0.55) return uv;
		uv = fract(uv * vec2(6.17, 4.93) + vec2(hash21(id + float(i) + salt), hash21(id * 1.7 + float(i))));
	}
	return uv;
}

vec3 baseColour(vec3 position, float seed) {
	vec3 ink = clamp(colz.rgb, 0.15, 1.0);
	// soft fish-school hues
	vec3 tint = 0.55 + 0.45 * cos(6.28318 * (vec3(0.0, 0.33, 0.67) + seed * 3.0));
	ink = mix(ink, tint, 0.45);
	if (videocolor > 0.5) {
		vec2 vuv = fract(position.xy * 0.35 + 0.5);
		ink = mix(ink, texture(sTD2DInputs[7], vuv).rgb, 0.4);
	}
	return ink;
}

void main()
{
	vec3 position, velocity, color;

	if (vUV.t > 1.0 - increment)
	{
		vec2 id = vUV.st;
		float seed = hash21(id + 3.3);
		vec2 uv = pickInteriorUV(id, floor(tsec * 0.15));
		float hit = step(0.55, textSample(uv));
		position = textToWorld(uv);
		position.z = (seed - 0.5) * 0.06;

		float ang = seed * 6.28318;
		float cruise = 0.015 + swim * 0.035;
		velocity = vec3(cos(ang), sin(ang), 0.0) * cruise;
		color = baseColour(position, seed) * (0.7 + 0.3 * seed);

		// denser refill so the word reads without a visible letter plate
		float birth = hit * step(hash21(id + 11.0), mix(0.12, 0.28, 1.0 - scatter));
		birth = max(birth, hit * step(0.35, scatter) * step(hash21(id + 9.0), 0.15));
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
		float seed = hash21(vUV.st + 1.7);
		vec2 uv = worldToTextUV(position);
		float dens = textSample(uv);
		vec2 g = textGrad(uv);
		float gLen = max(length(g), 1e-5);
		vec2 nrm = g / gLen;

		float phase = tsec * (0.55 + seed * 0.7) + seed * 12.0;
		float cruise = 0.012 + swim * (0.04 + seed * 0.025);
		float heading = atan(velocity.y, velocity.x + 1e-5);
		float turnNoise = sin(phase) * 0.35 + sin(phase * 0.37 + seed) * 0.2;
		float ang = heading + turnNoise * (0.015 + swim * 0.02) * meander;

		vec2 desire = vec2(cos(ang), sin(ang)) * cruise;

		// soft stay-inside: glide along walls
		if (dens < 0.62) {
			float push = (0.62 - dens) * (0.035 + swim * 0.02);
			vec2 tang = vec2(-nrm.y, nrm.x);
			float along = dot(desire, tang);
			desire = tang * along * 0.85 + nrm * push;
		}

		desire += vec2(sin(seed * 12.0 + tsec * 0.35), cos(seed * 9.0 + tsec * 0.28)) * 0.004 * meander;

		// Beat: school swims away (letter dissolves into leaving fish)
		vec2 awayDir = normalize(position.xy + vec2(1e-4) + (hash33(vUV.st).xy - 0.5) * 0.4);
		desire = mix(desire, awayDir * (0.08 + swim * 0.12), scatter);
		desire += (hash33(vUV.st + tsec).xy - 0.5) * scatter * 0.05;

		float turn = 0.08 + swim * 0.04;
		velocity.xy = mix(velocity.xy, desire, turn);
		velocity.z = mix(velocity.z, sin(tsec * 0.7 + seed * 9.0) * 0.01, 0.05);

		float spd = length(velocity.xy);
		float maxSpd = mix(0.025 + swim * 0.05, 0.14 + swim * 0.1, scatter);
		if (spd > maxSpd) velocity.xy *= maxSpd / max(spd, 1e-5);

		position += velocity * alive;

		uv = worldToTextUV(position);
		dens = textSample(uv);
		if (dens < 0.22 && scatter < 0.2) {
			g = textGrad(uv);
			gLen = max(length(g), 1e-5);
			position.xy += (g / gLen) * 0.03;
			velocity.xy *= 0.5;
		}
		if (dens < 0.08 && scatter < 0.15) {
			vec2 home = pickInteriorUV(vUV.st, seed + floor(tsec));
			position.xy = mix(position.xy, textToWorld(home).xy, 0.4);
			velocity.xy *= 0.2;
		}

		float inside = smoothstep(0.2, 0.6, dens);
		color = mix(color, baseColour(position, seed), 0.08);
		color *= mix(0.96, 0.997, mix(inside, 0.5, scatter));
		color = max(color, vec3(0.0));

		float kill = max(step(position.y, -1.7), step(max(color.r, max(color.g, color.b)), 0.02));
		// far after swim-away
		kill = max(kill, step(2.8, length(position.xy)) * step(0.3, scatter));
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
		root.store('fish_need_respawn', True)
	return


def onPulse(par):
	root = me.parent()
	if par.name == 'Beat':
		if str(root.par.Beatmode.eval()) == 'pulse':
			root.store('pulse_beat_t', absTime.seconds - 0.05)
			root.store('fish_need_respawn', True)
		return
	if par.name != 'Reset':
		return
	root.store('fish_need_respawn', True)
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
	# Keep word mask alive under slot render-scale (can crush TOPs to 128px black)
	tt = root.op('word_text')
	fit = root.op('word_fit')
	for o in (tt, fit):
		if o is None:
			continue
		try:
			o.store('sonomika_keep_custom_res', True)
		except Exception:
			pass
		try:
			if int(getattr(o, 'width', 0) or 0) < 256:
				o.par.outputresolution = 'custom'
				o.par.resolutionw = 1024
				o.par.resolutionh = 512
				if hasattr(o.par, 'resmult'):
					o.par.resmult = False
		except Exception:
			pass
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

FISH_DRAW = r'''# Fish-in-letters drawer (sandbox port). Samples word_fit; ignores broken 3D particle path.
import numpy as np

def _root():
	return me.parent()

def _ensure_state(root, n):
	st = root.fetch('fish_state', None)
	need = st is None or len(st.get('x', [])) != n
	if not need:
		return st
	rng = np.random.RandomState(7)
	st = {
		'x': rng.uniform(-0.4, 0.4, n).astype(np.float32),
		'y': rng.uniform(-0.2, 0.2, n).astype(np.float32),
		'vx': rng.uniform(-0.05, 0.05, n).astype(np.float32),
		'vy': rng.uniform(-0.05, 0.05, n).astype(np.float32),
		'seed': rng.rand(n).astype(np.float32),
		'phase': rng.uniform(0, 6.28318, n).astype(np.float32),
		'away': np.zeros(n, dtype=np.float32),
		't': 0.0,
	}
	root.store('fish_state', st)
	return st

def _mask_and_interiors(root):
	fit = root.op('word_fit')
	if fit is None:
		return None, None
	try:
		arr = np.asarray(fit.numpyArray(delayed=False), dtype=np.float32)
	except Exception:
		return None, None
	if arr.ndim == 3:
		lum = np.max(arr[..., :3], axis=2)
	else:
		lum = arr
	# TD arrays are often (h,w)
	ys, xs = np.where(lum > 0.45)
	if len(xs) < 8:
		ys, xs = np.where(lum > 0.2)
	if len(xs) < 1:
		return lum, None
	h, w = lum.shape
	# map pixel -> normalized letter space roughly matching sandbox [-2.7..2.7] x [-1.2..1.2]
	wx = (xs.astype(np.float32) / max(w - 1, 1) - 0.5) * 5.4
	wy = (0.5 - ys.astype(np.float32) / max(h - 1, 1)) * 2.35
	return lum, np.stack([wx, wy], axis=1)

def onSetupParameters(scriptOp):
	page = scriptOp.appendCustomPage('Fish')
	return

def onCook(scriptOp):
	root = _root()
	try:
		n = int(max(80, min(int(getattr(root.par, 'Particles', None) and root.par.Particles.eval() or 720), 1600)))
	except Exception:
		n = 720
	try:
		swim = float(root.par.Swim.eval()) if hasattr(root.par, 'Swim') else 0.35
	except Exception:
		swim = 0.35
	try:
		scatter = float(root.op('flowfields/motion/trig_bus')[0]) if root.op('flowfields/motion/trig_bus') else 0.0
	except Exception:
		scatter = 0.0

	# resolution: prefer readable letter canvas
	W = 960
	H = 540
	try:
		scriptOp.par.outputresolution = 'custom'
		scriptOp.par.resolutionw = W
		scriptOp.par.resolutionh = H
		scriptOp.par.resmult = False
		scriptOp.store('sonomika_keep_custom_res', True)
	except Exception:
		pass

	lum, interiors = _mask_and_interiors(root)
	st = _ensure_state(root, n)
	# respawn into interiors when word changes / first cook
	if interiors is not None and (root.fetch('fish_need_respawn', True) or scatter > 0.55):
		idx = np.random.randint(0, len(interiors), size=n)
		st['x'][:] = interiors[idx, 0]
		st['y'][:] = interiors[idx, 1]
		ang = np.random.uniform(0, 6.28318, n).astype(np.float32)
		spd = (0.03 + swim * 0.05) * (0.6 + st['seed'])
		if scatter > 0.55:
			st['vx'][:] = np.cos(ang) * (0.35 + swim)
			st['vy'][:] = np.sin(ang) * (0.25 + swim * 0.7)
			st['away'][:] = 1.0
		else:
			st['vx'][:] = np.cos(ang) * spd
			st['vy'][:] = np.sin(ang) * spd
			st['away'][:] = 0.0
		root.store('fish_need_respawn', False)

	dt = 1.0 / 60.0
	st['t'] = float(st['t']) + dt
	t = st['t']
	x = st['x']; y = st['y']; vx = st['vx']; vy = st['vy']
	seed = st['seed']; phase = st['phase']; away = st['away']

	# sample density via nearest interior distance heuristic
	if interiors is not None and len(interiors) > 0:
		# subsample interiors for speed
		step = max(1, len(interiors) // 800)
		ins = interiors[::step]
		# vectorized nearest (chunked)
		desire_x = np.zeros(n, dtype=np.float32)
		desire_y = np.zeros(n, dtype=np.float32)
		for i in range(n):
			phase[i] += dt * (0.55 + float(seed[i]) * 0.7)
			if away[i] > 0.5 or scatter > 0.25:
				wag = np.sin(t * 2.0 + phase[i]) * 0.08
				vx[i] += np.cos(phase[i] + t * 0.3) * 0.03 * dt
				vy[i] += np.sin(phase[i] * 1.2 + t * 0.2) * 0.025 * dt
				vx[i] += wag * dt
				vx[i] *= 0.992
				vy[i] *= 0.992
				x[i] += vx[i] * dt * 1.8
				y[i] += vy[i] * dt * 1.8
				continue
			d = (ins[:, 0] - x[i]) ** 2 + (ins[:, 1] - y[i]) ** 2
			j = int(np.argmin(d))
			tx, ty = float(ins[j, 0]), float(ins[j, 1])
			dx, dy = tx - x[i], ty - y[i]
			dist = (dx * dx + dy * dy) ** 0.5 + 1e-5
			# cruise with gentle wander
			cruise = 0.035 + swim * (0.45 + float(seed[i]) * 0.25)
			heading = np.arctan2(vy[i], vx[i] + 1e-5)
			heading += np.sin(phase[i]) * 0.35 * dt
			dxs = np.cos(heading) * cruise
			dys = np.sin(heading) * cruise
			# keep near letter mass
			if dist > 0.12:
				dxs += (dx / dist) * min(0.2, dist) * 1.4
				dys += (dy / dist) * min(0.2, dist) * 1.4
			turn = 1.1
			vx[i] += (dxs - vx[i]) * min(1.0, turn * dt)
			vy[i] += (dys - vy[i]) * min(1.0, turn * dt)
			spd = (vx[i] * vx[i] + vy[i] * vy[i]) ** 0.5
			max_spd = 0.06 + swim * 0.45
			if spd > max_spd:
				vx[i] *= max_spd / spd
				vy[i] *= max_spd / spd
			x[i] += vx[i] * dt
			y[i] += vy[i] * dt
			# hard rescue if lost
			if dist > 2.2:
				x[i], y[i] = tx, ty
				vx[i] *= 0.2
				vy[i] *= 0.2
	else:
		x *= 0.99
		y *= 0.99

	# draw
	img = np.zeros((H, W, 4), dtype=np.float32)
	# map world -> pixels
	px = ((x / 5.4) + 0.5) * (W - 1)
	py = (0.5 - (y / 2.35)) * (H - 1)
	# tiny bright dots (school)
	rad = 1
	try:
		ps = float(root.par.Pointsize.eval())
		rad = max(1, min(3, int(round(ps * 0.35))))
	except Exception:
		pass
	cols = np.stack([
		0.35 + 0.55 * np.cos(seed * 6.28),
		0.55 + 0.4 * np.cos(seed * 6.28 + 2.1),
		0.85 + 0.15 * np.cos(seed * 6.28 + 4.2),
	], axis=1).astype(np.float32)
	for i in range(n):
		xi = int(px[i]); yi = int(py[i])
		if xi < 1 or yi < 1 or xi >= W - 1 or yi >= H - 1:
			continue
		c = cols[i]
		for oy in range(-rad, rad + 1):
			for ox in range(-rad, rad + 1):
				if ox * ox + oy * oy > rad * rad + 1:
					continue
				yy = yi + oy; xx = xi + ox
				img[yy, xx, 0] = min(1.0, img[yy, xx, 0] + c[0])
				img[yy, xx, 1] = min(1.0, img[yy, xx, 1] + c[1])
				img[yy, xx, 2] = min(1.0, img[yy, xx, 2] + c[2])
				img[yy, xx, 3] = 1.0
	scriptOp.copyNumpyArray(img)
	root.store('fish_state', st)
'''


DEFAULT_SAVE_PATHS = (
    r'tox\Factory\particle_fish_letters.tox',
    r'release\tox\particle_fish_letters.tox',
)


def _repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, '..', '..'))


def _ensure_word_params(wrap):
    page = None
    for pg in wrap.customPages:
        if pg.name.lower() in ('flowfields', 'words', 'fish'):
            page = pg
            break
    if page is None:
        page = wrap.appendCustomPage('Fish Letters')

    if not hasattr(wrap.par, 'Word'):
        p = page.appendStr('Word', label='Word / Letters')
        p.val = 'SONOMIKA'
        p.default = 'SONOMIKA'
    if not hasattr(wrap.par, 'Fontsize'):
        p = page.appendFloat('Fontsize', label='Font Size')
        p.min = 40
        p.max = 320
        p.normMin = 60
        p.normMax = 240
        p.default = 180
        p.val = 180
    if not hasattr(wrap.par, 'Swim'):
        p = page.appendFloat('Swim', label='Swim Speed')
        p.min = 0
        p.max = 2
        p.normMin = 0
        p.normMax = 1.5
        p.default = 0.35
        p.val = 0.35


def _ensure_word_tops(p1, wrap):
    """Word mask on WRAP. Recreate if resolution was crushed by slot render-scale."""
    # Destroy broken/crushed mask nodes (slot scale can freeze them at 128px black)
    for name in ('word_text', 'word_fit'):
        old = wrap.op(name)
        if old is None:
            continue
        crushed = False
        try:
            crushed = int(old.width) < 256 or int(old.height) < 128
        except Exception:
            crushed = True
        if crushed:
            try:
                old.destroy()
            except Exception:
                pass

    tt = wrap.op('word_text') or wrap.create('textTOP', 'word_text')
    try:
        tt.store('sonomika_keep_custom_res', True)
    except Exception:
        pass

    word = 'SONOMIKA'
    if hasattr(wrap.par, 'Word'):
        try:
            word = str(wrap.par.Word.eval()) or 'SONOMIKA'
        except Exception:
            word = 'SONOMIKA'
    size = 180.0
    if hasattr(wrap.par, 'Fontsize'):
        try:
            size = max(float(wrap.par.Fontsize.eval()), 100.0)
        except Exception:
            pass

    tt.par.text = word
    for name, val in (
        ('fontsizex', size),
        ('fontsizey', size),
        ('resolutionw', 1024),
        ('resolutionh', 512),
        ('outputresolution', 'custom'),
        ('resmult', False),
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
        fit.store('sonomika_keep_custom_res', True)
    except Exception:
        pass
    try:
        fit.par.outputresolution = 'custom'
        fit.par.resolutionw = 1024
        fit.par.resolutionh = 512
        fit.par.resmult = False
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

    sel = p1.op('word_sel') or p1.create('selectTOP', 'word_sel')
    try:
        sel.par.top = fit.path
    except Exception:
        pass

    for dead in ('word_text', 'word_fit'):
        old = p1.op(dead)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass

    return fit, sel


def apply_fish_letters(wrap, save_paths=None):
    info = []
    if wrap is None:
        return ['missing wrap']

    _ensure_word_params(wrap)

    if hasattr(wrap.par, 'Credit'):
        wrap.par.Credit = 'Sonomika fish letters — tiny particles swim inside words'
    if hasattr(wrap.par, 'Videocolor'):
        wrap.par.Videocolor.val = False
    if hasattr(wrap.par, 'Showsource'):
        wrap.par.Showsource.val = False
    if hasattr(wrap.par, 'Mix'):
        wrap.par.Mix.val = 1.0
    if hasattr(wrap.par, 'Particles'):
        try:
            wrap.par.Particles.val = max(int(wrap.par.Particles.eval()), 720)
        except Exception:
            pass
    if hasattr(wrap.par, 'Pointsize'):
        try:
            # Camera sits far (~tz 33); tiny values vanish. Keep readable school dots.
            wrap.par.Pointsize.min = 0.5
            wrap.par.Pointsize.normMin = 0.5
            wrap.par.Pointsize.val = 4.5
        except Exception:
            pass
    if hasattr(wrap.par, 'Bright'):
        try:
            wrap.par.Bright.val = max(float(wrap.par.Bright.eval()), 4.0)
        except Exception:
            pass
    if hasattr(wrap.par, 'Trail'):
        try:
            wrap.par.Trail.val = 0.55
        except Exception:
            pass
    if hasattr(wrap.par, 'Spread'):
        try:
            wrap.par.Spread.val = 0.55
        except Exception:
            pass
    if hasattr(wrap.par, 'Swim'):
        try:
            wrap.par.Swim.val = 0.35
        except Exception:
            pass
    if hasattr(wrap.par, 'Fontsize'):
        try:
            if float(wrap.par.Fontsize.eval()) < 120:
                wrap.par.Fontsize.val = 180
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

    _fit, word_sel = _ensure_word_tops(p1, wrap)

    pm = p1.op('particleMotion')
    gl = p1.op('glsl1')
    if pm is None or gl is None:
        return ['missing particleMotion/glsl1']

    pm.text = MOTION

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
        gl.par.vec4valuex.expr = 'parent(3).par.Swim'
        gl.par.vec4valuey.expr = 'max(0.25, min(parent(3).par.Spread, 1.5))'
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
    pe.par.pars = 'Reset Beat Beatmode Word Fontsize Swim'
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

    # reset feedbacks so fish birth into the word cleanly
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

    info.append('fish letters motion installed')

    # Sandbox-style CPU fish drawer — works in performance slots where 3D particles collapse
    try:
        wrap.store('fish_need_respawn', True)
        draw = wrap.op('fish_draw') or wrap.create('scriptTOP', 'fish_draw')
        tdat = wrap.op('fish_draw_callbacks') or wrap.create('textDAT', 'fish_draw_callbacks')
        tdat.text = FISH_DRAW
        try:
            draw.par.callbacks = tdat.path
        except Exception:
            try:
                draw.text = FISH_DRAW
            except Exception:
                pass
        for o in (draw,):
            try:
                o.store('sonomika_keep_custom_res', True)
                o.par.outputresolution = 'custom'
                o.par.resolutionw = 960
                o.par.resolutionh = 540
                o.par.resmult = False
            except Exception:
                pass

        fit = wrap.op('fish_fit') or wrap.create('resolutionTOP', 'fish_fit')
        try:
            fit.store('sonomika_keep_custom_res', True)
        except Exception:
            pass
        # Slot out is often forced ~128; fill-fit keeps the word readable
        try:
            fit.par.outputresolution = 'useinput'
            fit.par.resmult = False
        except Exception:
            pass
        for fitmode in ('fill', 'fitbest', 'fitoutside', 2, 1):
            try:
                fit.par.fit = fitmode
                break
            except Exception:
                continue
        try:
            while fit.inputs:
                fit.inputConnectors[0].disconnect()
        except Exception:
            pass
        try:
            fit.inputConnectors[0].connect(draw)
        except Exception:
            try:
                draw.outputConnectors[0].connect(fit)
            except Exception:
                pass

        # Recreate out1 if it is a dead/black node (common after slot scale fights)
        out = wrap.op('out1')
        rebuild_out = False
        if out is not None:
            try:
                import numpy as _np
                mx = float(_np.asarray(out.numpyArray(delayed=False)).max())
                if mx <= 0.0 and float(_np.asarray(draw.numpyArray(delayed=False)).max()) > 0.1:
                    rebuild_out = True
            except Exception:
                rebuild_out = False
        if out is None or rebuild_out:
            if out is not None:
                try:
                    out.destroy()
                except Exception:
                    pass
            out = wrap.create('outTOP', 'out1')
            info.append('recreated out1')
        try:
            while out.inputs:
                out.inputConnectors[0].disconnect()
        except Exception:
            pass
        try:
            fit.outputConnectors[0].connect(out.inputConnectors[0])
        except Exception:
            try:
                out.inputConnectors[0].connect(fit)
            except Exception:
                pass

        sf = wrap.op('select_flow')
        if sf is not None and hasattr(sf.par, 'top'):
            try:
                sf.par.top = draw.path
            except Exception:
                pass
        info.append('fish_draw -> fish_fit -> out1')
    except Exception as e:
        info.append('fish_draw fail ' + str(e))

    if save_paths:
        wrap.par.externaltox = ''
        for path in save_paths:
            try:
                wrap.save(path)
                info.append('saved ' + path)
            except Exception as e:
                info.append('save fail ' + path + ' ' + str(e))
        try:
            wrap.par.externaltox = 'tox/factory/particle_fish_letters.tox'
        except Exception:
            wrap.par.externaltox = save_paths[0].replace('\\', '/')
    return info


def apply_to_project(save=True):
    root = op('/project1')
    wrap = root.op('particle_fish_letters')
    if wrap is None:
        return ['missing /project1/particle_fish_letters']
    paths = None
    if save:
        base = _repo_root()
        paths = [os.path.join(base, p) for p in DEFAULT_SAVE_PATHS]
    return apply_fish_letters(wrap, paths)
