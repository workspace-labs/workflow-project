"""Draw the measured systems diagram using the board's boxes, arrows and text styles."""

from . import paint, theme
from .render_diagram import FRAME, MAIN_WIDTH
from .systems_layout import DETAIL_GAP, LABEL_STYLE


def _words(c, lines, centre, top, style, colour):
    font, size, lead = style
    c.setFont(font, size)
    c.setFillColor(colour)
    for line in lines:
        c.drawCentredString(centre, top - lead / 2 - size * 0.3, line)
        top -= lead
    return top


def draw(c, diagram, left, top):
    """Draw at the given top-left corner. MirrorCanvas supplies the reading direction."""
    for arrow in diagram.arrows:
        points = [(left + x, top - y) for x, y in arrow.points]
        c.setLineWidth(MAIN_WIDTH)
        c.setStrokeColor(theme.ACCENT)
        c.drawPath(paint.rounded_path(c, points, radius=3.0, trim_end=5.5), stroke=1, fill=0)
        paint.arrowhead(c, points[-1], points[-2], theme.ACCENT)
        rect = arrow.label_rect
        _words(c, arrow.label_lines, left + (rect.x0 + rect.x1) / 2, top - rect.y0 - 2,
               LABEL_STYLE, theme.ACCENT)

    for box in diagram.boxes:
        rect = box.rect
        height = rect.y1 - rect.y0
        c.setFillColor(theme.WHITE)
        c.setStrokeColor(theme.INK)
        c.setLineWidth(FRAME)
        c.roundRect(left + rect.x0, top - rect.y1, rect.x1 - rect.x0, height, 8, stroke=1, fill=1)
        centre = left + (rect.x0 + rect.x1) / 2
        words_h = len(box.name_lines) * theme.STEP_TITLE[2]
        if box.detail_lines:
            words_h += DETAIL_GAP + len(box.detail_lines) * theme.STEP_DETAIL[2]
        y = top - rect.y0 - (height - words_h) / 2
        y = _words(c, box.name_lines, centre, y, theme.STEP_TITLE, theme.INK)
        _words(c, box.detail_lines, centre, y - DETAIL_GAP, theme.STEP_DETAIL, theme.INK_SOFT)
