"""Resolve an upstream commit, then stage its archive without modifying any checkout."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from tempfile import TemporaryDirectory
from urllib.parse import quote
from urllib.request import urlopen
from zipfile import ZipFile

PIN = "89e53f4df9dfe80e5fd32af2cd51e1e996c4298f"
PIN_SHA256 = "f65288be094e7832cb364ce415ca25269d50f6b17e27d62bfea06151f27a6c9b"
REPO = "LoveProgramming-cc/Inkpad-gnome"


def main():
    work = Path(sys.argv[1]).resolve()
    rev = sys.argv[2]
    if rev == "pinned":
        sha = PIN
    elif re.fullmatch("[0-9a-f]{40}", rev):
        sha = rev
    else:
        with urlopen(f"https://api.github.com/repos/{REPO}/commits/{quote(rev, safe='')}", timeout=60) as response:
            sha = json.load(response)["sha"]
    if not re.fullmatch("[0-9a-f]{40}", sha):
        raise ValueError("Invalid upstream revision")
    archive = work/"cache"/f"source-{sha}.zip"
    if not archive.exists():
        partial = archive.with_suffix(".part")
        with urlopen(f"https://codeload.github.com/{REPO}/zip/{sha}", timeout=120) as src, partial.open("wb") as dst:
            shutil.copyfileobj(src,dst)
        partial.replace(archive)
    if sha == PIN and hashlib.sha256(archive.read_bytes()).hexdigest() != PIN_SHA256:
        raise ValueError(f"Unexpected pinned upstream archive: {archive}")
    root = work/"source"
    root.mkdir(exist_ok=True)
    prefix = f"Inkpad-gnome-{sha}"
    if not (root/prefix).exists():
        with TemporaryDirectory(dir=root) as tmp, ZipFile(archive) as z:
            for member in z.infolist():
                name = Path(member.filename)
                if name.parts[:1] != (prefix,) or ".." in name.parts:
                    raise ValueError(member.filename)
                z.extract(member,tmp)
            (Path(tmp)/prefix).rename(root/prefix)
    (work/"source.commit").write_text(sha+"\n", encoding="ascii")
    print("Upstream commit",sha,flush=True)


if __name__ == "__main__":
    main()
