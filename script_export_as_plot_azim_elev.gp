# Export one CST farfield matrix .plot file to a PNG azimuth/elevation map.
#
# Data convention:
#   x axis: theta, degrees
#   y axis: phi, degrees, shifted from 0..360 to -180..180 by ($2 - 180)
#   z/color: matrix value from column 3
#
# Usage for one file from PowerShell:
#   gnuplot -e "infile='C:/dev/md/test/farfield (f=34) [1].raw.txt.plot'; freq='34'; outfile='C:/dev/md/test/34.png'" script_export_as_plot_azim_elev.gp
#
# Batch usage from PowerShell, run in C:\dev\md\test:
#   Get-ChildItem -Filter '*.plot' | ForEach-Object {
#       if ($_.Name -match 'f=(\d+(?:\.\d+)?)') {
#           $freq = $Matches[1]
#           $in = $_.FullName.Replace('\','/')
#           $out = (Join-Path $_.DirectoryName ($freq + '.png')).Replace('\','/')
#           gnuplot -e "infile='$in'; freq='$freq'; outfile='$out'" script_export_as_plot_azim_elev.gp
#       }
#   }
#
# Required variables:
#   infile  - path to the .plot file
#   freq    - frequency label in GHz, e.g. "34"
#   outfile - output PNG path

if (!exists("infile"))  infile  = "farfield (f=34) [1].raw.txt.plot"
if (!exists("freq"))    freq    = "34"
if (!exists("outfile")) outfile = freq . ".png"

set encoding utf8
set terminal pngcairo size 1200,800 enhanced font "Arial,14"
set output outfile

unset key
set title sprintf("f = %s GHz", freq)
set xlabel "θ, deg"
set ylabel "φ, deg"
set xrange [0:*]
set yrange [-180:180]
set cblabel "Value"

plot infile matrix using 1:($2-180):3 with image

set output
