"""Fix Boost CMake config files to use the correct bin/ location for DLLs on Windows.

On Windows with conda, Boost DLLs are installed to Library/bin/ while the CMake
config files reference them from Library/lib/ (using ${_BOOST_LIBDIR}). This script
patches the CMake config files to:
  1. Add _BOOST_BINDIR = lib/../bin in any file that defines _BOOST_LIBDIR
     (these are the per-library *-config.cmake wrapper files)
  2. Use _BOOST_BINDIR for .dll IMPORTED_LOCATION paths
     (these are the variant config files, e.g. boost_date_time.lib,
      which CMake includes from the wrapper and reuse _BOOST_LIBDIR from
      the parent scope)

Note: boost's cmake install generates variant config files named after the
library artifact (e.g. boost_date_time.lib, boost_filesystem.lib).  These
files contain CMake code despite their .lib extension and are NOT binary
import libraries.
"""
import re
import sys
from pathlib import Path


def patch_cmake_file(path):
    """Patch a single cmake file to fix DLL paths. Returns True if file was modified."""
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return False
    original = content

    # Add _BOOST_BINDIR after any _BOOST_LIBDIR definition (if not already present).
    # This applies to the per-library *-config.cmake wrapper files.
    if "_BOOST_BINDIR" not in content and "_BOOST_LIBDIR" in content:
        content = re.sub(
            r"(get_filename_component\s*\(\s*_BOOST_LIBDIR\s[^)]+\)[^\n]*\n)",
            r'\1get_filename_component(_BOOST_BINDIR "${_BOOST_LIBDIR}/../bin" ABSOLUTE)\n',
            content,
        )

    # Replace ${_BOOST_LIBDIR}/boost_*.dll in IMPORTED_LOCATION lines.
    # This applies to both the wrapper .cmake files and the variant config
    # files (e.g. boost_date_time.lib) that CMake includes from the wrapper.
    # _BOOST_BINDIR is available in those included files because CMake's
    # include() shares the caller's variable scope.
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
    # rglob("*") to cover both *.cmake wrapper files and *.lib variant config
    # files (boost's cmake install uses the library artifact name as the cmake
    # include filename, so variant files have extensions like .lib or .a).
    for cmake_file in sorted(f for f in cmake_dir.rglob("*") if f.is_file()):
        if patch_cmake_file(cmake_file):
            patched += 1
            print(f"  patched: {cmake_file.name}")

    print(f"Patched {patched} cmake file(s) in {cmake_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <cmake_dir>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
