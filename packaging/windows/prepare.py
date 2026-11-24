"""Fetch verified upstream archives and extract the build tools onto the data drive."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile
from urllib.request import urlopen
from zipfile import ZipFile

work = Path(sys.argv[1]).resolve()
cache = work / "cache"
lock = Path(__file__).with_name("dependencies.json")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch(item):
    name, spec = item
    archive = cache / name
    if not archive.is_file() or digest(archive) != spec["sha256"]:
        partial = cache / (name + ".part")
        with urlopen(spec["url"], timeout=120) as src, partial.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        if digest(partial) != spec["sha256"]:
            raise ValueError(f"Checksum mismatch: {name}")
        partial.replace(archive)
    return archive


def copy(src, root, relative):
    dst = (root / relative).resolve()
    if not dst.is_relative_to(root):
        raise ValueError(relative)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("wb") as out:
        shutil.copyfileobj(src, out)


def unpack(archive):
    if archive.name.endswith(".zst"):
        with tarfile.open(archive, "r|zst") as tar:
            for member in tar:
                path = Path(member.name)
                if member.isfile() and path.parts[:1] == ("ucrt64",) and path.parts[1:2] != ("include",) and path.suffix not in {".a",".h"}:
                    with tar.extractfile(member) as src:
                        copy(src, work / "dependencies", path)
        return
    with ZipFile(archive) as z:
        for member in z.infolist():
            name = member.filename
            if member.is_dir():
                continue
            if name.startswith("Contents/VC/"):
                path = name.removeprefix("Contents/")
            elif name.startswith(("c/Include/", "c/bin/", "c/um/x64/", "c/ucrt/x64/")) and "/arm" not in name.lower() and "/x86/" not in name.lower():
                path = "sdk/" + name.removeprefix("c/")
            else:
                continue
            with z.open(member) as src:
                copy(src, work / "toolchain", path)


def main():
    fingerprint = hashlib.sha256(lock.read_bytes() + Path(__file__).read_bytes()).hexdigest()
    marker = work / "dependencies.ready"
    if marker.is_file() and marker.read_text() == fingerprint:
        return
    print("Preparing pinned compiler, SDK and runtime packages", flush=True)
    with ThreadPoolExecutor(4) as pool:
        archives = list(pool.map(fetch, json.loads(lock.read_text()).items()))
    for archive in archives:
        unpack(archive)
    marker.write_text(fingerprint)


if __name__ == "__main__":
    main()
