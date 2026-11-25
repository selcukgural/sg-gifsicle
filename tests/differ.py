# The differential test: gifsicle 1.99 and the SG port run with the same options on the same GIFs,
# each in a folder of its own; the exit code, the output, the standard error and every file written
# must be the same.
#
#   python3 tests/differ.py [--quick] [--show N] [--gifs DIR]... [WORD]...
#
# The GIFs: those `gifs.py` makes from a seed (written once into tests/corpus/), the icons of the
# system where there are some (/usr/share/httpd/icons on macOS), and any folder given with --gifs.
# A WORD keeps only the GIFs whose names hold it. One GIF of 65535 by 65535 takes 8.6 GB in each
# program, so it runs alone after the rest, with fewer options; --quick leaves it out.

import concurrent.futures as cf
import glob
import os
import shutil
import sys
import tempfile
import time

from common import HERE, programs, run_in
import gifs as made

OPTIONS = [
    [], ["-I"], ["-I", "-I"], ["--xinfo"], ["--cinfo"], ["--sinfo"], ["--xinfo", "--sinfo", "--cinfo"],
    ["--crop", "2,2+10x10"], ["--crop", "0,0-5,5"], ["--crop", "5,5+1000x1000"],
    ["--flip-horizontal"], ["--flip-vertical"], ["--rotate-90"], ["--rotate-180"], ["--rotate-270"],
    ["-i"], ["--careful"], ["-d", "10"], ["--no-comments"], ["-n", "frame"], ["-c", "hello"], ["-l"], ["-l3"],
    ["--no-loopcount"], ["-t", "#000000"], ["-t", "0"], ["--bg", "#ffffff"], ["-B", "#ff0000"], ["-p", "3,4"],
    ["-S", "100x100"], ["--logical-screen", "1x1"], ["--max-screen", "10x10"], ["--crop-transparency"],
    ["-D", "bg"], ["--disposal=previous"], ["#0"], ["#0", "#-1"], ["#1-3"], ["--delete", "#0", "--done"],
    ["--no-extensions"], ["--app-extension", "ABCDEFGH123", "data"], ["--extension", "0x99", "body"],
    ["--same-delay"], ["-e"], ["-E"],
    ["-O1"], ["-O2"], ["-O3"], ["-U"], ["-U", "-O3"], ["-U", "-O2"], ["--careful", "-O3"],
    ["-O3", "--crop", "3,3+20x15"], ["--rotate-90", "-O2"], ["--flip-vertical", "-U"], ["-i", "-O1"],
    ["--no-extensions", "-O2"], ["-O3", "--no-comments"], ["-d5", "-l2", "-O2"], ["--crop-transparency", "-O3"],
    ["-t", "#000000", "-O2"], ["--disposal=bg", "-O2"], ["-p", "10,10", "-S", "300x300"],
    ["--max-screen", "20x20", "-U"], ["-m", "{0}", "{0}"], ["--multifile", "{0}"], ["--no-ignore-errors", "-O1"],
    ["--optimize=keep-empty", "-O3"], ["-O3", "--unoptimize"],
    # resizing
    ["--resize", "20x20"], ["--resize", "200x150"], ["--scale", "0.5"], ["--scale", "2"], ["--scale", "1.5x0.7"],
    ["--resize-width", "33"], ["--resize-height", "7"], ["--resize-fit", "40x40"], ["--resize-touch", "50x10"],
    ["--resize-geometry", "30x30^"], ["--resize", "1x1"], ["--resize", "300x2"],
    *[["--resize-method", m, size, value] for m in ("sample", "box", "mix", "catrom", "lanczos2", "lanczos3", "mitchell")
      for size, value in (("--resize", "37x29"), ("--scale", "2.3"), ("--scale", "0.37"))],
    ["--resize-colors", "64", "--resize", "30x30"], ["--resize-colors", "256", "--resize-method", "lanczos3", "--scale", "0.6"],
    ["--resize-colors", "8", "--resize-method", "box", "--scale", "0.5"],
    ["-U", "--resize", "50x40"], ["--resize", "50x40", "-O3"], ["-j4", "--resize", "40x40"], ["-j4", "-U", "--resize", "40x40"],
    ["-j4", "-U", "--resize-colors", "128", "--resize-method", "catrom", "--resize", "40x40"],
    ["--crop", "2,2+20x20", "--resize", "10x30"], ["--rotate-90", "--scale", "0.8"], ["-t", "#000000", "--scale", "0.7"],
    # colors: reducing, dithering, colormaps, gamma
    *[["--colors", n] for n in ("2", "3", "7", "16", "129", "255", "256")],
    *[["--colors", n, "--color-method", m, *d] for m in ("diversity", "blend-diversity", "median-cut")
      for n, d in (("4", []), ("32", ["--dither"]), ("200", ["--dither=o8"]))],
    *[["--colors", "12", f"--dither={d}"] for d in (
        "none", "posterize", "default", "fs", "floyd-steinberg", "atkinson", "at", "o3", "o4", "o8", "ro64", "o",
        "ordered", "diag45", "diagonal", "halftone", "half,4,3", "trihalftone,10", "trihalf,147,2", "sqhalftone,5",
        "sqhalf,7,4", "squarehalftone,30,9", "o4,8", "o,3", "o,4,9", "ro64,16", "o,4x5", "o8,1", "halftone,148",
        "sqhalftone,256", "o,4,300", "foo", "o,", "halftone,,3", "o4,99999999999999999999")],
    ["--colors", "5", "--dither", "--no-dither"], ["-f", "--colors", "3", "-O3"], ["--dither=at", "--colors", "64", "-U"],
    ["--colors", "8", "--gamma", "oklab"], ["--colors", "8", "--gamma", "oklab", "--dither"], ["--colors", "8", "--gamma", "srgb"],
    ["--colors", "8", "--gamma", "1.0"], ["--colors", "8", "--gamma", "2.2", "--dither=o4"], ["--colors", "8", "--gamma", "0.5"],
    ["--colors", "8", "--no-gamma"], ["--colors", "8", "--gamma", "bad"], ["--colors", "8", "--gamma", "-1"],
    ["--use-colormap", "web"], ["--use-colormap", "gray", "--dither"], ["--use-colormap", "bw", "--dither=o4"],
    ["--gray"], ["--use-colormap", "{0}", "--dither=atkinson", "{0}"], ["--use-exact-colormap", "web"],
    ["--use-exact-colormap", "bw", "--dither"], ["--use-colormap", "web", "--gamma", "oklab", "--dither=ro64"],
    ["--colors", "16", "--resize", "30x30"], ["--resize", "40x40", "--colors", "64", "--dither"],
    ["--colors", "6", "--crop", "1,1+9x9", "--rotate-90"], ["--colors", "9", "-t", "#000000", "-O2"],
    ["-b", "--colors", "8", "--dither=fs", "{0}", "--dither=atkinson", "{0}", "--dither=fs", "{0}"],
    ["--colors", "4", "-i"], ["--colors", "40", "--careful", "-O3"],
    # lossy
    ["--lossy"], ["--lossy=0"], ["--lossy=1"], ["--lossy=80"], ["--lossy=400"], ["--lossy=80", "-O3"],
    ["--lossy=60", "-i"], ["--lossy=50", "--careful"], ["--lossy=30", "--colors", "32", "--dither"],
    ["--lossy=100", "-U", "-O2"], ["--lossy=200", "--gamma", "1.5"], ["--lossy=-1"],
    # a shell command given the colormap
    ["--transform-colormap", "cat"], ["--transform-colormap", "sed s/0/9/g", "--colors", "8"],
    ["--transform-colormap", "awk '{print 255-$1, 255-$2, 255-$3}'"], ["--transform-colormap", "false"],
    ["--transform-colormap", "head -n 1"], ["--transform-colormap", "cat; echo 1 2 3"], ["--transform-colormap", "true"],
    ["--transform-colormap", "echo bad"], ["--transform-colormap", "cat >&2"], ["--transform-colormap", "exit 3"],
    ["--transform-colormap", "cat", "--transform-colormap", "sort -r", "-O2"],
]
HEAVY = {"e-bad-frame-too-large.gif"}
HEAVY_OPTIONS = [[], ["-I"], ["-O2"], ["-U"], ["--crop", "3,3+20x15"], ["--colors", "8"], ["--lossy=80"]]
ICONS = "/usr/share/httpd/icons"


def corpus():
    folder = os.path.join(HERE, "corpus")
    if os.path.isdir(folder):
        return folder
    part = folder + ".part"
    shutil.rmtree(part, ignore_errors=True)
    os.makedirs(part)

    def put(name, data):
        with open(os.path.join(part, name), "wb") as f:
            f.write(data)

    for name, data in made.edges().items():
        put(f"e-{name}.gif", data)
    put("test-animation.gif", made.animation("test", 120, 90, 40))
    put("own-colors.gif", made.animation("own", 100, 70, 30, colors=256, shared=False))
    put("many-colors.gif", made.many_colors())
    rng = made.random.Random("port")
    for i in range(150):
        put(f"a{i:03d}.gif", made.animation(f"p{i}", rng.randrange(4, 80), rng.randrange(4, 80), rng.randrange(1, 12),
                                            colors=rng.choice((2, 4, 16, 100, 255, 256)), small=rng.random() < 0.5,
                                            shared=rng.random() < 0.7))
    os.replace(part, folder)
    return folder


def case(ref, new, gif, options, limit):
    out = []
    for binary in (ref, new):
        work = tempfile.mkdtemp(prefix="sg-gifsicle-")
        try:
            shutil.copy(gif, os.path.join(work, "in.gif"))
            args = [a.replace("{0}", "in.gif") for a in options]
            if not any("{0}" in a for a in options):
                args.append("in.gif")
            out.append(run_in(binary, args, work, limit))
        finally:
            shutil.rmtree(work)
    return gif, options, out[0], out[1]


def main():
    words, folders, quick, show = [], [], False, 25
    argv = sys.argv[1:]
    while argv:
        word = argv.pop(0)
        if word == "--quick":
            quick = True
        elif word == "--show":
            show = int(argv.pop(0))
        elif word == "--gifs":
            folders.append(argv.pop(0))
        else:
            words.append(word)
    ref, new = programs()
    folders = [corpus()] + ([ICONS] if os.path.isdir(ICONS) else []) + folders
    found = sorted(g for folder in folders for g in glob.glob(os.path.join(folder, "*.gif")))
    found = [g for g in found if not words or any(w in os.path.basename(g) for w in words)]
    light = [g for g in found if os.path.basename(g) not in HEAVY]
    heavy = [] if quick else [g for g in found if os.path.basename(g) in HEAVY]
    print(f"{len(light)} GIFs x {len(OPTIONS)} option sets, {len(heavy)} large GIF(s) x {len(HEAVY_OPTIONS)} alone",
          flush=True)

    total = differ = 0
    start = time.monotonic()

    def seen(result):
        nonlocal total, differ
        gif, options, a, b = result
        total += 1
        if a != b:
            differ += 1
            if differ <= show:
                (ra, fa), (rb, fb) = a, b
                print(f"DIFF {os.path.basename(gif)} {' '.join(options)}: code {ra[0]} {rb[0]}, "
                      f"output {len(ra[1])} {len(rb[1])} bytes, files {sorted(fa)} {sorted(fb)}"
                      f"{'' if fa == fb else ' (contents differ)'}")
                if ra[2] != rb[2]:
                    print(f"  ref: {ra[2][:240]!r}\n  new: {rb[2][:240]!r}")
        if total % 2000 == 0:
            print(f"  {total} runs, {time.monotonic() - start:.0f} s", flush=True)

    with cf.ThreadPoolExecutor(os.cpu_count() or 4) as pool:
        for future in cf.as_completed([pool.submit(case, ref, new, g, o, 120) for g in light for o in OPTIONS]):
            seen(future.result())
    for gif in heavy:
        for options in HEAVY_OPTIONS:
            seen(case(ref, new, gif, options, 600))
    print(f"{total - differ}/{total} the same, {time.monotonic() - start:.0f} s")
    sys.exit(1 if differ else 0)


if __name__ == "__main__":
    main()
