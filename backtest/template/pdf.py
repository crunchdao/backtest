import io
import os
import typing
import itertools

import fpdf

from .models import *
from .template import *


class PdfTemplateRenderer(TemplateRenderer):

    DEFAULT_PRIORITIES = {
        Text.__name__.lower(): 50,
        Shape.__name__.lower(): -20,
        Image.__name__.lower(): 10
    }

    def __init__(
        self,
        priorities: typing.Dict[str, int] = None,
        debug=False,
    ) -> None:
        super().__init__()

        if priorities is None:
            priorities = PdfTemplateRenderer.DEFAULT_PRIORITIES

        self.priorities = priorities
        self.debug = debug

    def render(
        self,
        template: Template,
        output: io.FileIO
    ) -> Template:
        pdf = fpdf.FPDF(
            unit="pt"
        )

        families = set()

        for font in template.document.fonts:
            file_name = f"{font.family}.ttf"

            if font.family.lower() in pdf.fonts:
                continue

            if os.path.exists(file_name):
                pdf.add_font(font.family, "", file_name)
            else:
                font.family = "helvetica"

                if file_name not in families:
                    print(f"font {file_name} not found, using {font.family} instead")

            families.add(file_name)

        pdf.set_auto_page_break(False)

        for page in template.document.pages:
            pdf.add_page(
                format=(page.size.x, page.size.y),
            )

            elements = page.elements.copy()
            for index, element in enumerate(elements):
                element._index = index

            elements = sorted(elements, key=lambda x: (
                self.priorities[x.__class__.__name__.lower()], x._index))

            for element in elements:
                pdf.set_xy(element.position.x, element.position.y)

                if isinstance(element, Shape):
                    self._render_shape(pdf, element)
                elif isinstance(element, Text):
                    self._render_text(pdf, element)
                elif isinstance(element, Image):
                    self._render_image(pdf, element)

            if self.debug:
                self._render_debug(pdf, elements)

        pdf.output(output)

    def _render_image(self, pdf: fpdf.FPDF, image: Image):
        pdf.image(
            image.bytes,
            image.position.x, image.position.y,
            image.position.width, image.position.height
        )

    def _render_text(self, pdf: fpdf.FPDF, text: Text):
        align: fpdf.Align
        start_x: int
        start_y: int

        if text.alignment == Alignment.RIGHT:
            align = fpdf.Align.R
            start_x, start_y = pdf.x + 3, pdf.y - 1
        else:
            align = fpdf.Align.L
            start_x, start_y = pdf.x - 3, pdf.y

        font = text.font
        pdf.set_font(font.family, '', font.size)
        space_size = pdf.get_string_width(" ")

        x, y = start_x, start_y

        def find_span(start: int):
            previous = None

            for index, span in enumerate(text.spans):
                if span.start > start:
                    break

                previous = span

            return previous, index

        for index, word in split_words(text.content):
            span, span_index = find_span(index)

            color = span.color or text.color
            pdf.set_text_color(color.red, color.green, color.blue)

            font = span.font or text.font
            pdf.set_font(font.family, '', font.size)
            
            if self.debug:
                if span_index % 2:
                    pdf.set_text_color(255, 0, 0)
                else:
                    pdf.set_text_color(0, 255, 0)

            if word[0] == "\n":
                x = start_x
                y += font.size * len(word)
            elif word[0] == " ":
                x += space_size * len(word)
            else:
                span_width = pdf.get_string_width(word)

                next_x = x + span_width

                width = next_x - start_x
                if width > text.position.width + 2:
                    x = start_x
                    y += font.size
                    next_x = start_x + span_width
                
                pdf.set_xy(x, y)
                pdf.cell(
                    span_width,
                    font.size,
                    word,
                    align=align
                )

                x = next_x

    def _render_shape(self, pdf: fpdf.FPDF, shape: Shape):
        with pdf.new_path(shape.position.x, shape.position.y) as path:
            path.style.fill_color = shape.color.hex_string
            path.style.stroke_color = fpdf.drawing.gray8(0, 0)
            path.style.stroke_opacity = 0

            clip = shape.clip
            if clip:
                clipping_path = fpdf.drawing.ClippingPath()
                clipping_path.rectangle(
                    clip.x, clip.y,
                    clip.width, clip.height,
                )

                path.clipping_path = clipping_path

            for point in shape.points:
                path.line_to(point.x, point.y)

            path.close()

    def _render_debug(self, pdf: fpdf.FPDF, elements: typing.List[Element]):
        for element in elements:
            if isinstance(element, Text):
                pdf.set_draw_color(255, 0, 0)
            elif isinstance(element, Image):
                pdf.set_draw_color(0, 255, 0)
            elif isinstance(element, Shape):
                pdf.set_draw_color(0, 0, 255)
            else:
                continue

            pdf.rect(
                element.position.x,
                element.position.y,
                element.position.width,
                element.position.height
            )


def split_words(text: str):
    for _, group in itertools.groupby(enumerate(text), lambda x: (x[1] == " ", x[1] == "\n")):
        index, part = next(group)
        yield index, part + "".join(x for _, x in group)
