"""Vectorized escape-time iteration for Mandelbrot / Julia fractals."""

from __future__ import annotations

import numpy as np

_REF_LIMIT = 1e6
_Z_LINEAR_CAP = 4.0


def escape_iter(
    c_re: np.ndarray,
    c_im: np.ndarray,
    max_iter: int,
    z0_re: np.ndarray | None = None,
    z0_im: np.ndarray | None = None,
    bailout: float = 4.0,
) -> np.ndarray:
    """
    Escape-time iteration over a complex grid.

    Mandelbrot (3 args): z0 = 0, c = per-pixel (c_re, c_im).
    Julia (5 args): z0 = per-pixel (z0_re, z0_im), c = constant (c_re, c_im).
    """
    max_iter = int(max_iter)
    bailout = float(bailout)

    cr = np.asarray(c_re, dtype=np.float64)
    ci = np.asarray(c_im, dtype=np.float64)

    if z0_re is None:
        zr = np.zeros_like(cr, dtype=np.float64)
        zi = np.zeros_like(ci, dtype=np.float64)
    else:
        zr = np.asarray(z0_re, dtype=np.float64)
        zi = np.asarray(z0_im, dtype=np.float64)
        if cr.shape == () or cr.size == 1:
            cr = np.full_like(zr, float(cr.ravel()[0]))
        if ci.shape == () or ci.size == 1:
            ci = np.full_like(zi, float(ci.ravel()[0]))

    esc = np.zeros(zr.shape, dtype=np.float64)
    mask = np.ones(zr.shape, dtype=bool)

    with np.errstate(over="ignore", invalid="ignore"):
        for n in range(max_iter):
            zr2 = zr * zr - zi * zi
            zi2 = 2.0 * zr * zi
            zr_new = zr2 + cr
            zi_new = zi2 + ci
            zr = np.where(mask, zr_new, zr)
            zi = np.where(mask, zi_new, zi)
            mag2 = zr * zr + zi * zi
            escaped = mask & ((mag2 > bailout) | ~np.isfinite(mag2))
            esc[escaped] = n + 1
            mask &= ~escaped
            if not np.any(mask):
                break

    esc[mask] = max_iter
    return esc


def burning_ship_iter(
    c_re: np.ndarray,
    c_im: np.ndarray,
    max_iter: int,
    bailout: float = 4.0,
) -> np.ndarray:
    """
    Burning Ship escape-time iteration: z = (|Re z| + i|Im z|)^2 + c, z0 = 0.
    """
    max_iter = int(max_iter)
    bailout = float(bailout)

    cr = np.asarray(c_re, dtype=np.float64)
    ci = np.asarray(c_im, dtype=np.float64)
    zr = np.zeros_like(cr, dtype=np.float64)
    zi = np.zeros_like(ci, dtype=np.float64)

    esc = np.zeros(zr.shape, dtype=np.float64)
    mask = np.ones(zr.shape, dtype=bool)

    with np.errstate(over="ignore", invalid="ignore"):
        for n in range(max_iter):
            ax = np.abs(zr)
            ay = np.abs(zi)
            zr2 = ax * ax - ay * ay
            zi2 = 2.0 * ax * ay
            zr_new = zr2 + cr
            zi_new = zi2 + ci
            zr = np.where(mask, zr_new, zr)
            zi = np.where(mask, zi_new, zi)
            mag2 = zr * zr + zi * zi
            escaped = mask & ((mag2 > bailout) | ~np.isfinite(mag2))
            esc[escaped] = n + 1
            mask &= ~escaped
            if not np.any(mask):
                break

    esc[mask] = max_iter
    return esc


def escape_perturb(
    anchor_re: float,
    anchor_im: float,
    dc_re: np.ndarray,
    dc_im: np.ndarray,
    max_iter: int,
    bailout: float = 4.0,
) -> np.ndarray:
    """
    Deep-zoom Mandelbrot via perturbation around a reference point.

    c = anchor + dc per pixel; dc should be small (e.g. dx / effective_scale).
    Falls back to direct escape_iter when the reference orbit overflows.
    """
    max_iter = int(max_iter)
    bailout = float(bailout)
    ar = float(anchor_re)
    ai = float(anchor_im)
    dr = np.asarray(dc_re, dtype=np.float64)
    di = np.asarray(dc_im, dtype=np.float64)

    Zr, Zi = 0.0, 0.0
    dzr = np.zeros_like(dr)
    dzi = np.zeros_like(di)
    esc = np.zeros(dr.shape, dtype=np.float64)
    mask = np.ones(dr.shape, dtype=bool)
    ref_ok = True

    with np.errstate(over="ignore", invalid="ignore"):
        for n in range(max_iter):
            if not ref_ok:
                break

            Zr2 = Zr * Zr - Zi * Zi + ar
            Zi2 = 2.0 * Zr * Zi + ai
            Zmag2 = Zr2 * Zr2 + Zi2 * Zi2
            if (
                not np.isfinite(Zmag2)
                or Zmag2 > bailout
                or abs(Zr2) > _REF_LIMIT
                or abs(Zi2) > _REF_LIMIT
                or abs(Zr2) > _Z_LINEAR_CAP
                or abs(Zi2) > _Z_LINEAR_CAP
            ):
                ref_ok = False
                break

            dzr_m = np.where(mask, dzr, 0.0)
            dzi_m = np.where(mask, dzi, 0.0)

            t1r = 2.0 * (Zr * dzr_m - Zi * dzi_m)
            t1i = 2.0 * (Zr * dzi_m + Zi * dzr_m)
            t2r = dzr_m * dzr_m - dzi_m * dzi_m
            t2i = 2.0 * dzr_m * dzi_m
            dzr_new = t1r + t2r + dr
            dzi_new = t1i + t2i + di

            zr = Zr2 + dzr_new
            zi = Zi2 + dzi_new
            mag2 = zr * zr + zi * zi
            escaped = mask & ((mag2 > bailout) | ~np.isfinite(mag2))
            esc[escaped] = n + 1
            mask &= ~escaped

            Zr, Zi = Zr2, Zi2
            dzr = np.where(mask, dzr_new, 0.0)
            dzi = np.where(mask, dzi_new, 0.0)

            if not np.any(mask):
                break

    if np.any(mask):
        full = escape_iter(ar + dr, ai + di, max_iter)
        esc[mask] = full[mask]

    return esc


def escape_zoom(
    anchor_re: float,
    anchor_im: float,
    dc_re: np.ndarray,
    dc_im: np.ndarray,
    max_iter: int,
    dc_threshold: float = 0.002,
    bailout: float = 4.0,
) -> np.ndarray:
    """Mandelbrot deep zoom: direct eval when |dc| is large, perturbation when tiny."""
    dr = np.asarray(dc_re, dtype=np.float64)
    di = np.asarray(dc_im, dtype=np.float64)
    if np.max(np.abs(dr)) > dc_threshold or np.max(np.abs(di)) > dc_threshold:
        return escape_iter(anchor_re + dr, anchor_im + di, max_iter, bailout=bailout)
    return escape_perturb(anchor_re, anchor_im, dr, di, max_iter, bailout=bailout)
