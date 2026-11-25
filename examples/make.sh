#!/bin/sh
# Makes the example GIFs of the README from pasha.gif with the port, and, where gifsicle 1.99 is
# on the PATH (or named by GIFSICLE), checks that gifsicle writes the same bytes.
#
#   sh examples/make.sh [PROGRAM]      # PROGRAM: the port, ../gifsicle by default
#
# pasha.gif is Pasha, the cat of SG (sg-lang's brand/pasha.png), made a GIF of 480 by 480 by macOS's
# `sips`; everything else here is written by the program.
set -eu
cd "$(dirname "$0")"
SG="${1:-../../gifsicle}"
C="${GIFSICLE:-gifsicle}"

make() {
    out="$1"
    shift
    "$SG" "$@" -o "$out"
    if command -v "$C" > /dev/null 2>&1; then
        "$C" "$@" -o "$out.c"
        if cmp -s "$out" "$out.c"; then
            echo "$out: $(wc -c < "$out" | tr -d ' ') bytes, the same as gifsicle's"
        else
            echo "$out: NOT the same as gifsicle's" >&2
            exit 1
        fi
        rm "$out.c"
    else
        echo "$out: $(wc -c < "$out" | tr -d ' ') bytes"
    fi
}

make small.gif --resize 160x_ --resize-method lanczos3 pasha.gif
make colors-8.gif --resize 240x_ --colors 8 pasha.gif
make colors-8-dither.gif --resize 240x_ --colors 8 --dither pasha.gif
make face.gif --crop 45,60+240x220 --flip-horizontal pasha.gif
make turn.gif --resize 240x_ pasha.gif
make turning.gif -l -d 40 turn.gif --rotate-90 turn.gif --rotate-180 turn.gif --rotate-270 turn.gif
make turning-small.gif -j4 --resize 120x_ --resize-method catrom -O3 turning.gif
rm turn.gif turning.gif
