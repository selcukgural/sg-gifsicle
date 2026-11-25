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
| `-j` (resizing the frames of an unoptimized GIF on several threads) | Done |

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

### Threads

`-j` resizes the frames of an unoptimized GIF on several threads, as gifsicle does, and the bytes written
are those of one thread. gifsicle's threads share the stream, behind two locks (one for the global colormap,
one for a global variable its sort reads) and an atomic counter that hands out frame numbers. In the port a
frame is moved out of the program's state, with its local colormap, and sent through a channel to a thread.
That thread owns the frame until it hands it back. Each thread also has its own copy of the global colormap
and of the gamma tables. No thread changes the colormap: as in gifsicle, frames are resized in order until it
is full. SG does not let a thread be given a borrow of anything another thread can reach, so this is how the
code has to be written, and it needs no lock. If uncompressing a damaged frame finds errors, the messages come
out in the order of the frames; gifsicle prints them as its threads find them. A build with ThreadSanitizer
finds no race.

## How fast

`tests/measure.py` runs four programs over 24 cases in three sizes, on GIFs made from a seed: the port built
with `sg build --release`; the port with its arithmetic checked (the C of `sg emit-c` compiled as `--release`
compiles it); gifsicle 1.99 as Homebrew builds it; and gifsicle built from its source by the same compiler, with
`-O2` and the configuration its `configure` writes (vector types and threads). Each case runs once to warm up and
five times after; the table shows the shortest time and the smallest peak of resident memory. What each program
writes is held to what Homebrew's gifsicle writes: the same bytes in every case. Apple M3 Max, macOS, Apple
clang 21, 25 November 2026.

| Case | SG | SG, checked | gifsicle | gifsicle, `-O2` here |
|---|---|---|---|---|
| 40 frames of 120 by 90, read and written | 0.005 s, 2.7 MB | 0.005 s, 2.8 MB | 0.004 s, 2.4 MB | 0.005 s, 2.4 MB |
| 40 frames, `-O3` | 0.006 s, 3.3 MB | 0.005 s, 3.4 MB | 0.004 s, 2.6 MB | 0.004 s, 2.7 MB |
| 40 frames, `--colors 16 --dither` | 0.005 s, 2.9 MB | 0.005 s, 3.0 MB | 0.005 s, 2.4 MB | 0.005 s, 2.4 MB |
| 10,000 small GIFs, `-I` | 0.307 s, 96.6 MB | 0.305 s, 96.6 MB | 0.312 s, 78.0 MB | 0.304 s, 78.1 MB |
| 2,000 frames of 480 by 270, read and written | 0.110 s, 15.1 MB | 0.120 s, 14.8 MB | 0.092 s, 8.8 MB | 0.093 s, 8.8 MB |
| 2,000 frames, `-O3` | 0.769 s, 28.4 MB | 0.827 s, 30.6 MB | 0.589 s, 22.2 MB | 0.572 s, 22.2 MB |
| 300 whole frames, `-O3` | 0.673 s, 32.8 MB | 0.706 s, 32.4 MB | 0.541 s, 24.4 MB | 0.528 s, 24.4 MB |
| 300 whole frames, `-U -O2` | 0.346 s, 32.4 MB | 0.371 s, 32.1 MB | 0.282 s, 24.4 MB | 0.267 s, 24.5 MB |
| 2,000 frames, `--lossy=80 -O2` | 1.155 s, 31.2 MB | 1.362 s, 30.9 MB | 1.010 s, 22.2 MB | 0.852 s, 22.3 MB |
| 800 by 600, `--scale 0.5` | 0.024 s, 12.9 MB | 0.026 s, 13.0 MB | 0.023 s, 12.2 MB | 0.022 s, 12.2 MB |
| 800 by 600, `--scale 2` | 0.028 s, 7.5 MB | 0.030 s, 7.5 MB | 0.024 s, 6.0 MB | 0.024 s, 6.1 MB |
| 800 by 600, `--colors 64` | 0.014 s, 4.6 MB | 0.014 s, 4.7 MB | 0.012 s, 3.9 MB | 0.013 s, 3.9 MB |
| 800 by 600, `--colors 64 --dither` | 0.050 s, 4.7 MB | 0.054 s, 4.7 MB | 0.052 s, 3.9 MB | 0.049 s, 3.9 MB |
| 40 frames of 800 by 600, `--scale 0.5 --resize-method lanczos3` | 1.279 s, 43.4 MB | 1.396 s, 43.5 MB | 1.259 s, 37.5 MB | 1.226 s, 37.6 MB |
| 40 frames, the same with `-j8` | 0.365 s, 135.8 MB | 0.400 s, 135.9 MB | 0.350 s, 129.4 MB | 0.366 s, 129.2 MB |
| 4000 by 4000, read and written | 0.105 s, 56.5 MB | 0.127 s, 56.6 MB | 0.098 s, 56.3 MB | 0.113 s, 56.3 MB |
| 4000 by 3000, read and written | 0.245 s, 49.8 MB | 0.262 s, 49.9 MB | 0.219 s, 49.6 MB | 0.230 s, 49.7 MB |
| 4000 by 4000, `--rotate-90` | 0.146 s, 71.9 MB | 0.171 s, 72.0 MB | 0.124 s, 65.2 MB | 0.139 s, 65.2 MB |
| 4000 by 3000, `--scale 0.5` | 0.448 s, 283.9 MB | 0.473 s, 284.0 MB | 0.434 s, 274.6 MB | 0.423 s, 274.7 MB |
| 4000 by 3000, `--resize 1920x_ --resize-method lanczos3` | 0.745 s, 367.9 MB | 0.798 s, 367.1 MB | 0.739 s, 358.8 MB | 0.729 s, 358.8 MB |
| 4000 by 3000, `--colors 64` | 0.259 s, 49.9 MB | 0.279 s, 49.9 MB | 0.235 s, 42.8 MB | 0.245 s, 42.8 MB |
| 4000 by 3000, `--colors 64 --dither` | 1.159 s, 51.1 MB | 1.318 s, 51.2 MB | 1.238 s, 42.8 MB | 1.158 s, 42.8 MB |
| 4000 by 3000, `--colors 64 --gamma oklab` | 0.262 s, 51.1 MB | 0.279 s, 51.2 MB | 0.236 s, 42.8 MB | 0.247 s, 42.8 MB |
| 4000 by 3000, `--lossy=80` | 0.434 s, 50.2 MB | 0.464 s, 50.2 MB | 0.413 s, 49.9 MB | 0.389 s, 50.0 MB |
| Size, stripped | 683 KB | 942 KB | 201 KB | 234 KB |
| Lines, neither blank nor only a comment | 12,773 | 12,773 | 12,964 | 12,964 |

- Large frames, turning, resizing and color reduction take 1.01 to 1.17 times gifsicle's time; the dithers are
  faster (0.94 and 0.95). On the GIFs of a few milliseconds the difference is under one millisecond. Most of what is left is the LZW encoder, which every write goes through: written as gifsicle's, it
  takes 1.08 to 1.21 times as long, and not for its checks (the same C without them takes the same time). The
  C compiler puts the lossy search inside it and the loop that finds the longest code then keeps the bases of
  its arrays on the stack.
- `-O3` and `-U` on animations take 1.23 to 1.31 times as long, `--lossy=80 -O2` 1.14: they compress each frame again and
  again, so the encoder counts more, and each time the port makes a table of codes of 100 KB that it must fill
  (C takes its memory as it is), about 3% of the time.
- Memory is the same on large frames. On animations the port holds 1.3 to 1.7 times as much: it reads the
  whole file into memory, where gifsicle reads from its `FILE`, and the allocator keeps more of what the port
  frees, many smaller blocks; the most the port holds at once in `-O3` is gifsicle's (14.9 MB against 14.6).
- `-j8` resizes the 40 whole frames 3.5 times as fast as one thread, as gifsicle does (0.365 s against its
  0.350); each thread holds its own screens, as gifsicle's do, so memory grows with the threads in both.
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
