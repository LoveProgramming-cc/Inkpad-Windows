"""Check the actual setup and portable payloads in a private data-drive test area."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import winreg
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
    powershell = Path(os.environ["SystemRoot"])/"System32/WindowsPowerShell/v1.0/powershell.exe"
    def shell_query(script):
        return subprocess.check_output([powershell,"-NoProfile","-NonInteractive","-Command",
            "$ErrorActionPreference='Stop';[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"+script],
            env=env, cwd=area, encoding="utf-8", timeout=45, creationflags=subprocess.CREATE_NO_WINDOW).strip()

    # Hosted runners use both real Windows shell folders. Local tests use private folders.
    real_shell = os.environ.get("INKPAD_VERIFY_REAL_SHELL") == "1"
    if real_shell:
        local_app_data = Path(shell_query("[Environment]::GetFolderPath('LocalApplicationData')"))
        install = local_app_data/"Programs/Inkpad"
        documents = Path(shell_query("[Environment]::GetFolderPath('MyDocuments','DoNotVerify')"))
        assert install.drive.upper() == "C:" and not install.exists()
        assert not (local_app_data/"Inkpad").exists() and not (documents/"Inkpad").exists()
        key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\InkpadGNOME"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key):
                raise RuntimeError("Real-shell tests require a clean Windows profile")
        except FileNotFoundError:
            pass
        dirs = [Path(shell_query(f"[Environment]::GetFolderPath('{kind}','DoNotVerify')"))
                for kind in ("DesktopDirectory","Programs")]
    else:
        dirs = [install/".test-shell"/kind for kind in ("Desktop","Programs")]
    links = [d/"Inkpad.lnk" for d in dirs]
    assert all(d.is_absolute() for d in dirs) and not any(p.exists() for p in links)

    def verify_links():
        for link in links:
            assert link.is_file(), link
            run([manifest.parent/"check_shortcut.exe",link,install])

    def run(command):
        subprocess.run(command, env=env, cwd=area, check=True, timeout=360,
                       creationflags=subprocess.CREATE_NO_WINDOW)

    # NSIS expects /D=... last and unquoted, including paths with spaces.
    options = "/S" if real_shell else "/S /NOREG"
    install_command = f'"{setup}" {options}' if real_shell else f'"{setup}" {options} /D={install}'
    run(install_command)
    verify_links()
    for name, expected in hashes.items():
        with (install/name).open("rb") as src:
            assert digest(src) == expected, name
    if real_shell:
        default_env = env.copy()
        default_env.pop("INKPAD_HOME",None)
        python = install/"runtime/bin/python3.14.exe"
        notebook = documents/"Inkpad/Inkpad startup check.inkpad"
        subprocess.run([python,"-I","-B","-X","utf8",Path(__file__).with_name("test_profile.py"),
                        install/"app",local_app_data,documents,area],env=default_env,check=True,timeout=90)
        default_env["INKPAD_TEST_EXE"] = str(install/"runtime/bin/python3.14w.exe")
        with subprocess.Popen([install/"Inkpad.exe",notebook],env=default_env,cwd=area) as app:
            try:
                subprocess.run([powershell,"-NoProfile","-NonInteractive","-Command",
                    "$end=(Get-Date).AddSeconds(40); do { "
                    "$p=Get-Process -Name python3.14w -ErrorAction SilentlyContinue | Where-Object {"
                    "$_.Path -eq $env:INKPAD_TEST_EXE -and $_.MainWindowTitle -like '*Inkpad startup check*'}; "
                    "if ($p -and $p.CloseMainWindow()) {exit 0}; Start-Sleep -Milliseconds 250 "
                    "} while ((Get-Date) -lt $end); exit 1"],env=default_env,check=True,timeout=50)
                assert app.wait(timeout=20) == 0
            finally:
                if app.poll() is None:
                    subprocess.run(["taskkill.exe","/PID",str(app.pid),"/T","/F"],env=default_env)
        assert not (install/"InkpadData").exists()
        print(f"Started and closed Inkpad.exe from {install}; reopened notebook from {documents}",flush=True)
    note = install/"InkpadData/library/验证.inkpad"
    note.parent.mkdir(parents=True)
    run([install/"runtime/bin/python3.14.exe","-I","-B","-X","utf8",
         Path(__file__).with_name("smoke.py"),install/"app",note])
    run([install/"runtime/bin/python3.14.exe","-I","-B","-X","utf8",
         Path(__file__).with_name("test_drive_login.py"),install/"app"])
    saved = note.read_bytes()
    links[0].unlink()
    run(install_command)
    verify_links()
    assert note.read_bytes() == saved
    run([install/"Uninstall.exe","/S"])
    deadline = time.monotonic() + 120
    while (install/"Uninstall.exe").exists() and time.monotonic() < deadline:
        time.sleep(.25)
    assert [p for p in install.rglob("*") if p.is_file()] == [note]
    assert note.read_bytes() == saved
    assert not any(p.exists() for p in links), links
    if real_shell:
        assert notebook.is_file()
    print("Verified desktop and Start menu shortcuts, reinstall repair and uninstall removal",flush=True)
    print(f"Verified {len(hashes)} installed files and ZIP entries, formats, reinstall and uninstall",flush=True)


if __name__ == "__main__":
    main()
