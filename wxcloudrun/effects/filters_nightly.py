from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from pathlib import Path
import numpy as np
import pylut
import time

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

def _apply_film_grain(arr_t, s, mid, sigma_base, sigma_slope, cw):
    if s <= 0:
        return arr_t
    h, w, _ = arr_t.shape
    l_hw = (0.2126 * arr_t[:, :, 0] + 0.7152 * arr_t[:, :, 1] + 0.0722 * arr_t[:, :, 2])
    w_mid = 1.0 - np.clip(np.abs(l_hw - mid) * 2.0, 0.0, 1.0)
    sigma = sigma_base + sigma_slope * s
    noise = np.random.normal(0.0, sigma, size=(h, w, 1)).astype(np.float32)
    noise = noise * w_mid[:, :, None]
    cw_arr = np.array(cw, dtype=np.float32)
    noise = np.repeat(noise, 3, axis=2) * cw_arr[None, None, :]
    return np.clip(arr_t + noise, 0.0, 1.0)

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
    arr = np.array(base, dtype=np.float32) / 255.0
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    l = 0.2126 * r + 0.7152 * g + 0.0722 * b
    hl = np.clip((l - 0.55) / 0.45, 0.0, 1.0)
    sh = np.clip((0.35 - l) / 0.35, 0.0, 1.0)
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
    h_, w_, _ = arr_t.shape
    arr_t = arr_t.reshape(-1, 3) @ m.T
    arr_t = arr_t.reshape(h_, w_, 3)
    arr_t = np.clip(arr_t, 0.0, 1.0)
    arr_t = _apply_film_grain(arr_t, s, mid=0.5, sigma_base=0.06, sigma_slope=0.08, cw=[0.95, 1.00, 1.18])
    if s > 0:
        h, w, _ = arr_t.shape
        yy, xx = np.ogrid[:h, :w]
        cx = (w - 1) * 0.5
        cy = (h - 1) * 0.5
        dx = (xx - cx) / (0.5 * w + 1e-6)
        dy = (yy - cy) / (0.5 * h + 1e-6)
        rad = np.sqrt(dx * dx + dy * dy)
        mask = np.clip((rad - 0.2) / 0.8, 0.0, 1.0)
        mask = mask * mask
        v = 0.45 * s
        v_mult = 1.0 - v * mask
        arr_t = np.clip(arr_t * v_mult[..., None], 0.0, 1.0)
    out = (arr_t * 255.0 + 0.5).astype('uint8')
    return Image.fromarray(out, mode='RGB')


def _filter_film_kodak_e100(img: Image.Image, strength: float) -> Image.Image:
    s = _clamp01(strength)
    if s <= 0:
        return img
    color_f = _scale_factor(0.95, s)
    base = ImageEnhance.Color(img).enhance(color_f)
    arr = np.array(base, dtype=np.float32) / 255.0
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    l = 0.2126 * r + 0.7152 * g + 0.0722 * b
    hl = np.clip((l - 0.55) / 0.45, 0.0, 1.0)
    mid = 0.5
    cf = 1.0 + 0.25 * s
    r = mid + (r - mid) * cf
    g = mid + (g - mid) * cf
    b = mid + (b - mid) * cf
    arr_t = np.stack([r, g, b], axis=-1)
    wb = np.array([1.0 - 0.020 * s, 1.0 - 0.005 * s, 1.0 + 0.060 * s], dtype=np.float32)
    arr_t = np.clip(arr_t * wb[None, None, :], 0.0, 1.0)
    antiR = 0.06 * s * hl
    arr_t[:, :, 0] = np.clip(arr_t[:, :, 0] * (1.0 - antiR), 0.0, 1.0)
    r2 = arr_t[:, :, 0]
    g2 = arr_t[:, :, 1]
    b2 = arr_t[:, :, 2]
    blue_rel = b2 - 0.5 * (r2 + g2)
    blue_mask = np.clip(blue_rel * 2.0, 0.0, 1.0)
    desat_other = 0.06 * s * (1.0 - blue_mask)
    l2 = (0.2126 * r2 + 0.7152 * g2 + 0.0722 * b2)
    arr_t[:, :, 0] = arr_t[:, :, 0] * (1.0 - desat_other) + l2 * desat_other
    arr_t[:, :, 1] = arr_t[:, :, 1] * (1.0 - desat_other) + l2 * desat_other
    arr_t[:, :, 2] = arr_t[:, :, 2] * (1.0 - desat_other) + l2 * desat_other
    boost_b = 0.28 * s * blue_mask
    arr_t[:, :, 2] = np.clip(arr_t[:, :, 2] * (1.0 + boost_b), 0.0, 1.0)
    l3 = (0.2126 * arr_t[:, :, 0] + 0.7152 * arr_t[:, :, 1] + 0.0722 * arr_t[:, :, 2])
    hl3 = np.clip((l3 - 0.55) / 0.45, 0.0, 1.0)
    sh3 = np.clip((0.45 - l3) / 0.45, 0.0, 1.0)
    c_boost = 0.20 * s
    arr_t = np.clip((arr_t - 0.5) * (1.0 + c_boost) + 0.5, 0.0, 1.0)
    arr_t = np.clip(arr_t * (1.0 + 0.10 * s * hl3[..., None]), 0.0, 1.0)
    arr_t = np.clip(arr_t * (1.0 - 0.10 * s * sh3[..., None]), 0.0, 1.0)
    arr_t = _apply_film_grain(arr_t, s, mid=0.5, sigma_base=0.008, sigma_slope=0.015, cw=[0.98, 1.00, 1.05])
    out = (arr_t * 255.0 + 0.5).astype('uint8')
    return Image.fromarray(out, mode='RGB')





def _filter_film_fuji_c100(img: Image.Image, strength: float) -> Image.Image:
    s = _clamp01(strength)
    if s <= 0:
        return img
    # Slightly lower global saturation first; we'll re-emphasize greens selectively
    color_f = _scale_factor(0.90, s)
    base = ImageEnhance.Color(img).enhance(color_f)

    arr = np.array(base, dtype=np.float32) / 255.0
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    # Luminance and tone regions
    l = 0.2126 * r + 0.7152 * g + 0.0722 * b
    hl = np.clip((l - 0.55) / 0.45, 0.0, 1.0)  # highlights
    sh = np.clip((0.40 - l) / 0.40, 0.0, 1.0)  # shadows

    # Increase overall contrast (C100 has higher contrast)
    mid = 0.5
    cf = 1.0 + 0.44 * s
    r = mid + (r - mid) * cf
    g = mid + (g - mid) * cf
    b = mid + (b - mid) * cf

    # Slightly cooler temperature (reduce R, increase B)
    wb = np.array([1.0 - 0.040 * s, 1.0, 1.0 + 0.100 * s], dtype=np.float32)
    arr_t = np.stack([r, g, b], axis=-1)
    arr_t = np.clip(arr_t * wb[None, None, :], 0.0, 1.0)

    # Emphasize greens: boost green where it's relatively dominant; slightly pull R/B there
    r2 = arr_t[:, :, 0]
    g2 = arr_t[:, :, 1]
    b2 = arr_t[:, :, 2]
    green_rel = g2 - 0.5 * (r2 + b2)
    green_mask = np.clip(green_rel * 2.0, 0.0, 1.0)
    boost_g = 0.56 * s * green_mask
    arr_t[:, :, 1] = np.clip(g2 * (1.0 + boost_g), 0.0, 1.0)
    arr_t[:, :, 0] = np.clip(r2 * (1.0 - 0.10 * s * green_mask), 0.0, 1.0)
    arr_t[:, :, 2] = np.clip(b2 * (1.0 - 0.06 * s * green_mask), 0.0, 1.0)

    # Slightly desaturate non-green areas so green hue stands out
    r3 = arr_t[:, :, 0]
    g3 = arr_t[:, :, 1]
    b3 = arr_t[:, :, 2]
    l2 = (0.2126 * r3 + 0.7152 * g3 + 0.0722 * b3)
    desat_other = 0.16 * s * (1.0 - green_mask)
    arr_t[:, :, 0] = r3 * (1.0 - desat_other) + l2 * desat_other
    arr_t[:, :, 1] = g3 * (1.0 - desat_other) + l2 * desat_other
    arr_t[:, :, 2] = b3 * (1.0 - desat_other) + l2 * desat_other

    # Highlights push towards brighter/whiter
    l3 = (0.2126 * arr_t[:, :, 0] + 0.7152 * arr_t[:, :, 1] + 0.0722 * arr_t[:, :, 2])
    hl3 = np.clip((l3 - 0.55) / 0.45, 0.0, 1.0)
    lift_mul = 0.24 * s
    lift_add = 0.12 * s
    arr_t = np.clip(arr_t * (1.0 + lift_mul * hl3[..., None]) + lift_add * hl3[..., None], 0.0, 1.0)
    # Desaturate highlights slightly to appear more neutral/white
    l4 = (0.2126 * arr_t[:, :, 0] + 0.7152 * arr_t[:, :, 1] + 0.0722 * arr_t[:, :, 2])
    desat_hl = 0.20 * s * hl3
    arr_t[:, :, 0] = arr_t[:, :, 0] * (1.0 - desat_hl) + l4 * desat_hl
    arr_t[:, :, 1] = arr_t[:, :, 1] * (1.0 - desat_hl) + l4 * desat_hl
    arr_t[:, :, 2] = arr_t[:, :, 2] * (1.0 - desat_hl) + l4 * desat_hl

    # Shadows tint slightly green
    tint_sh = np.array([185.0/255.0, 215.0/255.0, 185.0/255.0], dtype=np.float32)
    a_sh = 0.32 * s
    arr_t[:, :, 0] = arr_t[:, :, 0] * (1.0 - a_sh * sh) + tint_sh[0] * (a_sh * sh)
    arr_t[:, :, 1] = arr_t[:, :, 1] * (1.0 - a_sh * sh) + tint_sh[1] * (a_sh * sh)
    arr_t[:, :, 2] = arr_t[:, :, 2] * (1.0 - a_sh * sh) + tint_sh[2] * (a_sh * sh)

    # Fine film-like grain slightly stronger in mid/highs and a touch cooler
    arr_t = _apply_film_grain(arr_t, s, mid=0.55, sigma_base=0.016, sigma_slope=0.024, cw=[0.96, 1.00, 1.08])

    out = (arr_t * 255.0 + 0.5).astype('uint8')
    return Image.fromarray(out, mode='RGB')

def _filter_film_kodak_g200(img: Image.Image, strength: float) -> Image.Image:
    s = _clamp01(strength)
    if s <= 0:
        return img
    color_f = _scale_factor(1.08, s)
    base = ImageEnhance.Color(img).enhance(color_f)
    arr = np.array(base, dtype=np.float32) / 255.0
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    l = 0.2126 * r + 0.7152 * g + 0.0722 * b
    hl = np.clip((l - 0.55) / 0.45, 0.0, 1.0)
    sh = np.clip((0.35 - l) / 0.35, 0.0, 1.0)
    mid = 0.5
    cf = 1.0 + 0.25 * s * (1.0 - hl)
    r = mid + (r - mid) * cf
    g = mid + (g - mid) * cf
    b = mid + (b - mid) * cf
    wb = np.array([1.0 + 0.06 * s, 1.0 + 0.03 * s, 1.0 - 0.02 * s], dtype=np.float32)
    arr_t = np.stack([r, g, b], axis=-1)
    arr_t = np.clip(arr_t * wb[None, None, :], 0.0, 1.0)
    l2 = (0.2126 * arr_t[:, :, 0] + 0.7152 * arr_t[:, :, 1] + 0.0722 * arr_t[:, :, 2])
    hl2 = np.clip((l2 - 0.5) / 0.5, 0.0, 1.0)
    warm_hl = np.array([1.0 + 0.10 * s, 1.0 + 0.06 * s, 1.0 - 0.02 * s], dtype=np.float32)
    arr_t = np.clip(arr_t * (1.0 + (warm_hl[None, None, :] - 1.0) * hl2[..., None]), 0.0, 1.0)
    lift_mul = 0.12 * s
    lift_add = 0.05 * s
    arr_t = np.clip(arr_t * (1.0 + lift_mul * hl2[..., None]) + lift_add * hl2[..., None], 0.0, 1.0)
    tint_sh = np.array([210.0/255.0, 180.0/255.0, 160.0/255.0], dtype=np.float32)
    a_sh = 0.18 * s
    arr_t[:, :, 0] = arr_t[:, :, 0] * (1.0 - a_sh * sh) + tint_sh[0] * (a_sh * sh)
    arr_t[:, :, 1] = arr_t[:, :, 1] * (1.0 - a_sh * sh) + tint_sh[1] * (a_sh * sh)
    arr_t[:, :, 2] = arr_t[:, :, 2] * (1.0 - a_sh * sh) + tint_sh[2] * (a_sh * sh)
    r2 = arr_t[:, :, 0]
    g2 = arr_t[:, :, 1]
    b2 = arr_t[:, :, 2]
    red_rel = np.clip(r2 - 0.5 * (g2 + b2), 0.0, 1.0)
    yellow_rel = np.clip(np.minimum(r2, g2) - b2, 0.0, 1.0)
    boost_red = 0.25 * s * red_rel
    boost_yel = 0.22 * s * yellow_rel
    arr_t[:, :, 0] = np.clip(arr_t[:, :, 0] * (1.0 + boost_red + 0.5 * boost_yel), 0.0, 1.0)
    arr_t[:, :, 1] = np.clip(arr_t[:, :, 1] * (1.0 + boost_yel * 0.8), 0.0, 1.0)
    arr_t = _apply_film_grain(arr_t, s, mid=0.5, sigma_base=0.02, sigma_slope=0.03, cw=[1.02, 1.00, 0.98])
    out = (arr_t * 255.0 + 0.5).astype('uint8')
    return Image.fromarray(out, mode='RGB')

def _filter_lut01(img: Image.Image, strength: float) -> Image.Image:
    s = _clamp01(strength)
    if s <= 0:
        return img
    return _apply_lut(img, s, 'cubes/Titanium_Cinematic_01.cube')

def _apply_lut(img: Image.Image, s: float, cube_rel_path: str) -> Image.Image:
    base = img.convert('RGB')
    arr = np.array(base, dtype=np.float32) / 255.0
    this_file = Path(__file__).resolve()
    repo_root = this_file.parents[2]
    lut_path = repo_root / cube_rel_path
    t0 = time.time()
    lut = pylut.LUT.FromCubeFile(str(lut_path)) 
    t1 = time.time()
    print(f"[apply_lut] loaded LUT '{lut_path.name}' in {t1 - t0:.3f}s")

    h, w, _ = arr.shape
    flat = arr.reshape(-1, 3)
    out_list = []
    for rgb in flat:
        c = pylut.Color.FromFloatArray(rgb)
        c2 = lut.ColorFromColor(c)
        out_list.append(c2.ToFloatArray())
    arr_lut = np.array(out_list, dtype=np.float32).reshape(h, w, 3)
    t3 = time.time()
    print(f"[apply_lut] remap done in {t3 - t1:.3f}s (total {t3 - t0:.3f}s so far)")
    out = np.clip(arr * (1.0 - s) + arr_lut * s, 0.0, 1.0)
    out_u8 = (out * 255.0 + 0.5).astype('uint8')
    t4 = time.time()
    print(f"[apply_lut] blend/convert done in {t4 - t3:.3f}s (total {t4 - t0:.3f}s)")
    return Image.fromarray(out_u8, mode='RGB')

def _make_lut_filter(cube_filename: str):
    def _f(img: Image.Image, strength: float) -> Image.Image:
        return _apply_lut(img, _clamp01(strength), f'cubes/{cube_filename}')
    return _f

FILTER_HANDLERS = {
    'none': _filter_none,
    # 'black_white': _filter_black_white,
    # 'vivid': _filter_vivid,
    # 'retro': _filter_retro,
    # 'film': _filter_film,
    # 'lut01': _filter_lut01,
    'film_kodak_5219': _filter_film_kodak_5219,
    'film_fuji_c100': _filter_film_fuji_c100,
    'film_kodak_g200': _filter_film_kodak_g200,
    'film_kodak_e100': _filter_film_kodak_e100,
}

# Dynamically add LUT filters lut01..lut15 without duplicating code
_lut_handlers = {
    f'lut{i:02d}': _make_lut_filter(f'Titanium_Cinematic_{i:02d}.cube')
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
