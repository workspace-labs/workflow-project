"""The canvas for a right-to-left language: the whole page is mirrored, and the words are not.

Every page is laid out exactly as in English, then flipped left to right: lanes, arrows, step numbers,
table columns, the logo's side. Text and pictures are flipped back where they are drawn, so they read
normally. That is why no page needs a right-to-left version of its own.
"""

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

from . import theme


class MirrorCanvas(Canvas):
    def begin_page(self, page_width):
        """Flips everything drawn on this page from now on. Call it first on every page."""
        self.transform(-1, 0, 0, 1, page_width, 0)

    def drawString(self, x, y, text, mode=None, charSpace=0, direction=None, wordSpace=None, shaping=False):
        self._words(x, y, text, "left")

    def drawRightString(self, x, y, text, mode=None, charSpace=0, direction=None, wordSpace=None, shaping=False):
        self._words(x, y, text, "right")

    def drawCentredString(self, x, y, text, mode=None, charSpace=0, direction=None, wordSpace=None, shaping=False):
        self._words(x, y, text, "centre")

    def _words(self, x, y, text, align):
        self.draw_styled(x, y, [(text, self._fontname, self._fontsize, None)], align)

    def draw_styled(self, x, y, pieces, align="left"):
        """One line made of [(text, font, size, colour or None), ...] in reading order.

        `align` is the English one: "left" means the line starts at x, which on the mirrored page is
        its right-hand end.
        """
        parts = theme.segments([(text, font) for text, font, _, _ in pieces])
        sizes = [pieces[k][2] for _, _, k, _ in parts]
        widths = [pdfmetrics.stringWidth(part, face, size) for (part, face, _, _), size in zip(parts, sizes)]
        total = sum(widths)
        at = {"left": -total, "centre": -total / 2.0, "right": 0.0}[align]
        self.saveState()
        self.translate(x, y)
        self.scale(-1, 1)                      # back the right way round, for the words only
        for n, (part, face, k, mark) in enumerate(parts):
            size, colour = sizes[n], pieces[k][3]
            self.setFont(face, size)
            if colour is not None:
                self.setFillColor(colour)
            where = at
            if mark and n + 1 < len(parts):    # centre the mark on its letter, the next one drawn
                letter = pdfmetrics.stringWidth(parts[n + 1][0][0], parts[n + 1][1], size)
                where += max((letter - theme.MARK_WIDTH * size) / 2.0, 0.0)
            Canvas.drawString(self, where, 0, part)
            at += widths[n]
        self.restoreState()

    def drawImage(self, image, x, y, width=None, height=None, **options):
        self.saveState()
        self.translate(x + width, y)
        self.scale(-1, 1)
        found = Canvas.drawImage(self, image, 0, 0, width, height, **options)
        self.restoreState()
        return found
