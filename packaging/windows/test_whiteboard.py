"""Exercise the installed app using generated whiteboard content in an isolated profile."""
import io
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

app = Path(sys.argv[1])
sys.path.insert(0, str(app))
from start import configure
home, dlls = configure()

from inkpad.__main__ import App  # configure GI versions before constructing a canvas
import cairo
from gi.repository import GLib, Gtk
from inkpad import model
from inkpad.board_performance import BoardOverview, save_job
from inkpad.canvas import Canvas
from inkpad.window import Window


def pen(x, y):
    return model.Stroke("ball", (0.2, 0.3, 0.4), 2, [(x, y, 0.4), (x + 16, y + 8, 0.8)])


def draw(canvas, n):
    x, y = 120 + n % 20, 80 + n % 30
    canvas._down(x, y, 0.4, False)
    assert canvas._op is not None
    for j in range(1, 9):
        canvas._move(x + 2 * j, y + j, 0.4 + j * 0.04)
    canvas.do_snapshot(Gtk.Snapshot())
    canvas._up(x + 16, y + 8)


doc = model.Document({"board": True})
page, = doc.pages
doc.add_items(page, [pen(i % 25 * 32, i // 25 * 20) for i in range(650)])
tape = model.Stroke("tape", (1, 0.9, 0.1), 10, [(0, 0, 0.5)])
png = io.BytesIO()
cairo.ImageSurface(cairo.FORMAT_ARGB32, 4, 4).write_to_png(png)
doc.add_items(page, [tape, model.Image(40, 60, 30, 20, png.getvalue()),
                     model.Text(80, 30, "test", 14, (0, 0, 0))])
overview = BoardOverview()
doc.listeners.append(overview.changed)
overview.refresh(page)
initial = set(overview.cells)
extra = pen(-10000, -5000)
with patch.object(page.items[0], "polyline", side_effect=AssertionError("Rescanned old ink")):
    doc.add_items(page, [extra])
    overview.refresh(page)
    doc.touch()
    overview.refresh(page)
assert overview.box == model.page_box(page)
doc.undo()
overview.refresh(page)
assert overview.cells == initial
doc.redo()
overview.refresh(page)
assert overview.box == model.page_box(page)
before_erase = list(page.items)
page.items[-1] = pen(-500, 310)
doc.push_diff(page, before_erase)  # eraser can announce only a revision, keeping the same count
overview.refresh(page)
fresh = BoardOverview()
fresh.refresh(page)
assert (fresh.box, fresh.cells) == (overview.box, overview.cells)

doc.path = str(home / "generated-board.inkpad")
reference = doc.snapshot()
deferred = save_job(doc)
tape.open = True
doc.add_items(page, [pen(49, 60)])
assert deferred() == reference
assert save_job(doc)() == doc.snapshot()
canvas = Canvas()
canvas.set_document(doc)
canvas.allocate(800, 600, -1, None)
canvas.do_snapshot(Gtk.Snapshot())
win = SimpleNamespace(doc=doc, canvas=canvas, _save_thread=None, _save_timer=0,
                      _relocate=lambda d: True, _absorb=lambda d: True,
                      toast=lambda msg: errors.append(msg))
errors = []
def finish():
    thread = win._save_thread
    thread.join(30)
    assert not thread.is_alive()
    loop = GLib.MainContext.default()
    deadline = time.monotonic() + 5
    while win._save_thread and time.monotonic() < deadline:
        loop.iteration(False)
    assert not errors and win._save_thread is None

count, revision = len(page.items), doc.rev
Window._autosave(win)
for n in range(20):
    draw(canvas, n)
finish()
assert len(model.Document.load(doc.path).pages[0].items) == count
assert doc.saved_rev == revision and doc.modified
Window._autosave(win)
finish()
assert not doc.modified
reopened = model.Document.load(doc.path)
assert len(reopened.pages[0].items) == count + 20
assert reopened.snapshot()['pages'] == doc.snapshot()['pages']
assert reopened.snapshot()['images'] == [png.getvalue()]
print("Verified whiteboard drawing during autosave, overview updates, undo/redo and reopening")
