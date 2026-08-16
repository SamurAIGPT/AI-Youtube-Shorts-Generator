"""CLI entry point for the creator-profile clipping workflow."""
import sys
from pathlib import Path

# Windows uses 'charmap' by default, which can't encode Unicode characters
# like →. Reconfigure stdout/stderr to UTF-8 so output works on all platforms.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def _run_creator_workflow() -> int:
    """Expose the video skill's all-in-one creator-profile workflow from this CLI."""
    script_dir = Path(__file__).resolve().parent / "skills" / "video" / "scripts"
    sys.path.insert(0, str(script_dir))
    from creator_workflow import main as workflow_main
    return workflow_main()


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "video-workflow":
        sys.argv.pop(1)
    return _run_creator_workflow()


if __name__ == "__main__":
    sys.exit(main())
