"""Conservative shape isolation with alternatives; counters are never hole-filled."""
from dataclasses import dataclass
import cv2
import numpy as np
from PIL import Image
from .images import ImageError
from .models import Processing

cv2.setNumThreads(1)


@dataclass
class Processed:
    mask: np.ndarray
    alternatives: dict
    image: np.ndarray
    corrected: np.ndarray
    warnings: list
    angle: float
    bounds: tuple


def rotate(array, angle, border=0):
    h, w = array.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1)
    return cv2.warpAffine(array, matrix, (w, h), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=border)


def ink_bounds(mask):
    y, x = np.nonzero(mask > 127)
    if not len(x):
        raise ImageError("No lettering isolated. Adjust crop, polarity, threshold, or foreground color.")
    return int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1


def clean(mask, level):
    if level == 0:
        return mask
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if count < 2:
        return mask
    # Very conservative: keep punctuation and disconnected dots. No global erosion.
    cutoff = max(1, min(12, int(mask.size * .000004 * level)))
    keep = np.flatnonzero(stats[:, cv2.CC_STAT_AREA] >= cutoff)
    keep = keep[keep != 0]
    return (np.isin(labels, keep).astype(np.uint8) * 255)


def estimate_skew(mask):
    h, w = mask.shape
    if w < h * 1.5:
        return 0.0
    small = cv2.resize(mask, (min(w, 600), max(20, round(h * min(w, 600) / w))))
    def score(angle):
        rows = (rotate(small, angle) > 127).sum(axis=1)
        return float(np.sum(np.diff(rows.astype(float)) ** 2))
    base = score(0)
    angle = max(range(-10, 11), key=score)
    return float(angle) if angle not in (-10, 10) and score(angle) > base * 1.08 else 0.0


def preprocess(image: Image.Image, options: Processing):
    rgba = np.asarray(image.convert("RGBA"))
    rgba = np.rot90(rgba, -options.quarter_turns).copy()
    h, w = rgba.shape[:2]
    if options.perspective:
        corners = np.float32([[x * (w - 1), y * (h - 1)] for x, y in options.perspective])
        if not cv2.isContourConvex(corners) or abs(cv2.contourArea(corners)) < 64:
            raise ImageError("Perspective corners must form a non-crossing quadrilateral: top-left, top-right, bottom-right, bottom-left.")
        width = max(np.linalg.norm(corners[1]-corners[0]), np.linalg.norm(corners[2]-corners[3]))
        height = max(np.linalg.norm(corners[3]-corners[0]), np.linalg.norm(corners[2]-corners[1]))
        width, height = max(4, int(width)), max(4, int(height))
        dest = np.float32([[0, 0], [width-1, 0], [width-1, height-1], [0, height-1]])
        rgba = cv2.warpPerspective(rgba, cv2.getPerspectiveTransform(corners, dest), (width, height))
    else:
        x, y, cw, ch = options.crop
        rgba = rgba[round(y*h):max(round(y*h)+2, round((y+ch)*h)), round(x*w):max(round(x*w)+2, round((x+cw)*w))].copy()
    if min(rgba.shape[:2]) < 3:
        raise ImageError("Crop is too small. Select the complete lettering.")
    alpha = rgba[:, :, 3].astype(np.float32) / 255
    transparent = np.count_nonzero(alpha < .95) > alpha.size * .02
    visible = rgba[:, :, :3][alpha > .5]
    background = 16 if transparent and len(visible) and np.median(visible) > 180 else 255
    rgb = (rgba[:, :, :3] * alpha[..., None] + background * (1-alpha[..., None])).astype(np.uint8)
    border_color=tuple(int(v) for v in np.median(np.concatenate((rgb[0],rgb[-1],rgb[:,0],rgb[:,-1])),axis=0))
    if options.rotation:
        rgb = rotate(rgb, options.rotation, border_color); alpha = rotate(alpha, options.rotation)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray = np.clip((gray.astype(float)-127.5)*options.contrast+127.5,0,255).astype(np.uint8)
    warnings = []
    if min(gray.shape) < 40:
        warnings.append("Small lettering: use a larger source image for more distinguishing detail.")
    if np.percentile(gray, 95) - np.percentile(gray, 5) < 35:
        warnings.append("Low contrast may make the letter boundary uncertain.")
    light = options.polarity == "light"
    if options.polarity == "auto":
        border = np.concatenate((gray[0], gray[-1], gray[:,0], gray[:,-1]))
        light = np.median(border) < np.median(gray)
        if np.std(gray) > 1 and np.median(border) == np.median(gray):
            light = np.median(border) < 127
    mode = cv2.THRESH_BINARY if light else cv2.THRESH_BINARY_INV
    _, automatic = cv2.threshold(gray, 0, 255, mode | cv2.THRESH_OTSU)
    _, manual = cv2.threshold(gray, options.threshold, 255, mode)
    if options.method == "alpha":
        if not transparent:
            raise ImageError("This image has no useful transparency. Choose another processing method.")
        mask = (alpha > options.threshold / 255).astype(np.uint8)*255
    elif options.method == "color":
        color = np.array([int(options.foreground[i:i+2],16) for i in (1,3,5)])
        distance = np.linalg.norm(rgb.astype(float)-color, axis=2)
        mask = ((distance < options.color_tolerance) & (alpha > .1)).astype(np.uint8)*255
    elif options.method == "adaptive":
        block = min(51, min(gray.shape) // 2 * 2 - 1)
        if block < 3:
            raise ImageError("Crop is too small for adaptive thresholding.")
        mask = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,mode,block,7)
    elif options.method == "global":
        mask = manual
    elif transparent and np.std(alpha) > .15:
        mask = (alpha > .4).astype(np.uint8)*255
    else:
        mask = automatic
    if options.background_removal and transparent:
        mask[alpha < .1] = 0
    mask = clean(mask, options.denoise)
    alternatives = {"base": mask.copy()}
    # Color cores provide a reversible alternative for outlines/shadows, not fixed erosion.
    if (options.outline != "preserve" or options.shadow) and options.method != "color":
        selected = rgb[mask > 0]
        if len(selected) > 20:
            # Dominant quantized foreground color, excluding antialias fringes.
            quant = (selected // 32).astype(np.int32)
            keys = quant[:,0]*64 + quant[:,1]*8 + quant[:,2]
            dominant = np.bincount(keys).argmax()
            core_color = np.median(selected[keys == dominant],axis=0)
            core = ((np.linalg.norm(rgb.astype(float)-core_color,axis=2) < 48) & (mask > 0)).astype(np.uint8)*255
            ratio = np.count_nonzero(core)/max(1,np.count_nonzero(mask))
            if .25 < ratio < .95:
                alternatives["color core"] = clean(core,options.denoise)
                if options.outline == "fill" or options.shadow:
                    mask = alternatives["color core"]
            elif options.outline == "fill" or options.shadow:
                warnings.append("A separate fill/shadow color could not be isolated; preserved the original mask. Try foreground color selection.")
    angle = estimate_skew(mask)
    if options.deskew and angle:
        mask = rotate(mask, angle)
        alternatives = {k: rotate(v,angle) for k,v in alternatives.items()}
        rgb = rotate(rgb,angle,border_color)
    elif abs(angle) >= 2:
        warnings.append(f"Possible skew of about {-angle:g}°. Inspect automatic deskew or adjust fine rotation.")
    x0,y0,x1,y1 = ink_bounds(mask)
    if x0 <= 1 or y0 <= 1 or x1 >= mask.shape[1]-1 or y1 >= mask.shape[0]-1:
        warnings.append("Ink touches the crop boundary. Include complete letters and some surrounding space.")
    density = np.count_nonzero(mask)/mask.size
    if density > .7:
        warnings.append("Most pixels are foreground. Check polarity or tighten the crop.")
    if options.outline == "preserve":
        alternatives = {"base":mask}
    alternatives = {k: v[y0:y1,x0:x1] for k,v in alternatives.items()}
    return Processed(mask[y0:y1,x0:x1], alternatives, rgb[y0:y1,x0:x1], rgb, warnings, angle, (x0,y0,x1,y1))
