import io
import os
import typing

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
        font = text.font
        pdf.set_font(font.family, '', font.size)
        pdf.set_text_color(text.color.red, text.color.green, text.color.blue)

        align: fpdf.Align
        if text.alignment == Alignment.RIGHT:
            align = fpdf.Align.R
            pdf.set_xy(pdf.x + 3, pdf.y - 1)
        else:
            align = fpdf.Align.L
            pdf.set_xy(pdf.x - 3, pdf.y)

        pdf.cell(
            text.position.width,
            text.position.height,
            text.content,
            align=align
        )

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
