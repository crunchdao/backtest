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
            if class_ == "shapePath":
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

            elif class_ == "text":
                (
                    content,
                    font,
                    color,
                    alignment,
                    spans,
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
                    alignment=alignment,
                    spans=spans
                ))

            elif class_ == "bitmap":
                path = layer["image"]["_ref"]

                bytes = io.BytesIO()
                with zipfd.open(path) as fd:
                    shutil.copyfileobj(fd, bytes)

                elements.append(Image(
                    id=id,
                    natural_id=natural_id,
                    position=position,
                    bytes=bytes,
                    alternative=natural_id
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
        for layer in reversed(sketch["layers"]):
            layer["frame"]["x"] = 0
            layer["frame"]["y"] = 0

            elements = []
            find(layer, Vector2.zero(), None)
           
            if len(elements) > 1:
                pages.append(Page(
                    size=self._get_frame_wh(layer),
                    elements=elements
                ))

        return pages

    def load(self, path: str) -> Template:
        with zipfile.ZipFile(path) as zipfd:
            def open_or_none(file_path: str):
                try:
                    return zipfd.open(file_path)
                except KeyError as error:
                    return None

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

            loaded_fonts = dict()
            for font in document.fonts:
                file_name = font.file_name

                current = loaded_fonts.get(file_name)
                if current == False:
                    continue
                elif isinstance(current, bytes):
                    font.bytes = current
                    continue

                fd = open_or_none(file_name) or open_or_none(f"fonts/{file_name}")
                if fd:
                    with fd:
                        current = fd.read()
                        font.bytes = current
                        loaded_fonts[file_name] = current
                else:
                    loaded_fonts[file_name] = False

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

    REPLACE_TABLE = {
        "\uFB01": "fi",
        "\uFB02": "fl",
        "\u2019": "'",
        "\t": " ",
    }

    def _sanitize(self, input: str):
        if input is None:
            return None
        
        added = 0
        output = ""

        for character in input:
            replacement = self.REPLACE_TABLE.get(character)

            if replacement is None:
                output += character
                continue

            length = len(replacement)
            if length > 1:
                added += length - 1
            
            output += replacement
        
        return output, added

    def _extract_text(
        self,
        layer: dict,
    ):
        raw_string = layer["attributedString"]["string"]
        content, _ = self._sanitize(raw_string)

        font = Font(
            family=layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringFontAttribute"]["attributes"]["name"],
            size=layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringFontAttribute"]["attributes"]["size"],
        )

        color = self._convert_color(
            layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringColorAttribute"]
        )

        alignment = Alignment.LEFT
        if layer["style"]["textStyle"]["encodedAttributes"].get("paragraphStyle", {}).get("alignment", None) == 1:
            alignment = Alignment.RIGHT

        spans = self._extract_spans(layer, raw_string)

        content_length = len(content)
        span_length_sum = sum(span.length for span in spans)
        if content_length != span_length_sum:
            raise ValueError(f"spans are not same length as content: {content_length} != {span_length_sum}")

        return content, font, color, alignment, spans

    def _extract_span(
        self,
        attributes_item: dict,
        text_string: str,
    ) -> Span:
        location = attributes_item["location"]
        length = attributes_item["length"]

        raw_string = text_string[location:location + length]
        content, added = self._sanitize(raw_string)

        font = Font(
            family=attributes_item["attributes"]["MSAttributedStringFontAttribute"]["attributes"]["name"],
            size=attributes_item["attributes"]["MSAttributedStringFontAttribute"]["attributes"]["size"],
        )

        color = self._convert_color(
            attributes_item["attributes"]["MSAttributedStringColorAttribute"]
        )

        return Span(
            start=location,
            length=length + added,
            content=content,
            font=font,
            color=color,
        )

    def _extract_spans(
        self,
        layer: dict,
        text_string: str,
    ):
        attributes = layer["attributedString"]["attributes"]

        return [
            self._extract_span(item, text_string)
            for item in attributes
        ]
