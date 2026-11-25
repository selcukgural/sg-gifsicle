# What the tests share: the two programs compared, and how one run of each is captured.
#
#   GIFSICLE     the reference, gifsicle 1.99 (default: `gifsicle` on the PATH)
#   SG_GIFSICLE  the SG port (default: `gifsicle` next to this repository, where the README builds it)

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def program(variable, default):
    path = os.environ.get(variable) or default
    found = shutil.which(path) if os.sep not in path else (path if os.access(path, os.X_OK) else None)
    if not found:
        sys.exit(f"{variable}: no program at {path!r}; set {variable} to it")
    return os.path.abspath(found)


def programs():
    ref = program("GIFSICLE", "gifsicle")
    new = program("SG_GIFSICLE", os.path.join(os.path.dirname(ROOT), "gifsicle"))
    version = subprocess.run([ref, "--version"], capture_output=True, text=True).stdout.split("\n")[0]
    if not version.endswith(" 1.99"):
        sys.exit(f"GIFSICLE is {version!r}, not gifsicle 1.99")
    return ref, new


def run_in(binary, args, cwd, limit):
    """Runs `binary` in `cwd` with no input (`#0` and `-` would wait for it), and gives its exit
    code, output and standard error, and every file in `cwd` after it but `in.gif`."""
    try:
        r = subprocess.run([binary] + args, cwd=cwd, capture_output=True, timeout=limit, stdin=subprocess.DEVNULL)
        res = (r.returncode, r.stdout, r.stderr)
    except subprocess.TimeoutExpired:
        res = (None, b"", f"TIMEOUT after {limit} s".encode())
    files = {}
    for name in sorted(os.listdir(cwd)):
        if name != "in.gif":
            with open(os.path.join(cwd, name), "rb") as f:
                files[name] = f.read()
    return res, files
