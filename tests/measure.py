# How fast the port is, and how much memory it takes, beside gifsicle 1.99 on the same GIFs.
#
#   python3 tests/measure.py [--runs N] [--only WORD] [--sg PATH-TO-sg] [--gifsicle-source DIR]
#
# Four programs: the port built with `sg build --release`, the port with its arithmetic checked (the
# C of `sg emit-c` compiled with -O2, as `--release` compiles), the gifsicle of the PATH (Homebrew's, on macOS), and gifsicle built here from its
# source by the compiler SG compiles through, with `-O2` and the configuration its `configure` writes
# on this machine (vector types and threads on). The GIFs are made from a seed into
# `target/measure/` (the first run takes a minute). Each case is run once to warm up and then N
# times (5); the shortest time and the smallest peak of memory are shown. What each program writes in
# the first run is held to what gifsicle of the PATH writes: they must be the same bytes. A run past
# LIMIT seconds is stopped and named.

import argparse
import glob
import os
import random
import shutil
import subprocess
import sys
import threading
import time

from common import HERE, ROOT, programs
import gifs as made

TARGET = os.path.join(ROOT, "target", "measure")
LIMIT = 300
MACOS = sys.platform == "darwin"


def photo(seed, width, height):
    """One frame of `width` by `height` with 256 colors in smooth shapes and a little noise, a palette
    spread over the cube: a picture whose colors reducing and dithering have work to do."""
    rng = random.Random(f"gif-photo-{seed}")
    colors = [(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(256)]
    # Order the palette so that near indices are near colors, as smooth shapes need.
    colors.sort(key=lambda c: (c[0] // 32, c[1] // 32 if (c[0] // 32) % 2 == 0 else 7 - c[1] // 32, c[2]))
    w = made.Writer(width, height, colors)
    rows = []
    cx, cy = width * 0.4, height * 0.55
    for y in range(height):
        r = bytearray(width)
        for x in range(width):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            v = (x * 255 // max(1, width - 1) + int(d / 7) + (y // 9) * 3) % 256
            if (x ^ y) & 7 == 0:
                v = (v + rng.randrange(-6, 7)) % 256
            r[x] = v
        rows.append(bytes(r))
    w.frame(0, 0, width, height, b"".join(rows), control=False)
    return w.end()


INPUTS = {
    # name -> (how it is made, what it is)
    "small": (lambda: made.animation("measure-small", 120, 90, 40), "an animation of 40 frames of 120 by 90 (23 KB)"),
    "animation": (lambda: made.animation(1, 480, 270, 2000), "an animation of 2,000 frames of 480 by 270, the others parts of the first (2.5 MB)"),
    "animation-full": (lambda: made.animation(2, 480, 270, 300, small=False), "an animation of 300 frames of 480 by 270, each up to the whole screen (4.3 MB)"),
    "photo-medium": (lambda: photo(1, 800, 600), "one frame of 800 by 600 in smooth shapes"),
    "photo-large": (lambda: photo(2, 4000, 3000), "one frame of 4000 by 3000 in smooth shapes"),
    "large": (lambda: made.large(1, 4000), "one frame of 4000 by 4000, stripes with noise"),
}

# (size, what is done, input, options); "{out}" is where the program writes.
CASES = [
    ("small", "read and written", "small", ["{in}", "-o", "{out}"]),
    ("small", "-O3", "small", ["-O3", "{in}", "-o", "{out}"]),
    ("small", "--colors 16 --dither", "small", ["--colors", "16", "--dither", "{in}", "-o", "{out}"]),
    ("small", "-I of 10,000 small GIFs", "many", ["-I", "{many}"]),
    ("medium", "read and written", "animation", ["{in}", "-o", "{out}"]),
    ("medium", "-O3", "animation", ["-O3", "{in}", "-o", "{out}"]),
    ("medium", "-O3", "animation-full", ["-O3", "{in}", "-o", "{out}"]),
    ("medium", "-U -O2", "animation-full", ["-U", "-O2", "{in}", "-o", "{out}"]),
    ("medium", "--lossy=80 -O2", "animation", ["--lossy=80", "-O2", "{in}", "-o", "{out}"]),
    ("medium", "--scale 0.5", "photo-medium", ["--scale", "0.5", "{in}", "-o", "{out}"]),
    ("medium", "--scale 2", "photo-medium", ["--scale", "2", "{in}", "-o", "{out}"]),
    ("medium", "--colors 64", "photo-medium", ["--colors", "64", "{in}", "-o", "{out}"]),
    ("medium", "--colors 64 --dither", "photo-medium", ["--colors", "64", "--dither", "{in}", "-o", "{out}"]),
    ("large", "read and written", "large", ["{in}", "-o", "{out}"]),
    ("large", "read and written", "photo-large", ["{in}", "-o", "{out}"]),
    ("large", "--rotate-90", "large", ["--rotate-90", "{in}", "-o", "{out}"]),
    ("large", "--scale 0.5", "photo-large", ["--scale", "0.5", "{in}", "-o", "{out}"]),
    ("large", "--resize 1920x_ --resize-method lanczos3", "photo-large", ["--resize", "1920x_", "--resize-method", "lanczos3", "{in}", "-o", "{out}"]),
    ("large", "--colors 64", "photo-large", ["--colors", "64", "{in}", "-o", "{out}"]),
    ("large", "--colors 64 --dither", "photo-large", ["--colors", "64", "--dither", "{in}", "-o", "{out}"]),
    ("large", "--colors 64 --gamma oklab", "photo-large", ["--colors", "64", "--gamma", "oklab", "{in}", "-o", "{out}"]),
    ("large", "--lossy=80", "photo-large", ["--lossy=80", "{in}", "-o", "{out}"]),
]

# The files of gifsicle's source the program is made of (its Makefile.am), and the headers they share.
C_SOURCES = ["clp.c", "fmalloc.c", "giffunc.c", "gifread.c", "gifunopt.c", "kcolor.c", "merge.c", "optimize.c",
             "quantize.c", "support.c", "xform.c", "gifsicle.c", "gifwrite.c"]
C_HEADERS = ["src/gifsicle.h", "src/kcolor.h", "src/opttemplate.c", "include/lcdfgif/gif.h", "include/lcdf/clp.h",
             "include/lcdf/inttypes.h"]

CONFIG_H = """\
#define ENABLE_THREADS 1
#define HAVE_CBRTF 1
#define HAVE_EXT_VECTOR_TYPE_VECTOR_TYPES 1
#define HAVE_INT64_T 1
#define HAVE_INTTYPES_H 1
#define HAVE_MKSTEMP 1
#define HAVE_POW 1
#define HAVE_SIMD 1
#define HAVE_SNPRINTF 1
#define HAVE_STDINT_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STRING_H 1
#define HAVE_STRINGS_H 1
#define HAVE_SYS_SELECT_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_UINT64_T 1
#define HAVE_UINTPTR_T 1
#define HAVE_UNISTD_H 1
#define HAVE_VECTOR_SIZE_VECTOR_TYPES 1
#define HAVE___BUILTIN_SHUFFLEVECTOR 1
#define HAVE___SYNC_FETCH_AND_ADD 1
#define PATHNAME_SEPARATOR '/'
#define RANDOM random
#define SIZEOF_FLOAT 4
#define SIZEOF_UNSIGNED_INT 4
#define SIZEOF_UNSIGNED_LONG 8
#define SIZEOF_VOID_P 8
#define STDC_HEADERS 1
#define VERSION "1.99"
#define X_DISPLAY_MISSING 1
#include <stddef.h>
#define GIF_ALLOCATOR_DEFINED 1
#define Gif_Free free
#define HAVE_STRERROR 1
"""


def build(sg, source):
    os.makedirs(TARGET, exist_ok=True)
    out = {}
    print("building SG", file=sys.stderr, flush=True)
    out["SG"] = os.path.join(TARGET, "gifsicle-sg")
    subprocess.run([sg, "build", os.path.join(ROOT, "src"), "--release", "-o", out["SG"]], check=True, timeout=LIMIT)
    # Checked: the C of `sg emit-c` (arithmetic checked) compiled as `--release` compiles its own;
    # `sg build` alone compiles with -O0, for a debugger.
    print("building SG, checked", file=sys.stderr, flush=True)
    c_file = os.path.join(TARGET, "gifsicle-sg-checked.c")
    with open(c_file, "w") as f:
        subprocess.run([sg, "emit-c", os.path.join(ROOT, "src")], stdout=f, check=True, timeout=LIMIT)
    out["SG, checked"] = os.path.join(TARGET, "gifsicle-sg-checked")
    subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-O2", "-ffp-contract=off", c_file, "-o", out["SG, checked"],
                    "-lm", "-pthread"], check=True, timeout=LIMIT)
    out["gifsicle"] = programs()[0]
    folder = os.path.join(TARGET, "c")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "config.h"), "w") as f:
        f.write(CONFIG_H)
    path = os.path.join(TARGET, "gifsicle-c")
    cc = os.environ.get("CC", "cc")
    print(f"building gifsicle with {cc} -O2", file=sys.stderr, flush=True)
    subprocess.run([cc, "-O2", "-DHAVE_CONFIG_H", "-I", folder, "-I", os.path.join(source, "include"),
                    "-I", os.path.join(source, "src"), *[os.path.join(source, "src", c) for c in C_SOURCES],
                    "-lm", "-lpthread", "-o", path], check=True, timeout=LIMIT)
    out[f"gifsicle, {os.path.basename(cc)} -O2 here"] = path
    return out


def inputs():
    folder = os.path.join(TARGET, "gifs")
    os.makedirs(folder, exist_ok=True)
    paths = {}
    for name, (make, _) in INPUTS.items():
        path = os.path.join(folder, name + ".gif")
        if not os.path.exists(path):
            print(f"making {name}.gif", file=sys.stderr, flush=True)
            with open(path + ".part", "wb") as f:
                f.write(make())
            os.replace(path + ".part", path)
        paths[name] = path
    many = os.path.join(folder, "many")
    if not os.path.exists(many):
        print("making 10,000 small GIFs", file=sys.stderr, flush=True)
        made.small_gifs(many + ".part")
        os.replace(many + ".part", many)
    paths["many"] = sorted(glob.glob(os.path.join(many, "*.gif")))
    return paths


def args_of(words, paths, out):
    args = []
    for w in words:
        if w == "{many}":
            args += paths["many"]
        else:
            args.append(w.replace("{out}", out).replace("{in}", paths.get("in", "")))
    return args


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--only", default="")
    ap.add_argument("--sg", default=os.path.expanduser("~/Documents/new-language-design/interpreter/target/release/sg"))
    ap.add_argument("--gifsicle-source", default=os.path.expanduser("~/Documents/sg-gifsicle-upstream/src"))
    o = ap.parse_args()
    global SOURCE
    SOURCE = o.gifsicle_source
    builds = build(o.sg, o.gifsicle_source)
    paths = inputs()
    ref = "gifsicle"
    rows = []
    for size, what, name, words in CASES:
        label = f"{size} / {what} / {name}"
        if o.only and o.only not in label:
            continue
        row = {}
        written = {}
        for b, program in builds.items():
            out = os.path.join(TARGET, "out-" + b.split(",")[0].replace(" ", "-") + ".gif")
            p = dict(paths, **{"in": paths.get(name, "")}) if name != "many" else paths
            args = args_of(words, p, out)
            t, m, stdout = time_and_memory(program, args, o.runs)
            data = stdout
            if "{out}" in words:
                with open(out, "rb") as f:
                    data = f.read()
                os.remove(out)
            written[b] = data
            row[b] = (t, m)
            print(f"  {label}: {b} {t:.3f} s, {m / 1048576:.1f} MB", file=sys.stderr, flush=True)
        for b, data in written.items():
            if data != written[ref]:
                print(f"  NOT THE SAME: {b} wrote {len(data)} bytes, {ref} {len(written[ref])}", file=sys.stderr, flush=True)
                row[b] = row[b] + ("differs",)
        rows.append((size, what, name, row))
    report(builds, rows)


def time_and_memory(program, args, runs):
    """Shortest time and smallest peak of memory of `runs` runs after one to warm up; the first
    run's standard output."""
    best_t, best_m, first = None, None, None
    for i in range(runs + 1):
        start = time.perf_counter()
        out_file = open(os.path.join(TARGET, "stdout"), "w+b")
        err_file = open(os.path.join(TARGET, "stderr"), "w+b")
        p = subprocess.Popen([program, *args], stdin=subprocess.DEVNULL, stdout=out_file, stderr=err_file)
        hung = []
        watch = threading.Timer(LIMIT, lambda: (hung.append(1), p.kill()))
        watch.start()
        _, status, usage = os.wait4(p.pid, 0)
        watch.cancel()
        if hung:
            sys.exit(f"HUNG after {LIMIT} s: {program} {' '.join(args[:6])}")
        seconds = time.perf_counter() - start
        p.returncode = os.waitstatus_to_exitcode(status)
        out_file.seek(0)
        err_file.seek(0)
        stdout, stderr = out_file.read(), err_file.read()
        out_file.close()
        err_file.close()
        if p.returncode != 0:
            sys.exit(f"FAILED ({p.returncode}): {program} {' '.join(args[:6])}\n{stderr.decode(errors='replace')}")
        peak = usage.ru_maxrss if MACOS else usage.ru_maxrss * 1024
        if i == 0:
            first = stdout
            continue
        best_t = seconds if best_t is None else min(best_t, seconds)
        best_m = peak if best_m is None else min(best_m, peak)
    return best_t, best_m, first


def stripped_size(path):
    copy = os.path.join(TARGET, os.path.basename(path) + "-stripped")
    shutil.copyfile(path, copy)
    subprocess.run(["strip", copy], check=True, capture_output=True)
    return os.path.getsize(copy)


def sg_lines():
    n = 0
    for path in glob.glob(os.path.join(ROOT, "src", "*.sg")):
        for line in open(path, encoding="utf-8"):
            t = line.strip()
            if t and not t.startswith("//"):
                n += 1
    return n


def c_lines(source):
    n = 0
    files = [os.path.join(source, "src", c) for c in C_SOURCES] + [os.path.join(source, h) for h in C_HEADERS]
    for path in files:
        if not os.path.exists(path):
            continue
        inside = False
        for line in open(path, encoding="utf-8", errors="replace"):
            t = line.strip()
            code = ""
            i = 0
            while i < len(t):
                if inside:
                    j = t.find("*/", i)
                    if j < 0:
                        i = len(t)
                    else:
                        inside = False
                        i = j + 2
                elif t.startswith("/*", i):
                    inside = True
                    i += 2
                elif t.startswith("//", i):
                    break
                else:
                    code += t[i]
                    i += 1
            if code.strip():
                n += 1
    return n


def report(builds, rows):
    names = list(builds)
    print("\n| Size | Case | GIF | " + " | ".join(names) + " |")
    print("|---|---|---|" + "---|" * len(names))
    for size, what, name, row in rows:
        cells = []
        for b in names:
            t, m, *bad = row[b]
            cells.append(f"{t:.3f} s, {m / 1048576:.1f} MB" + (" (differs)" if bad else ""))
        print(f"| {size} | {what} | {name} | " + " | ".join(cells) + " |")
    print("\n| Size, stripped | " + " | ".join(f"{stripped_size(p) // 1024} KB" for p in builds.values()) + " |")
    print(f"\n| Lines | {sg_lines()} | {sg_lines()} | {c_lines(SOURCE)} | {c_lines(SOURCE)} |")
    print("\nSG ratio to gifsicle (time, peak):")
    for size, what, name, row in rows:
        t0, m0, *_ = row["gifsicle"]
        tl, ml, *_ = row[names[-1]]
        t, m, *_ = row["SG"]
        print(f"  {size:6} {what:45} {name:15} {t / t0:5.2f} {m / m0:5.2f}   to -O2 here {t / tl:5.2f}")


if __name__ == "__main__":
    main()
