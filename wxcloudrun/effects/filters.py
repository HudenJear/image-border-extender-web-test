from PIL import Image, ImageOps, ImageEnhance
import numpy as np

__all__ = [
    'apply_filter',
    'FILTER_HANDLERS',
    'AVAILABLE_FILTER_KEYS',
]


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _scale_factor(base_at_half: float, strength: float) -> float:
    """
    Map strength in [0,1] to a multiplicative factor.
    - 0.5 => base_at_half (existing baseline)
    - 1.0 => 1 + (base_at_half-1)*2
    - 0.0 => 1.0
    """
    s = _clamp01(strength)
    k = s / 0.5 if s > 0 else 0.0
    return 1.0 + (base_at_half - 1.0) * k


def _filter_none(img: Image.Image, strength: float) -> Image.Image:
    return img


def _filter_black_white(img: Image.Image, strength: float) -> Image.Image:
    gray = ImageOps.grayscale(img).convert('RGB')
    s = _clamp01(strength)
    if s < 0.5:
        a = s / 0.5
        return Image.blend(img, gray, a)
    else:
        out = gray
        extra = (s - 0.5) / 0.5
        contrast_factor = 1.0 + 0.2 * extra
        out = ImageEnhance.Contrast(out).enhance(contrast_factor)
        return out


def _filter_vivid(img: Image.Image, strength: float) -> Image.Image:
    color_f = _scale_factor(1.5, strength)
    contrast_f = _scale_factor(1.2, strength)
    bright_f = _scale_factor(1.03, strength)
    img_c = ImageEnhance.Color(img).enhance(color_f)
    img_ct = ImageEnhance.Contrast(img_c).enhance(contrast_f)
    img_b = ImageEnhance.Brightness(img_ct).enhance(bright_f)
    return img_b


def _filter_retro(img: Image.Image, strength: float) -> Image.Image:
    arr = np.array(img, dtype=np.float32)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    tr = 0.393 * r + 0.769 * g + 0.189 * b
    tg = 0.349 * r + 0.686 * g + 0.168 * b
    tb = 0.272 * r + 0.534 * g + 0.131 * b
    sepia = np.stack([tr, tg, tb], axis=-1)
    sepia = np.clip(sepia, 0, 255).astype('uint8')
    out = Image.fromarray(sepia, mode='RGB')
    out = ImageEnhance.Contrast(out).enhance(0.95)
    out = ImageEnhance.Color(out).enhance(1.05)

    s = _clamp01(strength)
    if s < 0.5:
        a = s / 0.5
        return Image.blend(img, out, a)
    else:
        extra = (s - 0.5) / 0.5
        warm = Image.new('RGB', out.size, (255, 235, 200))
        out2 = Image.blend(out, warm, 0.08 * extra)
        out2 = ImageEnhance.Color(out2).enhance(1.0 + 0.1 * extra)
        out2 = ImageEnhance.Contrast(out2).enhance(1.0 + 0.05 * extra)
        return out2


def _filter_film(img: Image.Image, strength: float) -> Image.Image:
    s = _clamp01(strength)
    k = s / 0.5 if s > 0 else 0.0
    sigma = 6.0 * k
    contrast_f = 1.0 + (0.98 - 1.0) * k
    tint_alpha = 0.04 * k

    if sigma > 0:
        arr = np.array(img, dtype=np.int16)
        h, w, _ = arr.shape
        noise = np.random.normal(loc=0.0, scale=sigma, size=(h, w, 1))
        noise = np.repeat(noise, 3, axis=2)
        arr = arr + noise
        arr = np.clip(arr, 0, 255).astype('uint8')
        out = Image.fromarray(arr, mode='RGB')
    else:
        out = img

    out = ImageEnhance.Contrast(out).enhance(contrast_f)
    if tint_alpha > 0:
        tint = Image.new('RGB', out.size, (220, 235, 225))
        out = Image.blend(out, tint, alpha=tint_alpha)
    return out


FILTER_HANDLERS = {
    'none': _filter_none,
    'black_white': _filter_black_white,
    'vivid': _filter_vivid,
    'retro': _filter_retro,
    'film': _filter_film,
}

AVAILABLE_FILTER_KEYS = set(FILTER_HANDLERS.keys())


def apply_filter(img_input: Image.Image, filter_key: str, strength: float = 0.5) -> Image.Image:
    if img_input is None:
        return img_input
    key = (filter_key or 'none').strip().lower()
    img = img_input.convert('RGB')
    handler = FILTER_HANDLERS.get(key, FILTER_HANDLERS['none'])
    return handler(img, strength)
