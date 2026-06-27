# self-host lut file
# dict pre-load is applied 

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np


@dataclass(frozen=True)
class CubeLUT:
    size: int
    table: np.ndarray
    domain_min: np.ndarray
    domain_max: np.ndarray


_CUBE_CACHE: dict[str, CubeLUT] = {}


def load_cube_lut(cube_path: str | Path) -> CubeLUT:
    p = Path(cube_path)
    key = str(p.resolve())
    cached = _CUBE_CACHE.get(key)
    if cached is not None:
        return cached

    size = None
    domain_min = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    domain_max = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    data: list[list[float]] = []

    with p.open('r', encoding='utf-8', errors='ignore') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if line.upper().startswith('TITLE'):
                continue
            if line.upper().startswith('LUT_3D_SIZE'):
                parts = line.split()
                size = int(parts[-1])
                continue
            if line.upper().startswith('DOMAIN_MIN'):
                parts = line.split()
                domain_min = np.array([float(parts[-3]), float(parts[-2]), float(parts[-1])], dtype=np.float32)
                continue
            if line.upper().startswith('DOMAIN_MAX'):
                parts = line.split()
                domain_max = np.array([float(parts[-3]), float(parts[-2]), float(parts[-1])], dtype=np.float32)
                continue

            parts = line.split()
            if len(parts) >= 3:
                data.append([float(parts[0]), float(parts[1]), float(parts[2])])

    if size is None:
        raise ValueError(f"Invalid .cube file (missing LUT_3D_SIZE): {p}")

    expected = size * size * size
    if len(data) < expected:
        raise ValueError(f"Invalid .cube file (data lines {len(data)} < expected {expected}): {p}")

    arr = np.asarray(data[:expected], dtype=np.float32)
    # .cube standard order: B fastest, then G, then R.
    # So reshape as [R][G][B][3] via (R, G, B, 3) with B as the last varying axis.
    table = arr.reshape((size, size, size, 3))

    lut = CubeLUT(size=size, table=table, domain_min=domain_min, domain_max=domain_max)
    _CUBE_CACHE[key] = lut
    return lut


def apply_cube_lut_float_rgb(arr_t: np.ndarray, lut: CubeLUT) -> np.ndarray:
    if arr_t.ndim != 3 or arr_t.shape[2] != 3:
        raise ValueError('arr_t must be HxWx3 float array')

    h, w, _ = arr_t.shape
    flat = arr_t.reshape(-1, 3).astype(np.float32, copy=False)

    dom_min = lut.domain_min
    dom_max = lut.domain_max
    dom_range = np.maximum(dom_max - dom_min, np.float32(1e-12))
    x = (flat - dom_min[None, :]) / dom_range[None, :]
    x = np.clip(x, 0.0, 1.0)
    # Avoid x==1.0 edge producing i1==size.
    one_minus = np.nextafter(np.float32(1.0), np.float32(0.0))
    x = np.minimum(x, one_minus)

    n = lut.size
    scaled = x * np.float32(n - 1)
    i0 = np.floor(scaled).astype(np.int32)
    f = scaled - i0.astype(np.float32)
    i1 = np.minimum(i0 + 1, n - 1)

    # .cube BGR-fastest order: table is [B][G][R][3]
    b0, g0, r0 = i0[:, 2], i0[:, 1], i0[:, 0]
    b1, g1, r1 = i1[:, 2], i1[:, 1], i1[:, 0]
    fb, fg, fr = f[:, 2:3], f[:, 1:2], f[:, 0:1]

    t = lut.table
    c000 = t[b0, g0, r0]
    c001 = t[b0, g0, r1]
    c010 = t[b0, g1, r0]
    c011 = t[b0, g1, r1]
    c100 = t[b1, g0, r0]
    c101 = t[b1, g0, r1]
    c110 = t[b1, g1, r0]
    c111 = t[b1, g1, r1]

    c00 = c000 * (1.0 - fr) + c001 * fr
    c01 = c010 * (1.0 - fr) + c011 * fr
    c10 = c100 * (1.0 - fr) + c101 * fr
    c11 = c110 * (1.0 - fr) + c111 * fr
    c0 = c00 * (1.0 - fg) + c01 * fg
    c1 = c10 * (1.0 - fg) + c11 * fg
    out = c0 * (1.0 - fb) + c1 * fb

    return out.reshape(h, w, 3)


def apply_cube_lut(arr_t: np.ndarray, lut: CubeLUT, strength: float = 1.0) -> np.ndarray:
    s = float(strength)
    if s <= 0:
        return arr_t
    if s >= 1:
        return apply_cube_lut_float_rgb(arr_t, lut)
    mapped = apply_cube_lut_float_rgb(arr_t, lut)
    return np.clip(arr_t * (1.0 - s) + mapped * s, 0.0, 1.0)