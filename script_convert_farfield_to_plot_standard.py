"""
Convert CST farfield TXT export to one .plot matrix file.

Coordinate systems
------------------

CST (Image 1):
  - Z_cst : along antenna longitudinal axis (beam direction)
  - X_cst : transverse horizontal
  - Y_cst : vertical (up)
  - theta_cst in [0, 180] measured from Z_cst
  - phi_cst   in [0, 360) measured from X_cst

Article / math standard (Fig. 4):
  - Z_art : vertical (up)  — theta measured from this axis
  - X_art : longitudinal antenna axis (horizontal)
  - Y_art : transverse horizontal
  - theta_art in [0, 90]
  - phi_art   in (-180, 180]

Axis mapping (CST Cartesian -> Article Cartesian):
  X_art = Y_cst   (longitudinal — antenna lies along Y in CST)
  Y_art = X_cst   (transverse horizontal)
  Z_art = Z_cst   (vertical — Z is up in both systems)

WHY INTERPOLATION IS REQUIRED
------------------------------
The CST grid (integer theta_cst x integer phi_cst) maps to an
IRREGULAR scatter of (theta_art, phi_art) points — not a regular grid.
Direct binning leaves most cells empty (nan).
Solution: scatter -> scipy.interpolate.griddata -> regular article grid.
"""

import argparse
import glob
import os
from typing import List, Tuple

import numpy as np
from scipy.interpolate import griddata


# ---------------------------------------------------------------------------
# Coordinate transform
# ---------------------------------------------------------------------------

def cst_to_article_cartesian(
    theta_cst_deg: np.ndarray,
    phi_cst_deg: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """CST spherical -> Article Cartesian (vectorised)."""
    th = np.deg2rad(theta_cst_deg)
    ph = np.deg2rad(phi_cst_deg)

    x_cst = np.sin(th) * np.cos(ph)
    y_cst = np.sin(th) * np.sin(ph)
    z_cst = np.cos(th)

    # Axis permutation
    x_art = y_cst   # longitudinal antenna axis (antenna along Y in CST)
    y_art = x_cst   # transverse horizontal
    z_art = z_cst   # vertical (Z is up in both systems)

    return x_art, y_art, z_art


def cartesian_to_article_spherical(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Article Cartesian -> article spherical (theta in [0,180], phi in (-180,180])."""
    r = np.sqrt(x**2 + y**2 + z**2)
    theta = np.rad2deg(np.arccos(np.clip(z / r, -1.0, 1.0)))
    phi = np.rad2deg(np.arctan2(y, x))

    # Wrap phi to (-180, 180]
    phi = ((phi + 180.0) % 360.0) - 180.0
    phi = np.where(phi == -180.0, 180.0, phi)

    return theta, phi


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def build_output_name(input_file: str) -> str:
    base, _ = os.path.splitext(input_file)
    return base + ".raw.txt.plot"


def find_farfield_files(directory: str) -> List[str]:
    patterns = [
        os.path.join(directory, "*_farfield*.txt"),
        os.path.join(directory, "*farfield*.txt"),
        os.path.join(directory, "*.txt"),
    ]
    files: List[str] = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    return sorted(set(files))


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def parse_farfield_file(
    input_file: str,
    output_file: str,
    theta_max: float = 90.0,
    normalize: bool = True,
    value_column: int = 2,
    theta_step: float = 1.0,
    phi_step: float = 1.0,
    interp_method: str = "linear",
) -> None:
    """
    Parse one CST farfield TXT, transform coordinates, interpolate onto
    a regular article grid, and write a .plot matrix.

    Output matrix layout:
      rows  = phi_art  values (sorted ascending, from -180 to +180)
      cols  = theta_art values (sorted ascending, from 0 to theta_max)
    """
    # ---- read raw data ---------------------------------------------------
    rows_cst = []
    in_table = False

    with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith("---"):
                in_table = True
                continue
            if not in_table:
                continue
            parts = s.split()
            if len(parts) <= value_column:
                continue
            try:
                rows_cst.append((float(parts[0]), float(parts[1]), float(parts[value_column])))
            except ValueError:
                continue

    if not rows_cst:
        raise RuntimeError(f"No numeric rows found in: {input_file}")

    theta_cst = np.array([r[0] for r in rows_cst])
    phi_cst   = np.array([r[1] for r in rows_cst])
    values    = np.array([r[2] for r in rows_cst])

    # ---- transform to article spherical ----------------------------------
    x_art, y_art, z_art = cst_to_article_cartesian(theta_cst, phi_cst)
    theta_art, phi_art  = cartesian_to_article_spherical(x_art, y_art, z_art)

    # ---- filter to upper hemisphere --------------------------------------
    mask = (theta_art >= 0.0) & (theta_art <= theta_max)
    theta_art = theta_art[mask]
    phi_art   = phi_art[mask]
    values    = values[mask]

    if len(values) == 0:
        raise RuntimeError(
            f"All rows filtered out. Try --theta-max 180."
        )

    # ---- build regular output grid ---------------------------------------
    theta_grid_vals = np.arange(0.0, theta_max + theta_step * 0.5, theta_step)
    phi_grid_vals   = np.arange(-180.0, 180.0 + phi_step * 0.5, phi_step)

    # Clip to avoid floating-point overshoot
    theta_grid_vals = theta_grid_vals[theta_grid_vals <= theta_max + 1e-9]
    phi_grid_vals   = phi_grid_vals[phi_grid_vals <= 180.0 + 1e-9]

    THETA_GRID, PHI_GRID = np.meshgrid(theta_grid_vals, phi_grid_vals)  # (n_phi, n_theta)

    # ---- interpolate scatter -> grid -------------------------------------
    # For phi near ±180 boundary: duplicate points shifted by ±360 to avoid edge artifacts
    phi_ext   = np.concatenate([phi_art - 360.0, phi_art, phi_art + 360.0])
    theta_ext = np.tile(theta_art, 3)
    values_ext = np.tile(values, 3)

    points  = np.column_stack([theta_ext, phi_ext])
    grid_values = griddata(
        points,
        values_ext,
        (THETA_GRID, PHI_GRID),
        method=interp_method,
        fill_value=np.nan,
    )

    # ---- normalize -------------------------------------------------------
    max_value = float(np.nanmax(values))
    if normalize:
        if max_value == 0.0:
            raise RuntimeError("Cannot normalize: max value is 0.")
        grid_values = grid_values / max_value

    # ---- write output ----------------------------------------------------
    with open(output_file, "w", encoding="utf-8") as out:
        for row in grid_values:
            out.write(" ".join("nan" if np.isnan(v) else f"{v:.6e}" for v in row) + "\n")

    # ---- report ----------------------------------------------------------
    nan_count = int(np.sum(np.isnan(grid_values)))
    total_cells = grid_values.size
    output_max = 1.0 if normalize else max_value

    print("Done")
    print(f"  Input          : {input_file}")
    print(f"  Output         : {output_file}")
    print(f"  Scatter points : {len(values)}")
    print(f"  Grid size      : {len(phi_grid_vals)} phi x {len(theta_grid_vals)} theta = {total_cells} cells")
    print(f"  NaN cells      : {nan_count} ({100*nan_count/total_cells:.1f}%)")
    print(f"  Theta range    : {theta_grid_vals[0]} .. {theta_grid_vals[-1]}  step={theta_step}")
    print(f"  Phi range      : {phi_grid_vals[0]} .. {phi_grid_vals[-1]}  step={phi_step}")
    print(f"  Raw max        : {max_value:.6e}")
    print(f"  Output max     : {output_max:.6e}  (normalized={normalize})")
    print(f"  Interp method  : {interp_method}")
    print("-" * 60)


# ---------------------------------------------------------------------------
# Path dispatcher
# ---------------------------------------------------------------------------

def process_path(path, theta_max, normalize, value_column, theta_step, phi_step, interp_method):
    if os.path.isfile(path):
        parse_farfield_file(
            input_file=path,
            output_file=build_output_name(path),
            theta_max=theta_max,
            normalize=normalize,
            value_column=value_column,
            theta_step=theta_step,
            phi_step=phi_step,
            interp_method=interp_method,
        )
        return

    if os.path.isdir(path):
        files = find_farfield_files(path)
        if not files:
            print(f"No .txt files found in: {path}")
            return
        print(f"Found {len(files)} file(s) in: {path}")
        print("=" * 60)
        for f in files:
            parse_farfield_file(
                input_file=f,
                output_file=build_output_name(f),
                theta_max=theta_max,
                normalize=normalize,
                value_column=value_column,
                theta_step=theta_step,
                phi_step=phi_step,
                interp_method=interp_method,
            )
        return

    raise FileNotFoundError(f"Path does not exist: {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert CST farfield TXT to normalized .plot matrix.\n"
            "Transform: CST (Z=beam, Y=up) -> Article (X=beam, Z=up).\n"
            "Interpolates scattered points onto a regular article grid.\n"
            "Output: phi rows x theta cols, phi in (-180,180], theta in [0, theta_max]."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("path", help="CST farfield .txt file or directory.")
    parser.add_argument("--no-normalize", action="store_true",
                        help="Keep raw values (do not scale max to 1).")
    parser.add_argument("--theta-max", type=float, default=90.0, metavar="DEG",
                        help="Max article theta to output (default: 90).")
    parser.add_argument("--theta-step", type=float, default=1.0, metavar="DEG",
                        help="Output grid step for theta (default: 1.0).")
    parser.add_argument("--phi-step", type=float, default=1.0, metavar="DEG",
                        help="Output grid step for phi (default: 1.0).")
    parser.add_argument("--value-column", type=int, default=2, metavar="COL",
                        help="Zero-based column index for the value (default: 2 = Abs(Dir.)).")
    parser.add_argument("--interp", default="linear",
                        choices=["linear", "nearest", "cubic"],
                        help="Interpolation method (default: linear).")

    args = parser.parse_args()

    process_path(
        path=args.path,
        theta_max=args.theta_max,
        normalize=not args.no_normalize,
        value_column=args.value_column,
        theta_step=args.theta_step,
        phi_step=args.phi_step,
        interp_method=args.interp,
    )


if __name__ == "__main__":
    main()
