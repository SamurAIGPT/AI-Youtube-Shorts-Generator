import os
import shutil
from typing import Optional


def _search_winget_packages() -> Optional[str]:
    """Search common WinGet package locations for ffmpeg.exe and return its bin dir."""
    local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
    packages_root = os.path.join(local_app, "Microsoft", "WinGet", "Packages")
    if not os.path.isdir(packages_root):
        return None

    for entry in os.listdir(packages_root):
        if not entry.lower().startswith("gyan.ffmpeg") and "ffmpeg" not in entry.lower():
            # still allow other ffmpeg package folders
            continue
        full = os.path.join(packages_root, entry)
        # Walk a few levels under the package entry to find a bin/ffmpeg.exe
        for root, dirs, files in os.walk(full):
            if "ffmpeg.exe" in files:
                return root
            # avoid extremely deep recursion
            if root.count(os.sep) - full.count(os.sep) > 6:
                dirs[:] = []
    return None


def _search_common_locations() -> Optional[str]:
    cand = []
    cand.append(os.path.join("C:", "Program Files", "ffmpeg", "bin"))
    cand.append(os.path.join("C:", "Program Files (x86)", "ffmpeg", "bin"))
    cand.append(os.path.expanduser("~\\AppData\\Local\\Programs\\ffmpeg\\bin"))
    cand.append(os.path.expanduser("~\\AppData\\Local\\Microsoft\\WindowsApps"))
    for p in cand:
        if os.path.exists(os.path.join(p, "ffmpeg.exe")):
            return p
    return None


def ensure_ffmpeg_on_path() -> None:
    """Ensure ffmpeg/ffprobe are available on PATH for local mode.

    If not present, attempt to find them in common WinGet or Program Files
    locations and prepend that folder to PATH at runtime.
    """
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return

    # Try WinGet packages area first
    found = _search_winget_packages()
    if not found:
        found = _search_common_locations()

    if found:
        # Prepend so subprocesses pick it up
        os.environ["PATH"] = found + os.pathsep + os.environ.get("PATH", "")
        if shutil.which("ffmpeg") and shutil.which("ffprobe"):
            return

    raise RuntimeError(
        "ffmpeg and ffprobe are required for --mode local. Could not find them on PATH.\n"
        "If you installed via winget, add the package's bin folder to PATH, for example:\n"
        "  C:\\Users\\<you>\\AppData\\Local\\Microsoft\\WinGet\\Packages\\<Gyan.FFmpeg...>\\...\\bin\n"
        "Or reinstall: winget install --id Gyan.FFmpeg"
    )
