# gifsicle's own tests (test/*.testie of its source), run with gifsicle 1.99 and with the SG port:
# the script's exit code, output and standard error must be the same. The tests call `gifsicle`,
# which is each program in turn, and `gifdiff`, gifsicle's, taken from the PATH.
#
#   GIFSICLE_TESTS=path/to/gifsicle-1.99/test python3 tests/testie.py [WORD]...
#
# A WORD keeps only the tests whose names hold it.

import base64
import difflib
import glob
import os
import shutil
import subprocess
import sys
import tempfile

from common import programs


def parse(path):
    section, name = None, None
    test = {"files": {}, "script": ""}
    for line in open(path, encoding="latin-1").read().split("\n"):
        if line.startswith("%"):
            parts = line.split()
            if parts[0] == "%script":
                section = "script"
            elif parts[0] == "%file":
                section, name = "file", parts[-1]
                test["files"][name] = [parts[1:-1], ""]
            else:
                section = "other"
            continue
        if section == "script":
            test["script"] += line + "\n"
        elif section == "file":
            test["files"][name][1] += line + "\n"
    return test


def run(test, binary, gifdiff):
    folder = tempfile.mkdtemp(prefix="sg-gifsicle-testie-")
    try:
        bin_dir, work = os.path.join(folder, "bin"), os.path.join(folder, "w")
        os.mkdir(bin_dir)
        os.mkdir(work)
        os.symlink(binary, os.path.join(bin_dir, "gifsicle"))
        os.symlink(gifdiff, os.path.join(bin_dir, "gifdiff"))
        for name, (flags, body) in test["files"].items():
            with open(os.path.join(work, name), "wb") as f:
                f.write(base64.b64decode(body) if "-e" in flags else body.encode("latin-1"))
        env = dict(os.environ, PATH=bin_dir + os.pathsep + os.environ["PATH"])
        try:
            r = subprocess.run(["bash", "-c", test["script"]], cwd=work, env=env, capture_output=True, timeout=300,
                               stdin=subprocess.DEVNULL)
            return r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            return None, b"", b"TIMEOUT after 300 s"
    finally:
        shutil.rmtree(folder)


def main():
    tests = os.environ.get("GIFSICLE_TESTS")
    if not tests or not os.path.isdir(tests):
        sys.exit("GIFSICLE_TESTS: set it to the test folder of gifsicle 1.99's source")
    gifdiff = shutil.which("gifdiff")
    if not gifdiff:
        sys.exit("no gifdiff on the PATH: it comes with gifsicle")
    ref, new = programs()
    words = sys.argv[1:]
    same = count = 0
    for path in sorted(glob.glob(os.path.join(tests, "*.testie"))):
        base = os.path.basename(path)
        if words and not any(w in base for w in words):
            continue
        test = parse(path)
        count += 1
        a, b = run(test, ref, gifdiff), run(test, new, gifdiff)
        same += a == b
        print(("SAME " if a == b else "DIFF ") + base)
        if a != b:
            if a[0] != b[0]:
                print(f"   code {a[0]} {b[0]}")
            for what, x, y in (("output", a[1], b[1]), ("standard error", a[2], b[2])):
                if x != y:
                    lines = difflib.unified_diff(x.decode("latin-1").split("\n"), y.decode("latin-1").split("\n"),
                                                 "ref", "new", lineterm="", n=1)
                    for line in list(lines)[:14]:
                        print(f"   {what} {line[:200]}")
    print(f"{same}/{count} tests the same")
    sys.exit(0 if same == count else 1)


if __name__ == "__main__":
    main()
