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
| Color reduction and dithering (`--colors`, `--use-colormap`, `--dither`, `--gamma`) | Not yet |
| `--lossy` | Not yet |
| `--transform-colormap` | Not yet tested |
| `-j` | Taken; resizing runs one frame after the other, which gives the same frames |

### The same bytes, and where they come from

The bytes the port writes are those of gifsicle 1.99 as Homebrew builds it on macOS, where two things
that C leaves to the compiler and the library decide some of them:

- **Fused arithmetic.** C lets a compiler turn `a * b + c` within one expression into one fused
  multiply-add, rounded once, and clang does (`-ffp-contract=on`); SG never fuses on its own. Where
  gifsicle's arithmetic of floating point is fused as clang builds it (the mixing of pixels when
  resizing, the weights of its filters, the tables of `--gamma`), the port writes the fusion out with
  `fusedMultiplyAdd`. A gifsicle built without fusion (GCC on x86-64, by default) gives a different
  pixel here and there.
- **The order of `qsort`.** C's `qsort` does not keep the order of items that compare equal, and
  gifsicle sorts colors with it, so which of two equally popular colors comes first is the library's
  choice. The port sorts as the C library of macOS does (`src/qsort.sg`, from Apple's libc, itself
  from FreeBSD). The GNU library of Linux orders such ties differently, so a gifsicle built on Linux
  can choose other colors for `--resize-colors` and, later, color reduction.

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

`differ.py` runs both programs, each in a folder of its own, with over a hundred sets of options over
GIFs made from a seed by `tests/gifs.py` (small and large, animated, interlaced, with local color
tables, transparency, every disposal, and broken ones), the icons of the system where there are
some, and any folder given with `--gifs DIR`. The exit code, the output, the standard error and
every file written must be the same. `testie.py` runs gifsicle's own tests from its source; the
one that reduces colors waits for that part.
