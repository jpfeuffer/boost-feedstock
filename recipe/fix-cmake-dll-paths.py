"""Fix Boost CMake config files to use the correct bin/ location for DLLs on Windows.

On Windows with conda, Boost DLLs are installed to Library/bin/ while the CMake
config files reference them from Library/lib/ (using ${_BOOST_LIBDIR}). This script
patches the CMake config files to:
  1. Add _BOOST_BINDIR = lib/../bin in any file that defines _BOOST_LIBDIR
  2. Use _BOOST_BINDIR for .dll IMPORTED_LOCATION paths
"""
import re
import sys
from pathlib import Path


def patch_cmake_file(path):
    """Patch a single cmake file to fix DLL paths. Returns True if file was modified."""
    content = path.read_text(encoding="utf-8")
    original = content

    # Add _BOOST_BINDIR after any _BOOST_LIBDIR definition (if not already present)
    if "_BOOST_BINDIR" not in content and "_BOOST_LIBDIR" in content:
        content = re.sub(
            r"(get_filename_component\s*\(\s*_BOOST_LIBDIR\s[^)]+\)[^\n]*\n)",
            r'\1get_filename_component(_BOOST_BINDIR "${_BOOST_LIBDIR}/../bin" ABSOLUTE)\n',
            content,
        )

    # Replace ${_BOOST_LIBDIR}/boost_*.dll in IMPORTED_LOCATION lines
    content = re.sub(
        r'\$\{_BOOST_LIBDIR\}/(boost_[^"\s)]+\.dll)',
        r"${_BOOST_BINDIR}/\1",
        content,
    )

    if content != original:
        path.write_text(content, encoding="utf-8")
        return True
    return False


def main(cmake_dir):
    cmake_dir = Path(cmake_dir)
    if not cmake_dir.is_dir():
        print(f"Directory not found: {cmake_dir}", file=sys.stderr)
        sys.exit(1)

    patched = 0
    for cmake_file in sorted(cmake_dir.rglob("*.cmake")):
        if patch_cmake_file(cmake_file):
            patched += 1
            print(f"  patched: {cmake_file.name}")

    print(f"Patched {patched} cmake file(s) in {cmake_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <cmake_dir>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
