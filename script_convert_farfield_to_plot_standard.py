"""
Convert CST farfield TXT export to one .plot matrix file.

What this version does:
- reads CST numeric table after the dashed separator line
- uses column 1 = theta, column 2 = phi, column 3 = Abs(Dir.) by default
- converts phi from CST 0..360 style to standard -180..180
- keeps only theta in 0..90
- normalizes all values so that max(value) = 1
- writes ONE output file: <input_name>.raw.txt.plot

Usage:
  python script_convert_farfield_to_plot.py "farfield (f=44) [1(1)].txt"
  python script_convert_farfield_to_plot.py /path/to/folder

Optional flags:
  --no-normalize        Do not normalize values
  --theta-max 180       Change theta cutoff, default is 90
  --value-column 2      Zero-based numeric column index, default 2 = Abs(Dir.)
"""

import argparse
import glob
import os
import sys
from typing import Dict, List, Tuple


def phi_to_standard(phi: float) -> float:
    """Convert phi to [-180, 180]. Keeps +180 instead of turning it into -180."""
    p = ((phi + 180.0) % 360.0) - 180.0

    # If CST has exactly 180, keep it as +180 for nicer axis ordering.
    # 540, 900, etc. also map to +180.
    if abs(p + 180.0) < 1e-9 and phi > 0:
        return 180.0

    return p


def parse_farfield_file(
    input_file: str,
    output_file: str,
    theta_max: float = 90.0,
    normalize: bool = True,
    value_column: int = 2,
) -> None:
    data: Dict[float, Dict[float, float]] = {}
    theta_values = set()
    phi_values = set()
    values: List[float] = []

    in_table = False
    total_rows = 0
    kept_rows = 0

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
                theta = float(parts[0])
                phi = float(parts[1])
                val = float(parts[value_column])
            except ValueError:
                continue

            total_rows += 1

            # Requirement: theta must be 0..90 by default.
            if theta < 0.0 or theta > theta_max:
                continue

            phi_std = phi_to_standard(phi)

            if phi_std not in data:
                data[phi_std] = {}

            # If duplicate phi appears after conversion, keep the later value.
            # In normal CST export with 0..360 this usually only affects edge cases.
            data[phi_std][theta] = val
            theta_values.add(theta)
            phi_values.add(phi_std)
            values.append(val)
            kept_rows += 1

    if not values:
        raise RuntimeError(
            f"No numeric farfield rows were parsed from {input_file}. "
            f"Check input format or --value-column."
        )

    max_value = max(values)
    if normalize:
        if max_value == 0.0:
            raise RuntimeError("Cannot normalize: max value is 0")
        for phi in data:
            for theta in data[phi]:
                data[phi][theta] = data[phi][theta] / max_value

    theta_list = sorted(theta_values)
    phi_list = sorted(phi_values)

    with open(output_file, "w", encoding="utf-8") as out:
        for phi in phi_list:
            row = []
            for theta in theta_list:
                if theta in data.get(phi, {}):
                    row.append(f"{data[phi][theta]:.6e}")
                else:
                    row.append("nan")
            out.write(" ".join(row) + "\n")

    normalized_max = 1.0 if normalize else max_value

    print("Done")
    print("Input          :", input_file)
    print("Output         :", output_file)
    print("Rows read      :", total_rows)
    print("Rows kept      :", kept_rows)
    print("Theta count    :", len(theta_list))
    print("Theta range    :", f"{theta_list[0]} .. {theta_list[-1]}")
    print("Phi count      :", len(phi_list))
    print("Phi range      :", f"{phi_list[0]} .. {phi_list[-1]}")
    print("Original max   :", f"{max_value:.6e}")
    print("Output max     :", f"{normalized_max:.6e}")
    print("Normalized     :", normalize)
    print("-" * 60)


def build_output_name(input_file: str) -> str:
    base, _ = os.path.splitext(input_file)
    return base + ".raw.txt.plot"


def find_farfield_files(path: str) -> List[str]:
    patterns = [
        os.path.join(path, "*_farfield*.txt"),
        os.path.join(path, "*farfield*.txt"),
    ]

    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))

    # unique + sorted
    return sorted(set(files))


def process_path(path: str, theta_max: float, normalize: bool, value_column: int) -> None:
    if os.path.isfile(path):
        output_file = build_output_name(path)
        parse_farfield_file(path, output_file, theta_max, normalize, value_column)
        return

    if os.path.isdir(path):
        files = find_farfield_files(path)

        if not files:
            print(f"No matching farfield files found in directory: {path}")
            print("Expected pattern: *farfield*.txt")
            return

        print(f"Found {len(files)} farfield file(s) in: {path}")
        print("=" * 60)

        for input_file in files:
            output_file = build_output_name(input_file)
            parse_farfield_file(input_file, output_file, theta_max, normalize, value_column)
        return

    print(f"Path does not exist: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert CST farfield TXT to one normalized .plot matrix."
    )
    parser.add_argument("path", help="Input CST farfield .txt file or folder")
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="Do not normalize values to max = 1",
    )
    parser.add_argument(
        "--theta-max",
        type=float,
        default=90.0,
        help="Maximum theta to keep, default: 90",
    )
    parser.add_argument(
        "--value-column",
        type=int,
        default=2,
        help="Zero-based column index for value, default: 2 = Abs(Dir.)",
    )

    args = parser.parse_args()

    process_path(
        args.path,
        theta_max=args.theta_max,
        normalize=not args.no_normalize,
        value_column=args.value_column,
    )


if __name__ == "__main__":
    main()
