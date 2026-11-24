"""Windows known folders and first-run adoption of pre-profile installations."""
import ctypes
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import uuid
import winreg

DOCUMENTS = "FDD39AD0-238F-46AF-ADB4-6C85480369C7"
LOCAL_APP_DATA = "F1B32785-6FBA-4FCF-9D55-7B8E7F157091"


def known_folder(folder_id):
    guid = (ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID(folder_id).bytes_le)
    result = ctypes.c_wchar_p()
    # DONT_VERIFY also returns configured folders that have not been created yet.
    hr = ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0x4000, None, ctypes.byref(result))
    if hr != 0:
        raise OSError(f"Windows known folder {folder_id}: HRESULT {hr & 0xffffffff:#x}")
    try:
        return Path(result.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(result, ctypes.c_void_p))


def previous_data(install):
    adjacent = install / "InkpadData"
    if adjacent.is_dir():
        return adjacent
    if (install / "Uninstall.exe").is_file():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Uninstall\InkpadGNOME",
                                0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
                old, _ = winreg.QueryValueEx(key, "LegacyDataDir")
            if Path(old).is_absolute() and Path(old).is_dir():
                return Path(old)
        except FileNotFoundError:
            pass
    return None


def adopt_config(home, legacy):
    # Publish preferences, credentials and the existing library selection together.
    # Never merge notebook trees or overwrite a profile already used by this user.
    dest = home / "config"
    if dest.exists():
        return
    home.mkdir(exist_ok=True, parents=True)
    with TemporaryDirectory(dir=home) as tmp:
        staged = Path(tmp) / "config"
        if legacy and (legacy / "config").is_dir():
            shutil.copytree(legacy / "config", staged)
        else:
            staged.mkdir()
        if legacy and (legacy / "library").is_dir():
            library = legacy / "library"
            has_notes = any(p.name not in {".trash", ".deleted"} or not p.is_dir() or any(p.iterdir())
                            for p in library.iterdir())
            settings = staged / "settings.json"
            if has_notes:
                saved = json.loads(settings.read_text(encoding="utf-8")) if settings.exists() else {}
                if not saved.get("library"):
                    saved["library"] = str(library)
                    settings.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        try:
            staged.rename(dest)
        except FileExistsError:
            pass  # A simultaneous first launch already published its complete profile.


def profile(install):
    override = os.environ.get("INKPAD_HOME")
    if override:
        home = Path(override).resolve()
        return home, home / "library"
    if not (install / "Uninstall.exe").exists() and (install / "InkpadData").is_dir():
        home = install / "InkpadData"
        return home, home / "library"
    home = known_folder(LOCAL_APP_DATA) / "Inkpad"
    adopt_config(home, previous_data(install))
    return home, known_folder(DOCUMENTS) / "Inkpad"
