"""
Convert CST farfield Elevation/Azimuth export to gnuplot matrix.

Input:
- numeric rows after line starting with ---
- columns:
    Elevation  Azimuth  Value

Processing:
1) remove lower hemisphere:
      elevation < 0
2) convert CST elevation to standard theta:
      theta = 90 - elevation
3) normalize values:
      value / max(value)

Output:
- <input>.raw.txt.plot
"""

import sys
import os
import glob
import math


def parse_farfield_file(input_file: str, output_file: str) -> None:
    data = {}
    theta_values = {}
    phi_values = {}
    values = []

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

            if len(parts) < 3:
                continue

            try:
                elevation = float(parts[0])
                azimuth = float(parts[1])
                value = float(parts[2])
            except ValueError:
                continue

            # remove lower hemisphere
            if elevation < 0.0:
                continue

            # keep only 0..90
            if elevation > 90.0:
                continue

            # CST elevation -> standard theta
            theta = 90.0 - elevation

            phi = azimuth

            if phi not in data:
                data[phi] = {}

            data[phi][theta] = value

            theta_values[theta] = 1
            phi_values[phi] = 1

            if not math.isnan(value):
                values.append(value)

    # normalize to max = 1
    max_val = max(values) if values else 1.0

    if max_val == 0:
        max_val = 1.0

    theta_list = sorted(theta_values.keys())
    phi_list = sorted(phi_values.keys())

    with open(output_file, "w", encoding="utf-8") as out:
        for phi in phi_list:
            for theta in theta_list:

                if theta in data[phi]:
                    normalized = data[phi][theta] / max_val
                    out.write("{:.6e} ".format(normalized))
                else:
                    out.write("nan ")

            out.write("\n")

    print("Done")
    print("Input      :", input_file)
    print("Output     :", output_file)

    if theta_list:
        print("Theta range:", min(theta_list), "..", max(theta_list))

    if phi_list:
        print("Phi range  :", min(phi_list), "..", max(phi_list))

    print("Theta pts  :", len(theta_list))
    print("Phi pts    :", len(phi_list))
    print("Max value  :", "{:.6e}".format(max_val))
    print("Normalized : max = 1")

    print("-" * 60)


def build_output_name(input_file: str) -> str:
    base, _ = os.path.splitext(input_file)
    return base + ".raw.txt.plot"


def process_path(path: str) -> None:

    if os.path.isfile(path):
        output_file = build_output_name(path)
        parse_farfield_file(path, output_file)
        return

    if os.path.isdir(path):

        pattern = os.path.join(path, "*farfield*.txt")
        files = sorted(glob.glob(pattern))

        if not files:
            print(f"No matching farfield files found in directory: {path}")
            print("Expected pattern: *farfield*.txt")
            return

        print(f"Found {len(files)} farfield file(s)")
        print("=" * 60)

        for input_file in files:
            output_file = build_output_name(input_file)
            parse_farfield_file(input_file, output_file)

        return

    print(f"Path does not exist: {path}")


def main() -> None:

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python script_convert_farfield_to_plot.py input.txt")
        print("  python script_convert_farfield_to_plot.py directory")
        return

    process_path(sys.argv[1])


if __name__ == "__main__":
    main()
