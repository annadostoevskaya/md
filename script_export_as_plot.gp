# How to use:
# 1) Put this script in a folder with one or more *.plot files (matrix format).
# 2) Run:
#    gnuplot script_export_as_plot.gp
# 3) Result images will be saved into ./plot as PNG files.
#
# Notes:
# - Uses file names to extract angle from pattern *_Angle_<value>_*.
# - If file name contains "_dB.plot", colorbar label is set to "Dir (dB)".

set terminal pngcairo size 1600,1200 enhanced font "Arial,16"
set encoding utf8

base_title = "Farfield Radiation Pattern"

set xlabel "Theta (deg)"
set ylabel "Phi (deg)"
set title base_title
unset key
set xrange [0:180]
set yrange [0:359]
set xtics 0, 30, 180
set ytics 0, 60, 360

system("mkdir -p plot")

files = system("printf '%s\n' *.plot")

do for [file in files] {
    if (strlen(file) == 0) {
        continue
    }

    angle = word(system(sprintf("echo %s | sed -E 's/.*_Angle_([^_]+)_.*/\\1/'", file)), 1)
    set title sprintf("%s (%s deg)", base_title, angle)

    if (strstrt(file, "_dB.plot") > 0) {
        set cblabel "Dir (dB)"
    } else {
        set cblabel "Dir"
    }

    outfile = sprintf("plot/%s.png", file[1:strlen(file)-5])
    set output outfile
    plot file matrix using 1:2:3 with image
    unset output
}
