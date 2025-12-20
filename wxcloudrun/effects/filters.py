from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from pathlib import Path
import numpy as np
import time

from .filter_utils import clamp01 as _clamp01
from .filter_utils import scale_factor as _scale_factor
from .filter_utils import apply_film_grain as _apply_film_grain
from .filter_utils import float_rgb_to_image
from .filter_utils import image_to_float_rgb
from .filter_utils import luminance_from_rgb
from .filter_utils import mask_above
from .filter_utils import mask_below
from .filter_utils import contrast_about_mid
from .filter_utils import apply_white_balance
from .filter_utils import apply_matrix_3x3
from .filter_utils import apply_highlight_lift
from .filter_utils import apply_tint_mask
from .filter_utils import desaturate_to_gray_mask
from .filter_utils import apply_rgb_gain_mask
from .filter_utils import apply_scalar_gain_mask
from .filter_utils import apply_channel_mul
from .filter_utils import blue_dominance_mask
from .filter_utils import green_dominance_mask
from .filter_utils import red_dominance_mask
from .filter_utils import yellow_dominance_mask, make_lut_filter,apply_lut

__all__ = [
    'apply_filter',
    'FILTER_HANDLERS',
    'AVAILABLE_FILTER_KEYS',
]


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


def _filter_film_kodak_5219(img: Image.Image, strength: float) -> Image.Image:
    s = _clamp01(strength)
    if s <= 0:
        return img
    color_f = _scale_factor(0.80, s)
    base = ImageEnhance.Color(img).enhance(color_f)
    arr = image_to_float_rgb(base)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    l = luminance_from_rgb(r, g, b)
    hl = mask_above(l, 0.55, 0.45)
    sh = mask_below(l, 0.35, 0.35)
    a = 1.4 * s
    l_f = l / (1.0 + a * l)
    l_new = l * (1.0 - hl) + l_f * hl
    scale = l_new / (l + 1e-6)
    r = r * scale
    g = g * scale
    b = b * scale
    toe = 0.28 * s
    l_toe = l_new - toe * sh * (1.0 - l_new) * l_new
    scale2 = l_toe / (l_new + 1e-6)
    r = r * scale2
    g = g * scale2
    b = b * scale2
    gray = l_new
    desat_hl = 0.18 * s * hl
    r = r * (1.0 - desat_hl) + gray * desat_hl
    g = g * (1.0 - desat_hl) + gray * desat_hl
    b = b * (1.0 - desat_hl) + gray * desat_hl
    tint_hl = np.array([240.0/255.0, 245.0/255.0, 220.0/255.0], dtype=np.float32)
    tint_sh = np.array([230.0/255.0, 200.0/255.0, 235.0/255.0], dtype=np.float32)
    a_hl = 0.24 * s
    a_sh = 0.16 * s
    r = r * (1.0 - a_hl * hl) + tint_hl[0] * (a_hl * hl)
    g = g * (1.0 - a_hl * hl) + tint_hl[1] * (a_hl * hl)
    b = b * (1.0 - a_hl * hl) + tint_hl[2] * (a_hl * hl)
    r = r * (1.0 - a_sh * sh) + tint_sh[0] * (a_sh * sh)
    g = g * (1.0 - a_sh * sh) + tint_sh[1] * (a_sh * sh)
    b = b * (1.0 - a_sh * sh) + tint_sh[2] * (a_sh * sh)
    arr_t = np.stack([r, g, b], axis=-1)
    m = np.array([
        [1.0, -0.030 * s, 0.000],
        [-0.015 * s, 1.0, 0.000],
        [0.000, -0.015 * s, 1.0],
    ], dtype=np.float32)
    arr_t = apply_matrix_3x3(arr_t, m)
    arr_t = np.clip(arr_t, 0.0, 1.0)
    arr_t = _apply_film_grain(arr_t, s, mid=0.5, sigma_base=0.015, sigma_slope=0.012, cw=[0.96, 1.00, 1.08])
    return float_rgb_to_image(arr_t)


def _filter_film_kodak_e100(img: Image.Image, strength: float) -> Image.Image:
    s = _clamp01(strength)
    if s <= 0:
        return img
    color_f = _scale_factor(0.95, s)
    base = ImageEnhance.Color(img).enhance(color_f)
    arr = image_to_float_rgb(base)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    l = luminance_from_rgb(r, g, b)
    hl = mask_above(l, 0.55, 0.45)
    mid = 0.5
    cf = 1.0 + 0.25 * s
    r = contrast_about_mid(r, cf, mid)
    g = contrast_about_mid(g, cf, mid)
    b = contrast_about_mid(b, cf, mid)
    arr_t = np.stack([r, g, b], axis=-1)
    wb = np.array([1.0 - 0.020 * s, 1.0 - 0.005 * s, 1.0 + 0.060 * s], dtype=np.float32)
    arr_t = apply_white_balance(arr_t, wb)
    antiR = 0.06 * s * hl
    arr_t = apply_channel_mul(arr_t, 0, (1.0 - antiR))
    blue_mask = blue_dominance_mask(arr_t, scale=2.0)
    desat_other = 0.06 * s * (1.0 - blue_mask)
    l2 = (0.2126 * arr_t[:, :, 0] + 0.7152 * arr_t[:, :, 1] + 0.0722 * arr_t[:, :, 2])
    arr_t = desaturate_to_gray_mask(arr_t, l2, desat_other)
    boost_b = 0.28 * s * blue_mask
    arr_t = apply_channel_mul(arr_t, 2, (1.0 + boost_b))
    l3 = (0.2126 * arr_t[:, :, 0] + 0.7152 * arr_t[:, :, 1] + 0.0722 * arr_t[:, :, 2])
    hl3 = np.clip((l3 - 0.55) / 0.45, 0.0, 1.0)
    sh3 = np.clip((0.45 - l3) / 0.45, 0.0, 1.0)
    c_boost = 0.20 * s
    arr_t = np.clip((arr_t - 0.5) * (1.0 + c_boost) + 0.5, 0.0, 1.0)
    arr_t = apply_scalar_gain_mask(arr_t, (1.0 + 0.10 * s * hl3))
    arr_t = apply_scalar_gain_mask(arr_t, (1.0 - 0.10 * s * sh3))
    arr_t = _apply_film_grain(arr_t, s, mid=0.5, sigma_base=0.008, sigma_slope=0.015, cw=[0.98, 1.00, 1.05])
    return float_rgb_to_image(arr_t)





def _filter_film_fuji_c100(img: Image.Image, strength: float) -> Image.Image:
    s = _clamp01(strength)
    if s <= 0:
        return img
    # Slightly lower global saturation first; we'll re-emphasize greens selectively
    color_f = _scale_factor(0.90, s)
    base = ImageEnhance.Color(img).enhance(color_f)

    arr = image_to_float_rgb(base)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    # Luminance and tone regions
    l = luminance_from_rgb(r, g, b)
    hl = mask_above(l, 0.55, 0.45)  # highlights
    sh = mask_below(l, 0.40, 0.40)  # shadows

    # Increase overall contrast (C100 has higher contrast)
    mid = 0.5
    cf = 1.0 + 0.44 * s
    r = contrast_about_mid(r, cf, mid)
    g = contrast_about_mid(g, cf, mid)
    b = contrast_about_mid(b, cf, mid)

    # Slightly cooler temperature (reduce R, increase B)
    wb = np.array([1.0 - 0.040 * s, 1.0, 1.0 + 0.100 * s], dtype=np.float32)
    arr_t = np.stack([r, g, b], axis=-1)
    arr_t = apply_white_balance(arr_t, wb)

    # Emphasize greens: boost green where it's relatively dominant; slightly pull R/B there
    green_mask = green_dominance_mask(arr_t, scale=2.0)
    boost_g = 0.56 * s * green_mask
    arr_t = apply_channel_mul(arr_t, 1, (1.0 + boost_g))
    arr_t = apply_channel_mul(arr_t, 0, (1.0 - 0.10 * s * green_mask))
    arr_t = apply_channel_mul(arr_t, 2, (1.0 - 0.06 * s * green_mask))

    # Slightly desaturate non-green areas so green hue stands out
    desat_other = 0.16 * s * (1.0 - green_mask)
    l2 = (0.2126 * arr_t[:, :, 0] + 0.7152 * arr_t[:, :, 1] + 0.0722 * arr_t[:, :, 2])
    arr_t = desaturate_to_gray_mask(arr_t, l2, desat_other)

    # Highlights push towards brighter/whiter
    l3 = (0.2126 * arr_t[:, :, 0] + 0.7152 * arr_t[:, :, 1] + 0.0722 * arr_t[:, :, 2])
    hl3 = np.clip((l3 - 0.55) / 0.45, 0.0, 1.0)
    lift_mul = 0.24 * s
    lift_add = 0.12 * s
    arr_t = apply_highlight_lift(arr_t, hl3, lift_mul=lift_mul, lift_add=lift_add)
    # Desaturate highlights slightly to appear more neutral/white
    l4 = (0.2126 * arr_t[:, :, 0] + 0.7152 * arr_t[:, :, 1] + 0.0722 * arr_t[:, :, 2])
    desat_hl = 0.20 * s * hl3
    arr_t = desaturate_to_gray_mask(arr_t, l4, desat_hl)

    # Shadows tint slightly green
    tint_sh = np.array([185.0/255.0, 215.0/255.0, 185.0/255.0], dtype=np.float32)
    a_sh = 0.32 * s
    arr_t = apply_tint_mask(arr_t, tint_sh, (a_sh * sh))

    # Fine film-like grain slightly stronger in mid/highs and a touch cooler
    arr_t = _apply_film_grain(arr_t, s, mid=0.55, sigma_base=0.016, sigma_slope=0.024, cw=[0.96, 1.00, 1.08])

    return float_rgb_to_image(arr_t)

def _filter_film_kodak_g200(img: Image.Image, strength: float) -> Image.Image:
    s = _clamp01(strength)
    if s <= 0:
        return img
    color_f = _scale_factor(1.08, s)
    base = ImageEnhance.Color(img).enhance(color_f)
    arr = image_to_float_rgb(base)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    l = luminance_from_rgb(r, g, b)
    hl = mask_above(l, 0.55, 0.45)
    sh = mask_below(l, 0.35, 0.35)
    mid = 0.5
    cf = 1.0 + 0.25 * s * (1.0 - hl)
    r = contrast_about_mid(r, cf, mid)
    g = contrast_about_mid(g, cf, mid)
    b = contrast_about_mid(b, cf, mid)
    wb = np.array([1.0 + 0.06 * s, 1.0 + 0.03 * s, 1.0 - 0.02 * s], dtype=np.float32)
    arr_t = np.stack([r, g, b], axis=-1)
    arr_t = apply_white_balance(arr_t, wb)
    l2 = (0.2126 * arr_t[:, :, 0] + 0.7152 * arr_t[:, :, 1] + 0.0722 * arr_t[:, :, 2])
    hl2 = np.clip((l2 - 0.5) / 0.5, 0.0, 1.0)
    warm_hl = np.array([1.0 + 0.10 * s, 1.0 + 0.06 * s, 1.0 - 0.02 * s], dtype=np.float32)
    arr_t = apply_rgb_gain_mask(arr_t, warm_hl, hl2)
    lift_mul = 0.12 * s
    lift_add = 0.05 * s
    arr_t = apply_highlight_lift(arr_t, hl2, lift_mul=lift_mul, lift_add=lift_add)
    tint_sh = np.array([210.0/255.0, 180.0/255.0, 160.0/255.0], dtype=np.float32)
    a_sh = 0.18 * s
    arr_t = apply_tint_mask(arr_t, tint_sh, (a_sh * sh))
    red_rel = red_dominance_mask(arr_t, scale=1.0)
    yellow_rel = yellow_dominance_mask(arr_t)
    boost_red = 0.25 * s * red_rel
    boost_yel = 0.22 * s * yellow_rel
    arr_t = apply_channel_mul(arr_t, 0, (1.0 + boost_red + 0.5 * boost_yel))
    arr_t = apply_channel_mul(arr_t, 1, (1.0 + boost_yel * 0.8))
    arr_t = _apply_film_grain(arr_t, s, mid=0.5, sigma_base=0.02, sigma_slope=0.03, cw=[1.02, 1.00, 0.98])
    return float_rgb_to_image(arr_t)

## LUT-related functionality removed for this release


FILTER_HANDLERS = {
    'none': _filter_none,
    'black_white': _filter_black_white,
    'vivid': _filter_vivid,
    'retro': _filter_retro,
    # 'film': _filter_film,
    # 'lut01': _filter_lut01,
    'film_kodak_5219': _filter_film_kodak_5219,
    'film_fuji_c100': _filter_film_fuji_c100,
    'film_kodak_g200': _filter_film_kodak_g200,
    'film_kodak_e100': _filter_film_kodak_e100,
}

# Dynamically add LUT filters lut01..lut15 without duplicating code
_lut_handlers = {
    f'lut{i:02d}': make_lut_filter(f'Titanium_Cinematic_{i:02d}.cube')
    for i in range(1, 16)
}
FILTER_HANDLERS.update(_lut_handlers)
print(FILTER_HANDLERS)

AVAILABLE_FILTER_KEYS = set(FILTER_HANDLERS.keys())


def apply_filter(img_input: Image.Image, filter_key: str, strength: float = 0.5) -> Image.Image:
    if img_input is None:
        return img_input
    key = (filter_key or 'none').strip().lower()
    img = img_input.convert('RGB')
    handler = FILTER_HANDLERS.get(key, FILTER_HANDLERS['none'])
    return handler(img, strength)


if __name__ == '__main__':
    img = Image.open(r'wxcloudrun\static\img_thumbnail\filter_film_kodak_g200.jpg')
    img = apply_lut(img, 1.0, 'cubes/Titanium_Cinematic_01.cube')
    img.save(r'test_lut.jpg')