import dataclasses
import io
import typing

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

    bytes: io.BytesIO


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
