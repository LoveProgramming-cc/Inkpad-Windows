import sys
from pathlib import Path

app, note = map(Path,sys.argv[1:])
sys.path.insert(0,str(app))
from start import configure
home, dlls = configure()

import cairo
from gi.repository import GdkPixbuf
from inkpad import goodnotes, model, pdf
from inkpad.__main__ import App

doc = model.Document()
stroke = model.Stroke("ball",(.1,.3,.6),2,[(20,20,.4),(42,65,.8)])
doc.add_items(doc.pages[0],[stroke])
doc.save(str(note))
reopened = model.Document.load(str(note))
assert reopened.pages[0].items[0].pts == stroke.pts
model.export_pdf(reopened,str(home/"test.pdf"))
background = pdf.PdfDoc((home/"test.pdf").read_bytes())
assert background.n_pages == 1
surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,300,400)
background.render(0,cairo.Context(surface))
assert any(surface.get_data())
model.export_png(reopened.pages[0],str(home/"test.png"),scale=1)
assert GdkPixbuf.Pixbuf.new_from_file(str(home/"test.png")).get_width() > 0
goodnotes.save(reopened,str(home/"test.goodnotes"),"测试")
assert goodnotes.load(str(home/"test.goodnotes"))[2]["strokes"] == 1
