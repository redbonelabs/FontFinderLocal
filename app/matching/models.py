import math
import unicodedata
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Processing(StrictModel):
    crop: tuple[float, float, float, float] = (0, 0, 1, 1)
    quarter_turns: int = Field(0, ge=0, le=3)
    rotation: float = Field(0, ge=-30, le=30)
    perspective: list[tuple[float, float]] | None = Field(None, min_length=4, max_length=4)
    polarity: Literal["auto", "dark", "light"] = "auto"
    method: Literal["auto", "global", "adaptive", "color", "alpha"] = "auto"
    threshold: int = Field(128, ge=1, le=254)
    foreground: str = "#000000"
    color_tolerance: int = Field(75, ge=5, le=240)
    contrast: float = Field(1, ge=0.5, le=3)
    background_removal: bool = True
    denoise: int = Field(1, ge=0, le=3)
    outline: Literal["preserve", "auto", "fill"] = "auto"
    shadow: bool = False
    deskew: bool = False

    @field_validator("crop")
    @classmethod
    def valid_crop(cls, value):
        x, y, w, h = value
        if not all(0 <= v <= 1 for v in value) or w < .005 or h < .005 or x + w > 1.00001 or y + h > 1.00001:
            raise ValueError("Crop must be a nonempty rectangle inside the image.")
        return value

    @field_validator("foreground")
    @classmethod
    def valid_color(cls, value):
        import re
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ValueError("Choose an RGB foreground color.")
        return value

    @field_validator("perspective")
    @classmethod
    def valid_points(cls, value):
        if value and any(not 0 <= n <= 1 for p in value for n in p):
            raise ValueError("Perspective corners must be inside the image.")
        return value


class ProcessRequest(StrictModel):
    image_id: str
    processing: Processing = Field(default_factory=Processing)


def validate_text(text):
    # Validation only. Never strip, normalize, casefold, or replace the returned text.
    if not any(not c.isspace() and not unicodedata.category(c).startswith("C") for c in text):
        raise ValueError("Enter at least one visible character exactly as shown in the image.")
    if any(unicodedata.category(c) in {"Cs", "Cc"} and c not in "\n\t" for c in text):
        raise ValueError("Unsupported control character in reference text.")
    if "\n" in text or "\t" in text:
        raise ValueError("Crop one line of lettering and enter that line using spaces, without tabs or line breaks.")
    return text


class MatchRequest(StrictModel):
    process_id: str
    text: str = Field(min_length=1, max_length=160)
    shortlist: int = Field(60, ge=10, le=120)
    sensitivity: Literal["balanced", "strict", "flexible"] = "balanced"
    tracking: float = Field(0, ge=-12, le=24)
    alignment: Literal["center", "left", "right"] = "center"
    variable_instances: bool = True

    _text = field_validator("text")(validate_text)


class Alignment(StrictModel):
    mode: Literal["side", "overlay", "difference", "outline"] = "overlay"
    x: float = Field(0, ge=-250, le=250)
    y: float = Field(0, ge=-150, le=150)
    scale: float = Field(1, ge=.5, le=2)
    scale_x: float = Field(1, ge=.5, le=2)
    scale_y: float = Field(1, ge=.5, le=2)
    rotation: float = Field(0, ge=-30, le=30)
    tracking: float | None = Field(None, ge=-12, le=24)
    opacity: float = Field(.6, ge=0, le=1)
    reference: Literal["processed", "original"] = "original"


class CompareRequest(StrictModel):
    font_id: str
    alignment: Alignment = Field(default_factory=Alignment)
