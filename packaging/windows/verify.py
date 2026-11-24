"""Check the actual setup and portable payloads in a private data-drive test area."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from zipfile import ZipFile


def digest(stream):
    return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    release, manifest = map(Path,sys.argv[1:])
    hashes = json.loads(manifest.read_text())
    setup, = release.glob("*-Setup.exe")
    portable, = release.glob("*-Portable.zip")
    with ZipFile(portable) as z:
        assert {i.filename for i in z.infolist()} == {"Inkpad/"+n for n in hashes}
        for name, expected in hashes.items():
            with z.open("Inkpad/"+name) as src:
                assert digest(src) == expected, name
    area = manifest.parent / "tests"
    install = area / "安装 space"
    area.mkdir()
    env = dict(os.environ,INKPAD_HOME=str(area/"profile"),
               PATH=os.pathsep.join([os.environ["SystemRoot"]+"\\System32",os.environ["SystemRoot"]]))

    def run(command):
        subprocess.run(command, env=env, cwd=area, check=True, timeout=360,
                       creationflags=subprocess.CREATE_NO_WINDOW)

    # NSIS expects /D=... last and unquoted, including paths with spaces.
    install_command = f'"{setup}" /S /NOREG /D={install}'
    run(install_command)
    for name, expected in hashes.items():
        with (install/name).open("rb") as src:
            assert digest(src) == expected, name
    note = install/"InkpadData/library/验证.inkpad"
    note.parent.mkdir(parents=True)
    run([install/"runtime/bin/python3.14.exe","-I","-B","-X","utf8",
         Path(__file__).with_name("smoke.py"),install/"app",note])
    saved = note.read_bytes()
    run(install_command)
    assert note.read_bytes() == saved
    run([install/"Uninstall.exe","/S"])
    deadline = time.monotonic() + 120
    while (install/"Uninstall.exe").exists() and time.monotonic() < deadline:
        time.sleep(.25)
    assert [p for p in install.rglob("*") if p.is_file()] == [note]
    assert note.read_bytes() == saved
    print(f"Verified {len(hashes)} installed files and ZIP entries, formats, reinstall and uninstall",flush=True)


if __name__ == "__main__":
    main()
