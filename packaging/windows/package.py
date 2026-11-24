"""Build the upstream GNOME edition as a relocatable Windows x64 app and NSIS installer."""
import ast
import struct
import re
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid
from zipfile import ZIP_DEFLATED, ZipFile

import sys
SOURCE = Path(__file__).resolve().parent
WORK = Path(sys.argv[1]).resolve()
COMMIT = (WORK/"source.commit").read_text().strip()
ROOT = WORK/"source"/("Inkpad-gnome-"+COMMIT)
KIT = WORK / 'toolchain'
SDK = '10.0.22621.0'
VC = KIT / 'VC/Tools/MSVC/14.44.35207'

def version():
    for node in ast.parse((ROOT/"inkpad/__init__.py").read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in node.targets):
            value = ast.literal_eval(node.value)
            if isinstance(value, str) and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value) and all(int(n)<65536 for n in value.split(".")):
                return value
    raise ValueError("Expected numeric major.minor.patch in inkpad/__init__.py")

VERSION = version()
BASE = WORK
DEPS = BASE / "dependencies/ucrt64"
LABEL = f"Inkpad-{VERSION}-win10-x64"


def keep(path):
    parts = path.parts
    if parts[0] == "bin":
        return path.suffix.lower() == ".dll" or path.name in {"python3.14w.exe","python3.14.exe"}
    if parts[0] == "etc":
        return parts[1] in {"fonts","ssl","pkcs11"}
    if parts[0] == "lib":
        if parts[1] == "python3.14":
            return not {"__pycache__", "test", "tests", "idlelib", "ensurepip", "turtledemo",
                        "config-3.14","Tools","tkinter","venv"}.intersection(parts[2:]) and path.suffix not in {".pyc",".cpp",".c"}
        return parts[1] in {"gdk-pixbuf-2.0","girepository-1.0","ossl-modules","pkcs11","p11-kit"}
    if parts[0] == "share":
        if parts[1] == "locale":
            return parts[2].split("_")[0] in {"zh","ja","en"}
        return parts[1] in {"licenses","glib-2.0","fontconfig","gtk-4.0","mime","icons","poppler",
                            "zoneinfo","libthai","icu","p11-kit"}
    return False


def stage_runtime(root, env):
    for f in DEPS.rglob("*"):
        rel = f.relative_to(DEPS)
        if f.is_file() and keep(rel):
            dest = root / rel
            dest.parent.mkdir(exist_ok=True, parents=True)
            if f.name in {"python3.14.exe","python3.14w.exe"}:
                shutil.copyfile(f,dest)
            else:
                shutil.copyfile(f, dest)
    # Poppler resolves its installed CMaps through narrow Win32 paths. Give
    # both Python hosts a UTF-8 process code page on Windows 10 1903+.
    mt=KIT/"sdk/bin"/SDK/"x64/mt.exe"
    for name in ("python3.14.exe","python3.14w.exe"):
        exe=root/"bin"/name
        manifest=root.parents[2]/(name+".manifest")
        subprocess.run([mt,"-nologo",f"-inputresource:{exe};#1",f"-out:{manifest}"],env=env,check=True)
        xml=manifest.read_text(encoding="utf-8-sig")
        if xml.count("<windowsSettings>")!=1:raise RuntimeError("Unexpected Python application manifest")
        utf8='<activeCodePage xmlns="http://schemas.microsoft.com/SMI/2019/WindowsSettings">UTF-8</activeCodePage>'
        manifest.write_text(xml.replace("<windowsSettings>","<windowsSettings>"+utf8),encoding="utf-8")
        subprocess.run([mt,"-nologo","-manifest",manifest,f"-outputresource:{exe};#1"],env=env,check=True)
    # GTK resolves relative DLL names in the loader cache against its runtime prefix.
    cache = root / "lib/gdk-pixbuf-2.0/2.10.0/loaders.cache"
    result = subprocess.check_output([DEPS/"bin/gdk-pixbuf-query-loaders.exe"], env=env)
    cache.write_bytes(b"\n".join(line for line in result.splitlines() if not line.startswith(b"#"))+b"\n")
    subprocess.run([DEPS/"bin/glib-compile-schemas.exe",root/"share/glib-2.0/schemas"],env=env,check=True)
    if not list((root/"bin").glob("libpoppler-glib-*.dll")):raise RuntimeError("Missing Poppler GLib")


def stage_app(upstream, payload, env):
    app = payload / "app"
    source = upstream / "inkpad"
    shutil.copytree(source,app/"inkpad",ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copyfile(SOURCE/"windows_platform.py",app/"inkpad/windows_platform.py")
    for stem in ("ptext","pdf","library","prefs","window"):
        path = app / "inkpad" / (stem+".py")
        text = path.read_text(encoding="utf-8")
        if stem in {"ptext","pdf"}:
            text = text.replace("import ctypes\n","import ctypes\nfrom .windows_platform import cdll\n",1)
            text = text.replace("ctypes.CDLL(", "cdll(")
        else:
            text = text.replace("import time\n","import time\nfrom .windows_platform import strftime\n",1)
            if "from .windows_platform import strftime" not in text:raise ValueError(stem)
            text = text.replace("time.strftime(", "strftime(")
        path.write_text(text,encoding="utf-8")
    shutil.copyfile(SOURCE/"start.py",app/"start.py")
    shutil.copyfile(upstream/"LICENSE",payload/"LICENSE")
    shutil.copyfile(upstream/"THIRD-PARTY-NOTICES.md",payload/"THIRD-PARTY-NOTICES.md")
    shutil.copyfile(SOURCE/"README.md",payload/"README.md")
    target = payload/"runtime/share/icons/hicolor/scalable/apps"
    target.mkdir(exist_ok=True,parents=True)
    shutil.copyfile(upstream/"data/io.github.inkpad.Inkpad.svg",target/"io.github.inkpad.Inkpad.svg")
    python = payload/"runtime/bin/python3.14.exe"
    subprocess.run([python,"-I","-B","-m","compileall","-q","--invalidation-mode","checked-hash",
                    "-s",app,"-p","Inkpad",app],env=env,check=True)
    compiled, = (app/"__pycache__").glob("start.cpython-*.pyc")
    shutil.copyfile(compiled,app/"start.pyc")


def compile_launcher(upstream,work,payload,env):
    ico = work/"Inkpad.ico"
    png = work/"Inkpad.png"
    images = []
    for size in (16, 24, 32, 48, 64, 128, 256):
        subprocess.run([DEPS/"bin/rsvg-convert.exe","-w",str(size),"-h",str(size),"-o",png,
                        upstream/"data/io.github.inkpad.Inkpad.svg"],env=env,check=True)
        images.append((size,png.read_bytes()))
    offset = 6 + 16 * len(images)
    with ico.open("wb") as out:
        out.write(struct.pack("<HHH",0,1,len(images)))
        for size, data in images:
            out.write(struct.pack("<BBBBHHII",size % 256,size % 256,0,0,1,32,len(data),offset))
            offset += len(data)
        for _, data in images:
            out.write(data)
    rc = work/"Inkpad.rc"
    numeric = VERSION.replace('.', ',') + ',0'
    rc.write_text(f'1 ICON "Inkpad.ico"\n1 VERSIONINFO\n FILEVERSION {numeric}\n PRODUCTVERSION {numeric}\n'
                  'BEGIN\nBLOCK "StringFileInfo"\nBEGIN\nBLOCK "040904B0"\nBEGIN\n'
                  'VALUE "ProductName", "Inkpad"\nVALUE "FileDescription", "Inkpad"\n'
                  f'VALUE "FileVersion", "{VERSION}"\nEND\nEND\nEND\n',encoding="ascii")
    sdk = KIT/"sdk"
    inc = sdk/"Include"/SDK
    env = dict(env,INCLUDE=os.pathsep.join(map(str,[VC/"include",inc/"um",inc/"ucrt",inc/"shared",inc/"winrt"])),
               LIB=os.pathsep.join(map(str,[VC/"lib/x64",sdk/"um/x64",sdk/"ucrt/x64"])))
    subprocess.run([sdk/"bin"/SDK/"x64/rc.exe","/nologo",rc.name],cwd=work,env=env,check=True)
    subprocess.run([VC/"bin/Hostx64/x64/cl.exe","/nologo","/MT","/O2","/std:c++17","/EHsc","/utf-8",
                    SOURCE/"launcher.cpp","/Fe:"+str(payload/"Inkpad.exe"),"/link","/subsystem:windows",
                    "Inkpad.res","shell32.lib","user32.lib"],env=env,cwd=work,check=True)
    subprocess.run([VC/"bin/Hostx64/x64/cl.exe","/nologo","/MT","/O2","/std:c++17","/EHsc","/utf-8",
                    SOURCE/"check_shortcut.cpp","/Fe:check_shortcut.exe","/link","ole32.lib","uuid.lib"],
                   env=env,cwd=work,check=True)
    return ico


def main():
    work=BASE/("build-"+uuid.uuid4().hex[:8]);release=work/"release";payload=release/"Inkpad"
    payload.mkdir(parents=True);source=ROOT
    env=dict(os.environ,TEMP=str(WORK/"tmp"),TMP=str(WORK/"tmp"),PATH=str(DEPS/"bin")+os.pathsep+os.environ["PATH"])
    print(f"Staging in {work}",flush=True)
    stage_runtime(payload/"runtime",env);stage_app(source,payload,env)
    (payload/"UPSTREAM.txt").write_text("https://github.com/LoveProgramming-cc/Inkpad-gnome/commit/"+COMMIT+"\n", encoding="ascii")
    ico=compile_launcher(source,work,payload,env)
    files=sorted(p.relative_to(payload) for p in payload.rglob("*") if p.is_file())
    dirs=sorted({d for p in files for d in p.parents if d!=Path(".")},key=lambda d:(-len(d.parts),str(d)))
    remove=work/"remove.nsh"
    def nsis(p):return str(p).replace("$","$$")
    remove.write_text("\n".join([f'Delete "$INSTDIR\\{nsis(f)}"' for f in files]+
                                [f'RMDir "$INSTDIR\\{nsis(d)}"' for d in dirs]),encoding="utf-8-sig")
    setup=release/(LABEL+"-Setup.exe");portable=release/(LABEL+"-Portable.zip")
    nsis_tool=next(DEPS.rglob("makensis.exe"))
    subprocess.run([nsis_tool,"/V2","/INPUTCHARSET","UTF8",f"/DVERSION={VERSION}",f"/DPAYLOAD={payload}",
                    f"/DSETUP={setup}",f"/DICON={ico}",f"/DREMOVE_FILES={remove}",SOURCE/"setup.nsi"],env=env,check=True)
    with ZipFile(portable,"w",ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(payload/p,(Path("Inkpad")/p).as_posix())
    with ZipFile(portable) as z:
        if z.testzip() is not None or len(z.infolist())!=len(files):raise RuntimeError("Incomplete portable ZIP")
    manifest={str(p).replace("\\","/"):hashlib.sha256((payload/p).read_bytes()).hexdigest() for p in files}
    (work/"payload.json").write_text(json.dumps(manifest),encoding="utf-8")
    (release/"SHA256.txt").write_text("".join(hashlib.sha256(p.read_bytes()).hexdigest()+"  "+p.name+"\n"
                                             for p in (setup,portable)),encoding="ascii")
    subprocess.run([sys.executable, "-I", "-B", SOURCE/"verify.py", release, work/"payload.json"],env=env,check=True)
    out=WORK/"dist"
    out.mkdir(exist_ok=True)
    for artifact in (setup,portable,release/"SHA256.txt"):
        os.replace(artifact,out/artifact.name)
    print(f"Verified Windows packages: {out}",flush=True)


if __name__=="__main__":main()
