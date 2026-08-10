"""Build the Human/Object Box Tracker TOX. Run inside TouchDesigner."""
import os

ROOT = os.path.abspath(os.path.join(project.folder, '..')) if os.path.basename(project.folder).lower() == 'production' else project.folder
OUTS = (
    os.path.join(ROOT, 'production', 'tox', 'human_object_tracker', 'human_object_tracker.tox'),
    os.path.join(ROOT, 'production', 'tox premium', 'Released', 'human_object_tracker.tox'),
)

CALLBACKS = r'''import os
import cv2
import numpy as np

_net = None
_net_key = ''
_face_detector = None
_face_key = ''
_tracks = []
_frame = 0
_last_src_td = None
_last_mask_td = None

def _model_paths(comp):
    candidates = [
        os.path.join(project.folder, 'assets', 'human_object_tracker', 'model'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(comp.par.externaltox.eval() or ''))), 'assets', 'human_object_tracker', 'model'),
    ]
    for root in candidates:
        pb = os.path.join(root, 'ssd_mobilenet_v1_coco_2017_11_17', 'frozen_inference_graph.pb')
        cfg = os.path.join(root, 'ssd_mobilenet_v1_coco.pbtxt')
        if os.path.isfile(pb) and os.path.isfile(cfg): return pb, cfg
    return '', ''

def _load(comp):
    global _net, _net_key
    pb, cfg = _model_paths(comp)
    key = pb + '|' + cfg
    if _net is None or key != _net_key:
        if not pb: raise RuntimeError('Model missing: copy assets/human_object_tracker into Sonomika assets')
        _net = cv2.dnn.readNetFromTensorflow(pb, cfg)
        _net_key = key
    return _net

def _load_face(comp, size):
    global _face_detector, _face_key
    _, cfg = _model_paths(comp)
    model = os.path.join(os.path.dirname(cfg), 'face_detection_yunet_2023mar.onnx') if cfg else ''
    key = model + '|' + str(size)
    if not os.path.isfile(model): raise RuntimeError('YuNet face model missing from assets/human_object_tracker/model')
    if _face_detector is None or key != _face_key:
        _face_detector = cv2.FaceDetectorYN.create(model, '', size, 0.45, 0.3, 5000)
        _face_key = key
    else:
        _face_detector.setInputSize(size)
    return _face_detector

def _detect(comp, rgb):
    h, w = rgb.shape[:2]
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    mode = comp.par.Mode.menuIndex
    if mode == 3:
        detector = _load_face(comp, (w, h))
        detector.setScoreThreshold(max(0.40, float(comp.par.Confidence)))
        _, faces = detector.detect(bgr)
        found = []
        if faces is not None:
            for face in faces:
                x, y, bw, bh, score = int(face[0]), int(face[1]), int(face[2]), int(face[3]), float(face[-1])
                found.append([max(0,x), max(0,y), min(w,x+bw), min(h,y+bh), -1, score])
        found.sort(key=lambda b: b[5], reverse=True)
        return found[:int(comp.par.Maxobjects)]
    net = _load(comp)
    net.setInput(cv2.dnn.blobFromImage(
        bgr, scalefactor=1.0/127.5, size=(300, 300),
        mean=(127.5, 127.5, 127.5), swapRB=True, crop=False))
    out = net.forward().reshape(-1, 7)
    wanted = int(comp.par.Objectclass)
    found = []
    for row in out:
        conf, cls = float(row[2]), int(row[1])
        if conf < float(comp.par.Confidence): continue
        if mode == 0 and cls != 1: continue
        if mode == 1 and cls != wanted: continue
        x1, y1, x2, y2 = row[3:7]
        box = [max(0, min(w-1, int(x1*w))), max(0, min(h-1, int(y1*h))),
               max(1, min(w, int(x2*w))), max(1, min(h, int(y2*h))), cls, conf]
        if box[2] > box[0] and box[3] > box[1]: found.append(box)
    found.sort(key=lambda b: b[5], reverse=True)
    return found[:int(comp.par.Maxobjects)]

def _track(comp, boxes, w, h):
    global _tracks
    old = _tracks
    result = []
    threshold = float(comp.par.Motionthreshold) * (w*w + h*h) ** 0.5
    smooth = float(comp.par.Smoothing)
    for b in boxes:
        cx, cy = (b[0]+b[2])*.5, (b[1]+b[3])*.5
        choices = [t for t in old if t[4] == b[4]]
        match = min(choices, key=lambda t: ((t[0]+t[2])*.5-cx)**2 + ((t[1]+t[3])*.5-cy)**2, default=None)
        moving = True
        if match:
            ox, oy = (match[0]+match[2])*.5, (match[1]+match[3])*.5
            moving = ((cx-ox)**2 + (cy-oy)**2)**.5 >= threshold
            b[:4] = [int(match[i]*smooth + b[i]*(1-smooth)) for i in range(4)]
        b += [int(comp.par.Persistence), moving]
        result.append(b)
    for t in old:
        if t[6] > 0 and not any(t[4] == b[4] and abs((t[0]+t[2])-(b[0]+b[2])) < w*.15 for b in result):
            t[6] -= 1; result.append(t)
    _tracks = result[:int(comp.par.Maxobjects)]
    return [t for t in _tracks if (not comp.par.Motiononly or t[7])]

def onCook(scriptOp):
    global _frame, _tracks, _last_src_td, _last_mask_td
    comp = scriptOp.parent()
    if not scriptOp.inputs:
        scriptOp.copyNumpyArray(np.zeros((64,64,4), np.float32)); return
    detect_now = _frame % max(1, int(comp.par.Detectionrate)) == 0
    if not detect_now and _last_mask_td is not None:
        _frame += 1
        scriptOp.copyNumpyArray(_last_mask_td)
        return
    src_td = scriptOp.inputs[0].numpyArray(delayed=True)
    if src_td is None:
        if _last_src_td is None:
            src_td = scriptOp.inputs[0].numpyArray()
        else:
            src_td = _last_src_td
    else:
        _last_src_td = src_td
    # TouchDesigner returns TOP arrays as width x height; OpenCV uses height x width.
    src = np.transpose(np.nan_to_num(src_td), (1, 0, 2))
    rgb = np.clip(src[:,:,:3] * 255.0, 0, 255).astype(np.uint8)
    h, w = rgb.shape[:2]
    try:
        if comp.par.Active and detect_now:
            boxes = _detect(comp, rgb)
            _track(comp, boxes, w, h)
        _frame += 1
        pad = int(float(comp.par.Padding) * min(w,h))
        mask = np.zeros((h,w), np.uint8)
        shown = [t for t in _tracks if (not comp.par.Motiononly or t[7])]
        for b in shown:
            x1,y1,x2,y2 = max(0,b[0]-pad),max(0,b[1]-pad),min(w,b[2]+pad),min(h,b[3]+pad)
            cv2.rectangle(mask,(x1,y1),(x2,y2),255,-1)
        soft = int(float(comp.par.Softness) * min(w,h)); soft += 1-soft%2
        if soft > 1: mask = cv2.GaussianBlur(mask,(soft,soft),0)
        m = mask.astype(np.float32)/255.0
        result = np.dstack((m,m,m,m))
        _last_mask_td = np.ascontiguousarray(np.transpose(result.astype(np.float32), (1, 0, 2)))
        scriptOp.copyNumpyArray(_last_mask_td)
        comp.par.Status = 'Tracking {} object(s)'.format(len(shown))
    except Exception as exc:
        comp.par.Status = str(exc)
        scriptOp.copyNumpyArray(src_td.astype(np.float32))

def onSetupParameters(scriptOp): return
def onPulse(par): return
'''

root = op('/project1')
old = root.op('__build_human_object_tracker')
if old: old.destroy()
c = root.create('baseCOMP', '__build_human_object_tracker')
page = c.appendCustomPage('Tracker')
def toggle(n,l,v): p=page.appendToggle(n,label=l); p.default=v; p.val=v; return p
def flt(n,l,v,lo,hi):
    p=page.appendFloat(n,label=l); p.default=v; p.val=v; p.min=lo; p.max=hi; p.normMin=lo; p.normMax=hi; p.clampMin=True; p.clampMax=True; return p
toggle('Active','Active',True)
p=page.appendMenu('Mode',label='Detect')
c.cook(force=True)
p=c.par.Mode
p.menuNames=['people','selected','all','faces']
p.menuLabels=['People','Selected Object','All Objects','Faces']
p.default=0
p.val=0
p=page.appendInt('Objectclass',label='COCO Class ID'); p.default=1; p.val=1; p.min=1; p.max=90
flt('Confidence','Confidence',0.2,0.05,0.95)
p=page.appendInt('Detectionrate',label='Detect Every Frames'); p.default=5; p.val=5; p.min=1; p.max=30
p=page.appendInt('Processresolution',label='Processing Width'); p.default=240; p.val=240; p.min=160; p.max=960; p.normMin=160; p.normMax=960
toggle('Motiononly','Moving Objects Only',False)
flt('Motionthreshold','Motion Threshold',0.01,0.0,0.2)
p=page.appendInt('Persistence',label='Tracking Persistence'); p.default=6; p.val=6; p.min=0; p.max=60
flt('Smoothing','Tracking Smoothing',0.55,0.0,0.95)
p=page.appendInt('Maxobjects',label='Maximum Objects'); p.default=10; p.val=10; p.min=1; p.max=50
flt('Padding','Box Padding',0.02,0.0,0.25)
flt('Softness','Mask Softness',0.01,0.0,0.2)
p=page.appendMenu('Output',label='Output')
c.cook(force=True)
p=c.par.Output
p.menuNames=['mask','masked','boxes']
p.menuLabels=['Box Mask','Masked Source','Boxes Over Source']
p.default=2
p.val=2
flt('Borderwidth','Box Border Width',3.0,1.0,30.0)
p=page.appendRGB('Boxcolor',label='Box Colour'); p.default=(0.1,1.0,0.25); p.val=(0.1,1.0,0.25)
p=page.appendStr('Status',label='Status'); p.val='Ready'; p.readOnly=True

inp=c.create('inTOP','input1')
source=c.create('selectTOP','source_router')
source.par.top.expr="(parent().parent().op('video_canvas_fit') if parent().parent().op('video') and str(parent().parent().op('video').par.file.eval() or '') else (parent().parent().op('upstream') or parent().op('input1')))"
down=c.create('fitTOP','analysis_resolution'); down.inputConnectors[0].connect(source)
down.par.outputresolution.val='custom'
down.par.resolutionw.expr="max(parent().par.Processresolution, 640) if parent().par.Mode.menuIndex == 3 else parent().par.Processresolution"
down.par.resolutionh.expr="max(1, int((max(parent().par.Processresolution, 640) if parent().par.Mode.menuIndex == 3 else parent().par.Processresolution) * op('source_router').height / max(op('source_router').width, 1)))"
det=c.create('scriptTOP','tracker'); det.inputConnectors[0].connect(down)
cb=det.par.callbacks.eval()
if cb is None:
    cb=c.create('textDAT','tracker_callbacks')
    det.par.callbacks=cb
cb.text=CALLBACKS
det.par.outputresolution='useinput'
maskup=c.create('fitTOP','mask_full_resolution'); maskup.inputConnectors[0].connect(det)
maskup.par.outputresolution.val='custom'
maskup.par.resolutionw.expr="op('source_router').width"
maskup.par.resolutionh.expr="op('source_router').height"
masked=c.create('compositeTOP','masked_source'); masked.inputConnectors[0].connect(source); masked.inputConnectors[1].connect(maskup); masked.par.operand='multiply'
edges=c.create('edgeTOP','box_edges'); edges.inputConnectors[0].connect(maskup)
edges.par.edgecolorr.expr='parent().par.Boxcolorr'; edges.par.edgecolorg.expr='parent().par.Boxcolorg'; edges.par.edgecolorb.expr='parent().par.Boxcolorb'; edges.par.edgecolora=1.0
edges.par.strength.expr='parent().par.Borderwidth'
boxes=c.create('overTOP','boxes_over_source'); boxes.inputConnectors[0].connect(edges); boxes.inputConnectors[1].connect(source)
pick=c.create('switchTOP','output_select'); pick.inputConnectors[0].connect(maskup); pick.inputConnectors[1].connect(masked); pick.inputConnectors[2].connect(boxes); pick.par.index.expr='parent().par.Output.menuIndex'
out=c.create('nullTOP','out1'); out.inputConnectors[0].connect(pick)
inp.nodeX=0; source.nodeX=140; down.nodeX=300; det.nodeX=460; maskup.nodeX=620; pick.nodeX=800; out.nodeX=960
c.par.externaltox = ''
for path in OUTS:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c.save(path)
print('Saved:', *OUTS, sep='\n')
c.destroy()
