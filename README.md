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
| Resizing (`--resize`, `--scale` and their methods) | Not yet |
| Color reduction and dithering (`--colors`, `--use-colormap`, `--dither`, `--gamma`) | Not yet |
| `--lossy` | Not yet |
| `--transform-colormap`, `-j` | Not yet tested |

## Testing

The tests compare the program with gifsicle 1.99 itself: gifsicle's own `testie` tests, and runs of
both programs over generated GIFs with many options, where everything each writes is compared.
