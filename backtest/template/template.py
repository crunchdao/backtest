import io
import shutil

from .models import *


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
        elements = self.slots.get(key)
        if elements is None:
            print(f"no element for key={key}")
            return

        for element in elements:
            if isinstance(element, Text):
                text = element
                text.content = str(value)
            elif isinstance(element, Image):
                image = element

                if isinstance(value, io.BytesIO):
                    image.bytes = bytes
                elif isinstance(value, str):
                    bytes = io.BytesIO()
                    with open(value) as fd:
                        shutil.copyfileobj(fd, bytes)

                    image.bytes = bytes
                else:
                    raise ValueError(f"unsupported for image: {value}")


class TemplateLoader:

    def load(path: str) -> Template:
        raise NotImplemented()


class TemplateRenderer:

    def render(self, template: Template, output: io.FileIO) -> Template:
        raise NotImplemented()
