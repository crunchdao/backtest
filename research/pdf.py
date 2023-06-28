import random
import fpdf
import fpdf.drawing
import os
import typing
import dataclasses
import json
import tqdm

WHITE = 0xFFFFFF
BLACK = 0x000000
GRAY = 0xededed
RED = 0xff0000


Identifier = str | typing.Any

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
    def rbg(self) -> typing.Tuple[int, int, int]:
        return (self.red, self.green, self.blue)

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
    def font_families(self) -> typing.List[str]:
        return set(
            element.font.name
            for page in self.pages
            for element in page.elements
            if isinstance(element, Text)
        )


def load_sketch(sketch: dict):
    elements: typing.List[Element]

    def find(layer: dict, absolute_offset: Vector2, clip: Rectangle2):
        id = layer["do_objectID"]
        class_ = layer["_class"]

        size = Vector2(
            layer["frame"]["width"],
            layer["frame"]["height"]
        )

        local = Vector2(
            layer["frame"]["x"],
            layer["frame"]["y"],
        )

        absolute = local + absolute_offset

        position = Rectangle2(
            absolute.x, absolute.y,
            size.x, size.y,
        )

        if class_ == "shapePath":
            fill = next(iter(layer["style"]["fills"]), None)

            color = Color(
                fill["color"]["red"] * 255,
                fill["color"]["green"] * 255,
                fill["color"]["blue"] * 255,
                fill["color"]["alpha"] * 255
            ) if fill else Color.black()

            points: typing.List[Vector2] = []
            for point in layer["points"]:
                x, y = tuple(map(float, point["curveTo"].replace("{", "").replace("}", "").split(", ")))
                points.append(Vector2(
                    absolute.x + x * size.x,
                    absolute.y + y * size.y,
                ))
            
            elements.append(Shape(
                id=id,
                position=position,
                points=points,
                color=color,
                clip=clip,
            ))
            print(id, clip)

        if class_ == "text":
            content = layer["attributedString"]["string"]
            content = content.replace("\uFB01", "fi")
            content = content.replace("\uFB02", "fl")
            content = content.replace("\t", " ")
            content = content.replace("\n", " ")

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

            elements.append(Text(
                id=id,
                position=position,
                content=content,
                font=font,
                color=color,
            ))
        
        if class_ == "bitmap":
            path = layer["image"]["_ref"]
            path = os.path.join("tearsheet", path)

            elements.append(Image(
                id=id,
                position=position,
                path=path,
            ))

        clip: Rectangle2 = None
        for sub_layer in layer.get("layers", []):
            if sub_layer["hasClippingMask"]:
                sub_local = Vector2(
                    sub_layer["frame"]["x"],
                    sub_layer["frame"]["y"],
                )

                sub_absolute = sub_local + absolute

                clip = Rectangle2(
                    sub_absolute.x, sub_absolute.y,
                    sub_layer["frame"]["width"],
                    sub_layer["frame"]["height"],
                )
                print("new clip", sub_layer["do_objectID"], clip)
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
            size=Vector2(
                layer["frame"]["width"],
                layer["frame"]["height"],
            ),
            elements=elements
        ))

    document = Document(
        pages=pages
    )

    return document




def convert(
    document: Document,
    priorities: typing.Dict[str, int] = None,
    debug=False
):
    if priorities is None:
        priorities = {
            Text.__name__.lower(): 50,
            Shape.__name__.lower(): -20,
            Image.__name__.lower(): 10
        }

    pdf = fpdf.FPDF(
        unit="pt"
    )

    pdf.set_compression(False)
    pdf.set_text_color(255, 0, 0)
    pdf.set_fill_color(0, 255, 0)
    pdf.set_auto_page_break(False)
    pdf.add_font("LucidaGrande", '', "Lucida Grande Regular.ttf")
    pdf.add_font("LucidaGrande-Bold", '', "LucidaGrandeBold.ttf")

    for page in tqdm.tqdm(document.pages, desc="page"):
        pdf.add_page(
            format=(page.size.x, page.size.y),
        )

        elements = page.elements.copy()
        for index, element in enumerate(elements):
            element._index = index

        elements = sorted(elements, key=lambda x: (priorities[x.__class__.__name__.lower()], x._index))
        
        for element in tqdm.tqdm(elements, desc="element"):
            pdf.set_xy(element.position.x, element.position.y)

            if isinstance(element, Shape):
                shape = element

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

            if isinstance(element, Text):
                text = element

                font = text.font
                if font.family.lower() in pdf.fonts:
                    pdf.set_font(font.family, '', font.size)
                else:
                    pdf.set_font("Arial", '', font.size)
                    print("unknown", font.family)
                
                pdf.set_xy(pdf.x - 3, pdf.y + 1)
                pdf.set_text_color(text.color.rbg)
                pdf.cell(text.position.width, text.position.height, text.content)

            elif isinstance(element, Image):
                image = element

                pdf.image(
                    image.path,
                    image.position.x, image.position.y,
                    image.position.width, image.position.height
                )

        if debug:
            for element in elements:
                if isinstance(element, Text):
                    pdf.set_draw_color(255, 0, 0)
                elif isinstance(element, Image):
                    pdf.set_draw_color(0, 255, 0)
                elif isinstance(element, Shape):
                    pdf.set_draw_color(0, 0, 255)
                else:
                    continue

                pdf.rect(element.position.x, element.position.y, element.position.width, element.position.height)

    with open("output.pdf", "wb") as fd:
        pdf.output(fd)

print()
print()
print()
print()
print()

sketch = json.load(open("tearsheet/pages/38D296C9-D260-4EC7-9D17-B1D9738AF00D.json"))

document = load_sketch(sketch)
convert(document, debug=True)
os.system("cmd.exe /c output.pdf")
