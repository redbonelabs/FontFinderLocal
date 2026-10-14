"""Unicode metadata and face extraction independent of the HTTP layer."""
from pathlib import Path
from fontTools.ttLib import TTFont, TTCollection

SUPPORTED = {".ttf", ".otf", ".ttc", ".otc", ".woff", ".woff2"}
SCHEMA_VERSION = 1


def signature(path):
    st = path.stat()
    return f"{SCHEMA_VERSION}:{st.st_size}:{st.st_mtime_ns}:{st.st_ctime_ns}"


def name(font, *ids):
    table = font.get("name")
    if table is None:
        return ""
    for name_id in ids:
        records = sorted((n for n in table.names if n.nameID == name_id),
                         key=lambda n: (n.langID not in (0x409, 0), n.platformID != 3))
        for record in records:
            try:
                value = record.toUnicode().replace("\x00", "").strip()
                if value:
                    return value[:1024]
            except (UnicodeError, LookupError):
                continue
    return ""


def ranges(codepoints):
    output = []
    for cp in sorted(codepoints):
        if output and cp == output[-1][1] + 1:
            output[-1][1] = cp
        else:
            output.append([cp, cp])
    return output


def read_face(font, path, index):
    os2, post = font.get("OS/2"), font.get("post")
    selection = getattr(os2, "fsSelection", 0)
    italic = bool(selection & 1 or selection & 512 or getattr(post, "italicAngle", 0)
                  or getattr(font.get("head"), "macStyle", 0) & 2)
    family_class = (getattr(os2, "sFamilyClass", 0) >> 8) & 255
    # Only classify explicit metadata; an absent/unknown class stays unknown.
    category = "unknown"
    if getattr(post, "isFixedPitch", 0):
        category = "monospace"
    elif family_class in {1, 2, 3, 4, 5, 7}:
        category = "serif"
    elif family_class == 8:
        category = "sans-serif"
    elif family_class == 10:
        category = "script"
    elif family_class == 9:
        category = "decorative"
    elif family_class == 12:
        category = "symbol"
    family = name(font, 16, 1) or Path(path).stem
    style = name(font, 17, 2) or "Regular"
    axes, instances = [], []
    if "fvar" in font:
        for axis in font["fvar"].axes:
            axes.append({"tag": axis.axisTag, "name": name(font, axis.axisNameID) or axis.axisTag,
                         "min": axis.minValue, "default": axis.defaultValue, "max": axis.maxValue})
        for instance in font["fvar"].instances:
            instances.append({"name": name(font, instance.subfamilyNameID),
                              "coordinates": instance.coordinates})
    cmap = font.getBestCmap() or {}
    return {
        "family": family, "style": style, "full_name": name(font, 4) or f"{family} {style}",
        "postscript_name": name(font, 6), "weight": getattr(os2, "usWeightClass", 400),
        "italic": italic, "category": category, "face_index": index,
        "format": "OpenType/CFF" if font.sfntVersion == "OTTO" else "TrueType",
        "container": Path(path).suffix[1:].upper(), "axes": axes, "instances": instances,
        "coverage": ranges(cmap), "glyph_count": len(cmap),
    }


def extract_metadata(path):
    with open(path, "rb") as file:
        is_collection = file.read(4) == b"ttcf"
    if is_collection:
        collection = TTCollection(path, lazy=True)
        try:
            return [read_face(font, path, i) for i, font in enumerate(collection.fonts)]
        finally:
            collection.close()
    font = TTFont(path, lazy=True)
    try:
        return [read_face(font, path, 0)]
    finally:
        font.close()
