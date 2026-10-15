"""HarfBuzz shaping + FreeType glyph rasterization; never uses system fallback."""
from collections import OrderedDict
from dataclasses import dataclass
from io import BytesIO
import threading
import unicodedata
import freetype
import uharfbuzz as hb
import numpy as np
from ..rendering import Renderer, locate
from .models import validate_text


class RenderError(ValueError):
    pass


def missing_glyphs(face, text):
    coverage = face["coverage"]
    missing = []
    for char in dict.fromkeys(text):
        cp = ord(char)
        if cp in (0x200c, 0x200d) or 0xfe00 <= cp <= 0xfe0f:
            continue
        if not any(a <= cp <= b for a,b in coverage):
            missing.append(char)
    return missing


@dataclass
class Raster:
    mask: np.ndarray
    advance: float
    glyphs: int
    text: str


class Rasterizer:
    def __init__(self, assets=None, max_bytes=48*1024*1024):
        self.assets = assets or Renderer()
        self.cache = OrderedDict()
        self.size = 0
        self.max_bytes = max_bytes
        self.lock = threading.RLock()

    def _font_data(self, face, path):
        # Native sfnt files already contain exactly what FreeType/HarfBuzz need.
        # Reserializing every table merely to recompute checksums dominated cold
        # searches. Native collections retain their actual face index; only web
        # fonts need the existing standalone sfnt conversion.
        # Do not alter the shared browser asset renderer or add an unbounded cache.
        with path.open("rb") as source:
            header = source.read(4)
            if header in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
                return header + source.read(), 0
            if header == b"ttcf":
                return header + source.read(), face["face_index"]
        return self.assets.asset(face), 0

    def render(self, face, text, size=96, tracking=0, coordinates=None):
        validate_text(text)
        absent = missing_glyphs(face,text)
        if absent:
            raise RenderError("Missing glyphs: " + " ".join(absent[:10]))
        coordinates = coordinates or {}
        for axis in face["axes"]:
            value = coordinates.get(axis["tag"],axis["default"])
            if not axis["min"] <= value <= axis["max"]:
                raise RenderError("Variable axis is outside its supported range.")
        key = (face["id"],text,size,round(tracking,3),tuple(sorted(coordinates.items())))
        with self.lock:
            path = locate(face)  # A cached rendering must not disguise an unavailable font.
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            try:
                data, face_index = self._font_data(face, path)
                ft = freetype.Face(BytesIO(data), index=face_index)
                ft.set_pixel_sizes(0,size)
                if face["axes"]:
                    ft.set_var_design_coords([coordinates.get(a["tag"],a["default"]) for a in face["axes"]])
                font = hb.Font(hb.Face(data, face_index))
                font.scale = (size*64,size*64)
                hb.ot_font_set_funcs(font)
                if coordinates:
                    font.set_variations(coordinates)
                buffer = hb.Buffer(); buffer.add_str(text); buffer.guess_segment_properties()
                # With tracking, optional Latin ligatures are expanded so spacing is meaningful.
                hb.shape(font,buffer,{"liga":False,"clig":False} if tracking else {})
                infos, positions = buffer.glyph_infos, buffer.glyph_positions
                if any(info.codepoint == 0 for info in infos):
                    raise RenderError("Shaping produced a missing glyph; candidate excluded.")
                pen_x, pen_y = 0.,0.
                pieces = []
                for index,(info,pos) in enumerate(zip(infos,positions)):
                    ft.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_BITMAP)
                    bitmap = ft.glyph.bitmap
                    if bitmap.width and bitmap.rows:
                        if bitmap.pixel_mode != freetype.FT_PIXEL_MODE_GRAY:
                            raise RenderError("This color/bitmap glyph format is unsupported by the matching renderer.")
                        pixels = np.array(bitmap.buffer,dtype=np.uint8).reshape(bitmap.rows,abs(bitmap.pitch))[:,:bitmap.width]
                        x = round(pen_x + pos.x_offset/64 + ft.glyph.bitmap_left)
                        y = round(-pen_y - pos.y_offset/64 - ft.glyph.bitmap_top)
                        pieces.append((x,y,pixels))
                    pen_x += pos.x_advance/64
                    pen_y += pos.y_advance/64
                    if index+1 < len(infos) and infos[index+1].cluster != info.cluster:
                        pen_x += tracking
                if not pieces:
                    raise RenderError("This font produced no visible ink.")
                x0=min(p[0] for p in pieces); y0=min(p[1] for p in pieces)
                x1=max(x+p.shape[1] for x,y,p in pieces); y1=max(y+p.shape[0] for x,y,p in pieces)
                if (x1-x0)*(y1-y0) > 8_000_000 or x1-x0 > 20000 or y1-y0 > 2048:
                    raise RenderError("Rendered text is too large. Use a shorter crop/text sample.")
                mask=np.zeros((y1-y0,x1-x0),np.uint8)
                for x,y,pixels in pieces:
                    area=mask[y-y0:y-y0+pixels.shape[0],x-x0:x-x0+pixels.shape[1]]
                    np.maximum(area,pixels,out=area)
                raster=Raster(mask,pen_x,len(infos),text)
            except RenderError:
                raise
            except Exception as exc:
                raise RenderError("Font could not be shaped and rasterized.") from exc
            while self.cache and self.size+mask.nbytes > self.max_bytes:
                _,old=self.cache.popitem(last=False); self.size-=old.mask.nbytes
            if mask.nbytes <= self.max_bytes:
                self.cache[key]=raster; self.size+=mask.nbytes
            return raster
