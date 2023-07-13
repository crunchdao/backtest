import io
import os
import typing
import itertools

import fpdf

from .models import *
from .template import *


@dataclasses.dataclass()
class Word:

    position: Rectangle2
    content: str
    font: Font
    color: Color


@dataclasses.dataclass()
class Line:

    size: Vector2
    words: typing.List[Word]


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
    
    def _compute_lines(self, pdf: fpdf.FPDF, text: Text) -> typing.List[Line]:
        lines = []
        words = []

        def commit_line(min_height: float):
            nonlocal words, lines

            width = 0
            height = min_height

            if len(words):
                width = sum(word.position.width for word in words)
                height = max(word.position.height for word in words)

            lines.append(Line(
                size=Vector2(
                    width,
                    height
                ),
                words=words
            ))
            
            words = []

        font = text.font
        pdf.set_font(font.family, '', font.size)
        space_size = pdf.get_string_width(" ")

        x, y = 0, 0

        def find_span(start: int):
            previous = None

            for index, span in enumerate(text.spans):
                if span.start > start:
                    break

                previous = span

            return previous, index

        span_height = 0

        for index, word in split_words(text.content):
            span, span_index = find_span(index)

            color = span.color or text.color
            font = span.font or text.font
            pdf.set_font(font.family, '', font.size)
            
            if self.debug:
                if span_index % 2:
                    pdf.set_text_color(255, 0, 0)
                else:
                    pdf.set_text_color(0, 255, 0)
                
            span_height = font.size

            if word[0] == "\n":
                line_count = len(word)

                for _ in range(line_count):
                    commit_line(span_height)

                x = 0
                y += font.size * line_count
            elif word[0] == " ":
                x += space_size * len(word)
                span_width = pdf.get_string_width(word)
            else:
                span_width = pdf.get_string_width(word)

                next_x = x + span_width

                width = next_x
                height = span_height

                if width > text.position.width + 2:
                    commit_line(span_height)

                    x = 0
                    y += height
                    next_x = span_width
                
                words.append(Word(
                    position=Rectangle2(
                        x, y,
                        span_width, span_height
                    ),
                    content=word,
                    font=font,
                    color=color
                ))

                x = next_x

        commit_line(span_height)
        
        return lines

    def _render_text(self, pdf: fpdf.FPDF, text: Text):
        if right := (text.alignment == Alignment.RIGHT):
            start_x = pdf.x - 3
            start_y = pdf.y + 1
        else:
            start_x = pdf.x - 3
            start_y = pdf.y + 1
        
        lines = self._compute_lines(pdf, text)

        height_sum = sum(line.size.y for line in lines)
        free_space = max(0, text.position.height - height_sum)
        extra_space = free_space / (len(lines) + 1)
        
        debug = print if text.content == "16.17%" else lambda *x: ...

        for index, line in enumerate(lines, 1):
            if right:
                last_x = max(word.position.x + word.position.width for word in line.words) if len(line.words) else 0
                right_offset = text.position.width - last_x

            for word in line.words:
                pdf.set_text_color(word.color.red, word.color.green, word.color.blue)
                pdf.set_font(word.font.family, '', word.font.size)

                x = start_x + word.position.x
                y = start_y + word.position.y + (index * extra_space)

                if right:
                    x += right_offset

                pdf.set_xy(x, y)
                pdf.cell(
                    word.position.width,
                    word.position.height,
                    word.content,
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


def split_words(text: str):
    for _, group in itertools.groupby(enumerate(text), lambda x: (x[1] == " ", x[1] == "\n")):
        index, part = next(group)
        yield index, part + "".join(x for _, x in group)
