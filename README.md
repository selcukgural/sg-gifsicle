# sg-gifsicle

[gifsicle](https://www.lcdf.org/gifsicle/) 1.99, the command-line tool for GIF images by Eddie Kohler,
translated file by file into [SG](https://github.com/selcukgural/sg-lang), a small, memory-safe systems
language. The program takes the same options and writes the same bytes, the same messages and the same
exit codes as gifsicle 1.99, except where noted below.

This is a translation of gifsicle's code, and so it is licensed as gifsicle is: under the GNU General
Public License, version 2 (`COPYING`). The copyright notices of the original files are kept at the top
of each translated file.

## Building

SG is not released yet; it is built from its repository at the commit named in `SG_COMMIT`:

```
git clone https://github.com/selcukgural/sg-lang
cd sg-lang
git checkout $(cat ../sg-gifsicle/SG_COMMIT)
cd interpreter && cargo build --release && cd ../..
sg-lang/interpreter/target/release/sg build sg-gifsicle/src --release -o gifsicle
```

This needs Rust (to build the SG compiler) and a C compiler (SG compiles through C): clang or GCC on
Linux and macOS.

## Running

```
./gifsicle --help
./gifsicle -I animation.gif
./gifsicle -O3 --colors 64 in.gif -o out.gif
```

The options are gifsicle's; its manual applies as it is.

## What is there

| Part of gifsicle | State |
|---|---|
| Reading, writing, `-I` and its variants, frame selection and changes, merging, batch, explode | Done |
| Crop, flip, rotate, positions, extensions, comments, names, background, transparency | Done |
| `-O1`, `-O2`, `-O3`, `-U` (unoptimize), `--careful` | Done |
| Resizing (`--resize`, `--scale`, `--resize-colors` and every method) | Done |
| Color reduction and dithering (`--colors`, `--color-method`, `--use-colormap`, `--dither`, `--gamma`) | Done |
| `--lossy` | Done |
| `--transform-colormap` | Done |
| `-j` | Taken; resizing runs one frame after the other, which gives the same frames |

### The same bytes, and where they come from

The bytes the port writes are those of gifsicle 1.99 as Homebrew builds it on macOS, where two things
that C leaves to the compiler and the library decide some of them:

- **Fused arithmetic.** C lets a compiler turn `a * b + c` within one expression into one fused
  multiply-add, rounded once, and clang does (`-ffp-contract=on`); SG never fuses on its own. Where
  gifsicle's arithmetic of floating point is fused as clang builds it (the mixing of pixels when
  resizing, the weights of its filters, the tables of `--gamma`, the Oklab colors, the blending and
  median of colors when reducing them, the plans of ordered dithers, the score of `--lossy`), the port
  writes the fusion out with `fusedMultiplyAdd`, as the machine code of gifsicle shows it. Where clang
  turns `pow(0.25, y)` into `exp2(-2 * y)`, the port calls `exp2` too. A gifsicle built without fusion (GCC on x86-64, by default) gives a different
  pixel here and there.
- **The order of `qsort`.** C's `qsort` does not keep the order of items that compare equal, and
  gifsicle sorts colors with it, so which of two equally popular colors comes first is the library's
  choice. The port sorts as the C library of macOS does (`src/qsort.sg`, from Apple's libc, itself
  from FreeBSD). The GNU library of Linux orders such ties differently, so a gifsicle built on Linux
  can choose other colors for `--resize-colors` and color reduction.
- **`random()`.** Floyd-Steinberg and Atkinson dithers start from random errors that gifsicle takes
  from C's `random()`, never seeded. The port has the same generator (`src/quantize.sg`); the C
  libraries of macOS and Linux give the same numbers.

## How fast

`tests/measure.py` runs four programs over 22 cases in three sizes, on GIFs made from a seed: the port built
with `sg build --release`; the port with its arithmetic checked (the C of `sg emit-c` compiled as `--release`
compiles it); gifsicle 1.99 as Homebrew builds it; and gifsicle built from its source by the same compiler, with
`-O2` and the configuration its `configure` writes (vector types and threads). Each case runs once to warm up and
five times after; the table shows the shortest time and the smallest peak of resident memory. What each program
writes is held to what Homebrew's gifsicle writes: the same bytes in every case. Apple M3 Max, macOS, Apple
clang 21, 25 November 2026.

| Case | SG | SG, checked | gifsicle | gifsicle, `-O2` here |
|---|---|---|---|---|
| 40 frames of 120 by 90, read and written | 0.005 s, 2.8 MB | 0.005 s, 2.7 MB | 0.004 s, 2.4 MB | 0.005 s, 2.4 MB |
| 40 frames, `-O3` | 0.005 s, 3.3 MB | 0.005 s, 3.4 MB | 0.004 s, 2.6 MB | 0.004 s, 2.7 MB |
| 40 frames, `--colors 16 --dither` | 0.005 s, 2.9 MB | 0.005 s, 3.0 MB | 0.005 s, 2.4 MB | 0.004 s, 2.4 MB |
| 10,000 small GIFs, `-I` | 0.300 s, 96.5 MB | 0.303 s, 96.7 MB | 0.310 s, 78.0 MB | 0.306 s, 78.1 MB |
| 2,000 frames of 480 by 270, read and written | 0.109 s, 14.8 MB | 0.121 s, 14.9 MB | 0.093 s, 8.8 MB | 0.095 s, 8.8 MB |
| 2,000 frames, `-O3` | 0.782 s, 36.2 MB | 0.832 s, 35.0 MB | 0.590 s, 22.2 MB | 0.572 s, 22.2 MB |
| 300 whole frames, `-O3` | 0.673 s, 32.4 MB | 0.710 s, 33.1 MB | 0.543 s, 24.4 MB | 0.532 s, 24.4 MB |
| 300 whole frames, `-U -O2` | 0.346 s, 31.8 MB | 0.375 s, 31.7 MB | 0.279 s, 24.4 MB | 0.266 s, 24.5 MB |
| 2,000 frames, `--lossy=80 -O2` | 1.150 s, 36.6 MB | 1.373 s, 36.3 MB | 1.011 s, 22.2 MB | 0.845 s, 22.3 MB |
| 800 by 600, `--scale 0.5` | 0.024 s, 12.9 MB | 0.026 s, 12.9 MB | 0.023 s, 12.1 MB | 0.023 s, 12.2 MB |
| 800 by 600, `--scale 2` | 0.028 s, 7.4 MB | 0.029 s, 7.5 MB | 0.024 s, 6.1 MB | 0.024 s, 6.1 MB |
| 800 by 600, `--colors 64` | 0.014 s, 4.6 MB | 0.015 s, 4.6 MB | 0.012 s, 3.9 MB | 0.013 s, 3.9 MB |
| 800 by 600, `--colors 64 --dither` | 0.050 s, 4.6 MB | 0.053 s, 4.7 MB | 0.052 s, 3.9 MB | 0.049 s, 3.9 MB |
| 4000 by 4000, read and written | 0.108 s, 56.5 MB | 0.124 s, 56.5 MB | 0.100 s, 56.3 MB | 0.116 s, 56.3 MB |
| 4000 by 3000, read and written | 0.249 s, 49.8 MB | 0.264 s, 49.8 MB | 0.220 s, 49.6 MB | 0.235 s, 49.6 MB |
| 4000 by 4000, `--rotate-90` | 0.144 s, 72.0 MB | 0.164 s, 72.0 MB | 0.125 s, 65.1 MB | 0.139 s, 65.2 MB |
| 4000 by 3000, `--scale 0.5` | 0.449 s, 283.9 MB | 0.470 s, 284.0 MB | 0.434 s, 274.6 MB | 0.423 s, 274.7 MB |
| 4000 by 3000, `--resize 1920x_ --resize-method lanczos3` | 0.754 s, 367.9 MB | 0.782 s, 368.0 MB | 0.736 s, 358.7 MB | 0.722 s, 358.8 MB |
| 4000 by 3000, `--colors 64` | 0.265 s, 49.9 MB | 0.276 s, 49.9 MB | 0.235 s, 42.8 MB | 0.245 s, 42.8 MB |
| 4000 by 3000, `--colors 64 --dither` | 1.168 s, 51.1 MB | 1.293 s, 51.1 MB | 1.233 s, 42.8 MB | 1.149 s, 42.8 MB |
| 4000 by 3000, `--colors 64 --gamma oklab` | 0.267 s, 51.1 MB | 0.280 s, 51.1 MB | 0.237 s, 42.8 MB | 0.247 s, 42.8 MB |
| 4000 by 3000, `--lossy=80` | 0.436 s, 50.2 MB | 0.468 s, 50.2 MB | 0.421 s, 49.9 MB | 0.389 s, 49.9 MB |
| Size, stripped | 666 KB | 909 KB | 201 KB | 234 KB |
| Lines, neither blank nor only a comment | 12,556 | 12,556 | 12,964 | 12,964 |

- Large frames, turning, resizing and color reduction take 1.03 to 1.19 times gifsicle's time; the dithers are
  faster (0.95). On the GIFs of a few milliseconds the difference is under one millisecond. Most of what is left is the LZW encoder, which every write goes through: written as gifsicle's, it
  takes 1.08 to 1.21 times as long, and not for its checks (the same C without them takes the same time). The
  C compiler puts the lossy search inside it and the loop that finds the longest code then keeps the bases of
  its arrays on the stack.
- `-O3`, `-U` and `--lossy` on animations take 1.24 to 1.33 times as long: they compress each frame again and
  again, so the encoder counts more, and each time the port makes a table of codes of 100 KB that it must fill
  (C takes its memory as it is), about 3% of the time.
- Memory is the same on large frames. On animations the port holds 1.2 to 1.7 times as much: it reads the
  whole file into memory, where gifsicle reads from its `FILE`, and the allocator keeps more of what the port
  frees, many smaller blocks; the most the port holds at once in `-O3` is gifsicle's (14.9 MB against 14.6).
- The program is three times gifsicle's size: the checks, the messages of the panics, and SG's runtime.

## Testing

The tests compare the program with gifsicle 1.99 itself: gifsicle's own `testie` tests, and runs of
both programs over generated GIFs with many options, where everything each writes is compared.
They need Python 3, gifsicle 1.99 on the `PATH` (or named by `GIFSICLE`), with its `gifdiff`, and
the program built as above (or named by `SG_GIFSICLE`):

```
python3 sg-gifsicle/tests/differ.py            # every GIF with every set of options
python3 sg-gifsicle/tests/differ.py --quick    # without the GIF of 65535 by 65535 (8.6 GB a run)
GIFSICLE_TESTS=gifsicle-1.99/test python3 sg-gifsicle/tests/testie.py
```

`differ.py` runs both programs, each in a folder of its own, with over two hundred sets of options over
GIFs made from a seed by `tests/gifs.py` (small and large, animated, interlaced, with local color
tables, transparency, every disposal, and broken ones), the icons of the system where there are
some, and any folder given with `--gifs DIR`. The exit code, the output, the standard error and
every file written must be the same. `testie.py` runs gifsicle's own tests from its source.
`measure.py` measures as told above; it builds gifsicle from the source named by `--gifsicle-source`.
