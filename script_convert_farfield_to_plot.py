"""
How to use:
1) Convert one farfield file:
   python script_convert_farfield_to_plot.py path/to/input_farfield.txt
2) Convert all matching files in a directory:
   python script_convert_farfield_to_plot.py path/to/folder

Input format:
- Script reads numeric table rows after a line starting with '---'.
- Each data row must contain at least: theta phi value

Output:
- For each input file, creates <input_name>.raw.txt next to it.
- In directory mode, processes files matching: *_farfield*.txt
"""

import sys
import os
import glob


def parse_farfield_file(input_file: str, output_file: str) -> None:
    data = {}
    theta_values = {}
    phi_values = {}

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
                theta = float(parts[0])
                phi = float(parts[1])
                val = float(parts[2])
            except ValueError:
                continue

            if phi not in data:
                data[phi] = {}

            data[phi][theta] = val
            theta_values[theta] = 1
            phi_values[phi] = 1

    theta_list = sorted(theta_values.keys())
    phi_list = sorted(phi_values.keys())

    with open(output_file, "w", encoding="utf-8") as out:
        for phi in phi_list:
            for theta in theta_list:
                if theta in data[phi]:
                    out.write("{:.6e} ".format(data[phi][theta]))
                else:
                    out.write("nan ")
            out.write("\n")

    print("Done")
    print("Input :", input_file)
    print("Output:", output_file)
    print("Theta :", len(theta_list))
    print("Phi   :", len(phi_list))
    print("-" * 60)


def build_output_name(input_file: str) -> str:
    base, _ = os.path.splitext(input_file)
    return base + ".raw.txt"


def process_path(path: str) -> None:
    if os.path.isfile(path):
        output_file = build_output_name(path)
        parse_farfield_file(path, output_file)
        return

    if os.path.isdir(path):
        pattern = os.path.join(path, "*_farfield*.txt")
        files = sorted(glob.glob(pattern))

        if not files:
            print(f"No matching farfield files found in directory: {path}")
            print("Expected pattern: *_farfield*.txt")
            return

        print(f"Found {len(files)} farfield file(s) in: {path}")
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
        print("  python script_convert_farfield_to_plot.py directory_path")
        return

    path = sys.argv[1]
    process_path(path)


if __name__ == "__main__":
    main()
