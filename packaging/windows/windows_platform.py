"""Windows library names and CRT date formats for the upstream GNOME modules."""
import ctypes
from pathlib import Path
import time

BIN = Path(__file__).resolve().parents[2] / "runtime/bin"


def cdll(name):
    if name and ".so." in name:
        library, version = name.rsplit(".so.", 1)
        name = str(BIN / f"{library}-{version}.dll")
    return ctypes.CDLL(name)


def strftime(pattern, *args):
    return time.strftime(pattern.replace("%-", "%#"), *args)
