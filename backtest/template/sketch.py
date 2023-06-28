import zipfile
import shutil
import json

from .models import *
from .template import *


class SketchTemplateLoader(TemplateLoader):

    def _load(self, zipfd: zipfile.ZipFile, sketch: dict):
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

                    bytes = io.BytesIO()
                    with zipfd.open(path) as fd:
                        shutil.copyfileobj(fd, bytes)

                    elements.append(Image(
                        id=id,
                        natural_id=natural_id,
                        position=position,
                        bytes=bytes,
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

        return pages

    def load(self, path: str) -> Template:
        with zipfile.ZipFile(path) as zipfd:
            with zipfd.open('document.json') as fd:
                document_meta = json.load(fd)

            sketchs: typing.List[dict] = []
            for item in document_meta["pages"]:
                ref = item["_ref"]
                with zipfd.open(f"{ref}.json") as fd:
                    sketchs.append(json.load(fd))

            pages: typing.List[Page] = []
            for sketch in sketchs:
                pages.extend(self._load(zipfd, sketch))

            document = Document(
                pages=pages
            )

            return Template(
                path,
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
        content = content.replace("\u2019", "'")

        font = Font(
            family=layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringFontAttribute"]["attributes"]["name"],
            size=layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringFontAttribute"]["attributes"]["size"]
        )

        color = self._convert_color(
            layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringColorAttribute"]
        )

        return content, font, color
