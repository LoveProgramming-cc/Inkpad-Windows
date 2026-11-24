"""Exercise the normal installed profile in a disposable Windows user account."""
import json
from pathlib import Path
import sys

app, local, documents, area = map(Path,sys.argv[1:])
sys.path.insert(0,str(app))
from start import configure

home, dlls = configure()
assert home == local/"Inkpad"
from inkpad import model, settings
from inkpad.library import Store
from profile_paths import adopt_config

store = Store()
assert Path(store.root) == documents/"Inkpad"
note = Path(store.root)/"Inkpad startup check.inkpad"
doc = model.Document()
doc.save(str(note))
assert len(model.Document.load(str(note)).pages) == 1
custom = area/"自选文稿库"
prefs = settings.load()
prefs["library"] = str(custom)
settings.save(prefs)
assert Path(Store().root) == custom and Path(settings.PATH).parent == home/"config"
prefs["library"] = ""
settings.save(prefs)
assert Path(Store().root) == note.parent

legacy = area/"old-install/InkpadData"
(legacy/"config").mkdir(parents=True)
(legacy/"library").mkdir()
(legacy/"library/old.inkpad").write_bytes(note.read_bytes())
for selected in ("",str(custom)):
    (legacy/"config/settings.json").write_text(json.dumps({"library":selected,"language":"ja"}))
    new = area/("custom-profile" if selected else "legacy-profile")
    adopt_config(new,legacy)
    loaded = json.loads((new/"config/settings.json").read_text())
    assert loaded["library"] == (selected or str(legacy/"library")) and loaded["language"] == "ja"
    (new/"config/settings.json").write_text('{"language":"en"}')
    adopt_config(new,legacy)
    assert json.loads((new/"config/settings.json").read_text()) == {"language":"en"}
