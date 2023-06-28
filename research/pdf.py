import fpdf
import fpdf.drawing
import os
import typing
import dataclasses
import json
import tqdm
import io
import datetime

Identifier = typing.Any
NaturalIdentifier = str


@dataclasses.dataclass
class Vector2:

    x: int | float
    y: int | float

    def __add__(self, other):
        if isinstance(other, Vector2):
            return Vector2(
                self.x + other.x,
                self.y + other.y,
            )

        if isinstance(other, (int, float)):
            return Vector2(
                self.x + other,
                self.y + other,
            )

        raise ValueError(f"unsupported operator with: {type(other)}")

    @staticmethod
    def zero():
        return Vector2(0, 0)


@dataclasses.dataclass
class Rectangle2:

    x: int | float
    y: int | float
    width: int | float
    height: int | float

    @property
    def tuple(self):
        return (self.x, self.y, self.width, self.height)


@dataclasses.dataclass
class Color:

    red: int
    green: int
    blue: int
    alpha: int

    @property
    def hex_string(self) -> typing.Tuple[int, int, int]:
        return '#%02x%02x%02x%02x' % (
            int(self.red),
            int(self.green),
            int(self.blue),
            int(self.alpha),
        )

    @staticmethod
    def black() -> "Color":
        return Color(0, 0, 0, 255)


@dataclasses.dataclass
class Element:

    id: Identifier
    natural_id: NaturalIdentifier
    position: Rectangle2


@dataclasses.dataclass
class Shape(Element):

    points: typing.List[Vector2]
    color: Color
    clip: Rectangle2 = None


@dataclasses.dataclass
class Font:

    family: str
    size: int


@dataclasses.dataclass
class Text(Element):

    content: str
    font: Font
    color: Color


@dataclasses.dataclass
class Image(Element):

    path: str


@dataclasses.dataclass
class Page:

    size: Vector2
    elements: typing.List[Element]


@dataclasses.dataclass
class Document:

    pages: typing.List[Page]

    @property
    def fonts(self) -> typing.List[Font]:
        return list(
            element.font
            for page in self.pages
            for element in page.elements
            if isinstance(element, Text)
        )


class Template:

    name: str
    document: Document
    slots: typing.Dict[NaturalIdentifier | Identifier, typing.List[Element]]

    def __init__(
        self,
        name: str,
        document: Document
    ) -> None:
        self.name = name
        self.document = document

        self.slots = {}
        for page in document.pages:
            for element in page.elements:
                if element.id in self.slots:
                    self.slots[element.id].append(element)
                else:
                    self.slots[element.id] = [element]

                if element.natural_id in self.slots:
                    self.slots[element.natural_id].append(element)
                else:
                    self.slots[element.natural_id] = [element]

    def apply(self, variables: typing.Dict[NaturalIdentifier | Identifier, typing.Any]):
        for key, value in variables.items():
            self.set(key, value)

    def set(self, key: NaturalIdentifier | Identifier, value: typing.Any):
        for element in self.slots.get(key, []):
            if isinstance(element, Text):
                text = element
                text.content = str(value)
            elif isinstance(element, Image):
                image = element
                image.path = str(value)


class TemplateLoader:

    def load(path: str) -> Template:
        raise NotImplemented()


class TemplateRenderer:

    def render(self, template: Template, output: io.FileIO) -> Template:
        raise NotImplemented()


class SketchTemplateLoader(TemplateLoader):

    def load(self, sketch: str) -> Template:
        elements: typing.List[Element]

        def find(layer: dict, absolute_offset: Vector2, clip: Rectangle2):
            id = layer["do_objectID"]
            natural_id = layer["name"]

            local = self._get_frame_xy(layer)
            size = self._get_frame_wh(layer)
            absolute = local + absolute_offset

            position = Rectangle2(
                absolute.x, absolute.y,
                size.x, size.y,
            )

            class_ = layer["_class"]
            match class_:
                case "shapePath":
                    (
                        points,
                        color
                    ) = self._extract_shape_points(
                        layer,
                        absolute,
                        size
                    )

                    elements.append(Shape(
                        id=id,
                        natural_id=natural_id,
                        position=position,
                        points=points,
                        color=color,
                        clip=clip,
                    ))

                case "text":
                    (
                        content,
                        font,
                        color
                    ) = self._extract_text(
                        layer
                    )

                    elements.append(Text(
                        id=id,
                        natural_id=natural_id,
                        position=position,
                        content=content,
                        font=font,
                        color=color,
                    ))

                case "bitmap":
                    path = layer["image"]["_ref"]
                    path = os.path.join("tearsheet", path)

                    elements.append(Image(
                        id=id,
                        natural_id=natural_id,
                        position=position,
                        path=path,
                    ))

            clip: Rectangle2 = None
            for sub_layer in layer.get("layers", []):
                if sub_layer["hasClippingMask"]:
                    sub_size = self._get_frame_wh(sub_layer)
                    sub_local = self._get_frame_xy(sub_layer)

                    sub_absolute = sub_local + absolute

                    clip = Rectangle2(
                        sub_absolute.x, sub_absolute.y,
                        sub_size.x, sub_size.y,
                    )
                else:
                    find(sub_layer, absolute, clip)
                    clip = None

        pages: typing.List[Page] = []
        for layer in sketch["layers"]:
            layer["frame"]["x"] = 0
            layer["frame"]["y"] = 0

            elements = []
            find(layer, Vector2.zero(), None)

            pages.append(Page(
                size=self._get_frame_wh(layer),
                elements=elements
            ))

        document = Document(
            pages=pages
        )

        return Template(
            str(sketch["do_objectID"])[:50],
            document
        )

    def _get_frame_xy(self, layer: dict):
        return Vector2(
            layer["frame"]["x"],
            layer["frame"]["y"],
        )

    def _get_frame_wh(self, layer: dict):
        return Vector2(
            layer["frame"]["width"],
            layer["frame"]["height"],
        )

    def _extract_xy(self, input: str):
        input = input.replace("{", "")
        input = input.replace("}", "")

        return tuple(map(float, input.split(", ")))

    def _convert_color(self, input: dict) -> Color:
        return Color(
            input["red"] * 255,
            input["green"] * 255,
            input["blue"] * 255,
            input["alpha"] * 255
        )

    def _extract_shape_points(
        self,
        layer: dict,
        absolute: Vector2,
        size: Vector2
    ) -> Shape:
        fill = next(iter(layer["style"]["fills"]), None)
        color = self._convert_color(fill["color"]) if fill else Color.black()

        points: typing.List[Vector2] = []
        for point in layer["points"]:
            x, y = self._extract_xy(point["curveTo"])

            points.append(Vector2(
                absolute.x + x * size.x,
                absolute.y + y * size.y,
            ))

        return points, color

    def _extract_text(
        self,
        layer: dict,
    ) -> Shape:
        content = layer["attributedString"]["string"]
        content = content.replace("\uFB01", "fi")
        content = content.replace("\uFB02", "fl")
        content = content.replace("\t", " ")
        content = content.replace("\n", " ")
        content = content.replace("’", "'")

        font = Font(
            family=layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringFontAttribute"]["attributes"]["name"],
            size=layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringFontAttribute"]["attributes"]["size"]
        )

        color = Color(
            layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringColorAttribute"]["red"] * 255,
            layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringColorAttribute"]["green"] * 255,
            layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringColorAttribute"]["blue"] * 255,
            layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringColorAttribute"]["alpha"] * 255,
        )

        return content, font, color


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

        for font in template.document.fonts:
            file_name = f"{font.family}.ttf"
            if os.path.exists(file_name):
                if font.family.lower() not in pdf.fonts:
                    pdf.add_font(font.family, "", file_name)
            else:
                font.family = "helvetica"

        pdf.set_auto_page_break(False)

        for page in tqdm.tqdm(template.document.pages, desc="page"):
            pdf.add_page(
                format=(page.size.x, page.size.y),
            )

            elements = page.elements.copy()
            for index, element in enumerate(elements):
                element._index = index

            elements = sorted(elements, key=lambda x: (
                self.priorities[x.__class__.__name__.lower()], x._index))

            for element in tqdm.tqdm(elements, desc="element"):
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
            image.path,
            image.position.x, image.position.y,
            image.position.width, image.position.height
        )

    def _render_text(self, pdf: fpdf.FPDF, text: Text):
        font = text.font
        pdf.set_font(font.family, '', font.size)

        pdf.set_xy(pdf.x - 3, pdf.y + 1)
        pdf.set_text_color(text.color.red, text.color.green, text.color.blue)

        pdf.cell(
            text.position.width,
            text.position.height,
            text.content
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


print()
print()
print()
print()
print()

sketch = json.load(
    open("tearsheet/pages/38D296C9-D260-4EC7-9D17-B1D9738AF00D.json"))

loader = SketchTemplateLoader()
template = loader.load(sketch)

template.apply({
    "2023-06-13": datetime.date.today().isoformat(),
    "1.89": "Helloooo",
})

renderer = PdfTemplateRenderer(debug=True)
with open("output.pdf", "wb") as fd:
    renderer.render(template, fd)

os.system("cmd.exe /c output.pdf")
