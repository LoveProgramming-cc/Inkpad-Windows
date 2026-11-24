"""Entry point for the Windows distribution of Inkpad GNOME."""
import os
from pathlib import Path
import sys
import traceback

APP = Path(__file__).resolve().parent
ROOT = APP.parent
PREFIX = ROOT / "runtime"


def configure():
    sys.path.insert(0, str(APP))
    from profile_paths import profile
    home, library = profile(ROOT)
    home.mkdir(parents=True, exist_ok=True)
    os.environ["INKPAD_HOME"] = str(home)
    os.environ["INKPAD_WINDOWS_DEFAULT_LIBRARY"] = str(library)
    for key in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME",
                "XDG_DATA_HOME", "TMP", "TEMP"):
        folder = home / "runtime" / key.lower()
        folder.mkdir(exist_ok=True, parents=True)
        os.environ[key] = str(folder)
    os.environ.update(
        PATH=str(PREFIX / "bin") + os.pathsep + os.environ.get("PATH", ""),
        GI_TYPELIB_PATH=str(PREFIX / "lib/girepository-1.0"),
        GSETTINGS_SCHEMA_DIR=str(PREFIX / "share/glib-2.0/schemas"),
        XDG_DATA_DIRS=str(PREFIX / "share"),
        GSETTINGS_BACKEND="memory",
        GSK_RENDERER="cairo",
    )
    # Keep the handle alive so delayed GI/ctypes imports use the bundled DLLs.
    dlls = os.add_dll_directory(str(PREFIX / "bin"))
    if sys.stderr is None:
        sys.stdout = sys.stderr = (home / "runtime" / "inkpad.log").open("a", encoding="utf-8", buffering=1)
    return home, dlls


def main():
    home, dlls = configure()
    from inkpad.__main__ import App
    from inkpad import APP_ID
    import hashlib
    app = App()
    # Isolated libraries must not forward file-open events to one another.
    key = hashlib.sha256(os.path.normcase(str(home)).encode("utf-8")).hexdigest()[:16]
    app.set_application_id(APP_ID + ".p" + key)
    return app.run(["inkpad", *sys.argv[1:]])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        if sys.stderr is not None:
            traceback.print_exc()
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, str(exc), "Inkpad", 16)
        sys.exit(1)
