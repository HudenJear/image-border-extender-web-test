from PIL import Image
from pathlib import Path
import numpy as np
import time


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def scale_factor(base_at_half: float, strength: float) -> float:
    """
    Map strength in [0,1] to a multiplicative factor.
    - 0.5 => base_at_half (existing baseline)
    - 1.0 => 1 + (base_at_half-1)*2
    - 0.0 => 1.0
    """
    s = clamp01(strength)
    k = s / 0.5 if s > 0 else 0.0
    return 1.0 + (base_at_half - 1.0) * k


def image_to_float_rgb(img: Image.Image) -> np.ndarray:
    return np.array(img, dtype=np.float32) / 255.0


def float_rgb_to_image(arr_t: np.ndarray) -> Image.Image:
    out = (np.clip(arr_t, 0.0, 1.0) * 255.0 + 0.5).astype('uint8')
    return Image.fromarray(out, mode='RGB')


def luminance_from_rgb(r: np.ndarray, g: np.ndarray, b: np.ndarray) -> np.ndarray:
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def mask_above(l: np.ndarray, start: float, width: float) -> np.ndarray:
    return np.clip((l - start) / width, 0.0, 1.0)


def mask_below(l: np.ndarray, cutoff: float, width: float) -> np.ndarray:
    return np.clip((cutoff - l) / width, 0.0, 1.0)


def contrast_about_mid(x: np.ndarray, factor: float, mid: float = 0.5) -> np.ndarray:
    return mid + (x - mid) * factor


def apply_white_balance(arr_t: np.ndarray, wb: np.ndarray) -> np.ndarray:
    return np.clip(arr_t * wb[None, None, :], 0.0, 1.0)


def apply_rgb_gain_mask(arr_t: np.ndarray, gains_rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    m = mask[..., None]
    return np.clip(arr_t * (1.0 + (gains_rgb[None, None, :] - 1.0) * m), 0.0, 1.0)


def apply_scalar_gain_mask(arr_t: np.ndarray, gain: np.ndarray) -> np.ndarray:
    return np.clip(arr_t * gain[..., None], 0.0, 1.0)


def apply_channel_mul(arr_t: np.ndarray, channel: int, mul: np.ndarray) -> np.ndarray:
    out = arr_t.copy()
    out[:, :, channel] = np.clip(out[:, :, channel] * mul, 0.0, 1.0)
    return out


def apply_tint_mask(arr_t: np.ndarray, tint_rgb: np.ndarray, alpha_mask: np.ndarray) -> np.ndarray:
    a = alpha_mask[..., None]
    return arr_t * (1.0 - a) + tint_rgb[None, None, :] * a


def desaturate_to_gray_mask(arr_t: np.ndarray, gray: np.ndarray, amount_mask: np.ndarray) -> np.ndarray:
    a = amount_mask[..., None]
    g = gray[..., None]
    return arr_t * (1.0 - a) + g * a


def luminance_from_arr(arr_t: np.ndarray) -> np.ndarray:
    return luminance_from_rgb(arr_t[:, :, 0], arr_t[:, :, 1], arr_t[:, :, 2])


def channel_dominance_mask(primary: np.ndarray, other1: np.ndarray, other2: np.ndarray, scale: float = 2.0) -> np.ndarray:
    return np.clip((primary - 0.5 * (other1 + other2)) * scale, 0.0, 1.0)


def green_dominance_mask(arr_t: np.ndarray, scale: float = 2.0) -> np.ndarray:
    r = arr_t[:, :, 0]
    g = arr_t[:, :, 1]
    b = arr_t[:, :, 2]
    return channel_dominance_mask(g, r, b, scale=scale)


def blue_dominance_mask(arr_t: np.ndarray, scale: float = 2.0) -> np.ndarray:
    r = arr_t[:, :, 0]
    g = arr_t[:, :, 1]
    b = arr_t[:, :, 2]
    return channel_dominance_mask(b, r, g, scale=scale)


def red_dominance_mask(arr_t: np.ndarray, scale: float = 1.0) -> np.ndarray:
    r = arr_t[:, :, 0]
    g = arr_t[:, :, 1]
    b = arr_t[:, :, 2]
    return channel_dominance_mask(r, g, b, scale=scale)


def yellow_dominance_mask(arr_t: np.ndarray) -> np.ndarray:
    r = arr_t[:, :, 0]
    g = arr_t[:, :, 1]
    b = arr_t[:, :, 2]
    return np.clip(np.minimum(r, g) - b, 0.0, 1.0)


def apply_matrix_3x3(arr_t: np.ndarray, m: np.ndarray) -> np.ndarray:
    h_, w_, _ = arr_t.shape
    out = arr_t.reshape(-1, 3) @ m.T
    return out.reshape(h_, w_, 3)


def apply_highlight_lift(arr_t: np.ndarray, hl: np.ndarray, lift_mul: float, lift_add: float) -> np.ndarray:
    return np.clip(arr_t * (1.0 + lift_mul * hl[..., None]) + lift_add * hl[..., None], 0.0, 1.0)


def apply_film_grain(arr_t, s, mid, sigma_base, sigma_slope, cw, downsample: int = 4):
    if s <= 0:
        return arr_t
    h, w, _ = arr_t.shape
    l_hw = (0.2126 * arr_t[:, :, 0] + 0.7152 * arr_t[:, :, 1] + 0.0722 * arr_t[:, :, 2])
    w_mid = 1.0 - np.clip(np.abs(l_hw - mid) * 2.0, 0.0, 1.0)
    sigma = sigma_base + sigma_slope * s
    ds = 1 if downsample is None else int(downsample)
    if ds < 1:
        ds = 1
    lh = max(1, h // ds)
    lw = max(1, w // ds)
    noise_lr = np.random.normal(0.0, sigma, size=(lh, lw, 1)).astype(np.float32)
    rep_h = int(np.ceil(h / lh))
    rep_w = int(np.ceil(w / lw))
    noise = np.repeat(np.repeat(noise_lr, rep_h, axis=0), rep_w, axis=1)[:h, :w, :]
    noise = noise * w_mid[:, :, None]
    cw_arr = np.array(cw, dtype=np.float32)
    noise3 = noise * cw_arr[None, None, :]
    return np.clip(arr_t + noise3, 0.0, 1.0)


def apply_vignette(arr_t: np.ndarray, s: float, inner: float = 0.2, outer: float = 0.8, amount: float = 0.45) -> np.ndarray:
    if s <= 0:
        return arr_t
    h, w, _ = arr_t.shape
    yy, xx = np.ogrid[:h, :w]
    cx = (w - 1) * 0.5
    cy = (h - 1) * 0.5
    dx = (xx - cx) / (0.5 * w + 1e-6)
    dy = (yy - cy) / (0.5 * h + 1e-6)
    rad = np.sqrt(dx * dx + dy * dy)
    mask = np.clip((rad - inner) / outer, 0.0, 1.0)
    mask = mask * mask
    v = amount * s
    v_mult = 1.0 - v * mask
    return np.clip(arr_t * v_mult[..., None], 0.0, 1.0)


def apply_lut(img: Image.Image, s: float, cube_rel_path: str) -> Image.Image:
    import pylut

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


def make_lut_filter(cube_filename: str):
    def _f(img: Image.Image, strength: float) -> Image.Image:
        return apply_lut(img, clamp01(strength), f'cubes/{cube_filename}')
    return _f
