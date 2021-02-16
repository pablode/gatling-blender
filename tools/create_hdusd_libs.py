#**********************************************************************
# Copyright 2020 Advanced Micro Devices, Inc
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#********************************************************************
import os
import platform
import shutil
import subprocess
from pathlib import Path
import argparse


OS = platform.system()


def iterate_files(path, glob, *, ignore_parts=(), ignore_suffix=()):
    for f in path.glob(glob):
        if f.is_dir() or f.suffix in ignore_suffix or any(p in f.parts for p in ignore_parts):
            continue

        yield f


def iterate_copied_files(usd_dir, hdrpr_dir, mx_dir):
    # USD libraries
    for f in iterate_files(usd_dir / "lib", "**/*",
                           ignore_parts=("__pycache__",),
                           ignore_suffix=(".cmake", ".pdb", ".lib", ".def")):
        if "cmake" in f.name or "cmake" in f.relative_to(usd_dir / "lib").parts:
            continue
        yield f, Path("usd") / f.relative_to(usd_dir / "lib")

    for f in iterate_files(usd_dir / "bin", "*",
                           ignore_suffix=('.pdb',)):
        yield f, Path("usd") / f.relative_to(usd_dir / "bin")

    # copy RPR Hydra delegate libraries
    for f in iterate_files(hdrpr_dir / "lib", "**/*",
                           ignore_parts=("__pycache__",),
                           ignore_suffix=(".lib",)):
        yield f, Path("hdrpr") / f.relative_to(hdrpr_dir)

    for f in iterate_files(hdrpr_dir / "libraries", "**/*"):
        yield f, Path("hdrpr") / f.relative_to(hdrpr_dir)

    for f in iterate_files(hdrpr_dir / "materials", "**/*"):
        yield f, Path("hdrpr") / f.relative_to(hdrpr_dir)

    # put all the plugins in the same folder so USD would load them all
    for f in iterate_files(usd_dir / "plugin", "**/*",
                           ignore_suffix=(".lib",)):
        yield f, Path("plugins") / f.relative_to(usd_dir / "./plugin")

    for f in iterate_files(hdrpr_dir / "plugin", "**/*",
                           ignore_suffix=(".lib",)):
        yield f, Path("plugins") / f.relative_to(hdrpr_dir / "./plugin")

    # MaterialX libraries
    for f in iterate_files(mx_dir / "python/MaterialX", "*",
                           ignore_suffix=(".lib",)):
        yield f, Path("materialx") / f.relative_to(mx_dir)

    for f in iterate_files(mx_dir / "libraries", "**/*",
                           ignore_suffix=(".lib",)):
        yield f, Path("materialx") / f.relative_to(mx_dir)

    for f in iterate_files(mx_dir / "resources", "**/*",
                           ignore_suffix=(".lib",)):
        yield f, Path("materialx") / f.relative_to(mx_dir)

    for f in iterate_files(mx_dir / "bin", "*"):
        yield f, Path("materialx") / f.relative_to(mx_dir)


def main():
    ap = argparse.ArgumentParser()

    # Add the arguments to the parser
    ap.add_argument("-usd", required=True, metavar="",
                    help="Directory where USD was built")
    ap.add_argument("-hdrpr", required=True, metavar="",
                    help="Directory where HdRPR was installed")
    ap.add_argument("-mx", required=True, metavar="",
                    help="Directory where MaterialX was built")
    ap.add_argument("-libs", required=False, metavar="",
                    help="Target libs directory")
    ap.add_argument("-v", required=False, action="store_true",
                    help="Visualize copying info")
    args = ap.parse_args()

    if not args.libs:
        args.libs = os.environ['HDUSD_LIBS_DIR']

    libs_dir = Path(args.libs)
    if libs_dir.is_dir():
        shutil.rmtree(str(libs_dir))

    print(f"Copying libs to: {libs_dir}")

    for f, relative in iterate_copied_files(Path(args.usd), Path(args.hdrpr), Path(args.mx)):
        if args.v:
            print(f, '->', relative)

        f_copy = libs_dir / relative
        if not f_copy.parent.is_dir():
            f_copy.parent.mkdir(parents=True)

        shutil.copy(str(f), str(f_copy), follow_symlinks=False)

    if OS == 'Linux':
        print("Configuring rpath")
        patchelf_args = ['patchelf', '--set-rpath', "$ORIGIN/../../usd:$ORIGIN/../../hdrpr/lib",
                         str(libs_dir / 'plugins/usd/hdRpr.so')]
        if args.v:
            print(patchelf_args)

        subprocess.check_call(patchelf_args)

    print("Done.")


if __name__ == "__main__":
    main()