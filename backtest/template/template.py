import io
import shutil
import re
import collections
import matplotlib.figure
import sys

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

        self.slots = collections.defaultdict(list)
        for page in document.pages:
            for element in page.elements:
                self.slots[element.id].append(element)
                self.slots[element.natural_id].append(element)
    
    def log(self, message: str):
        print(f"template: {message}", file=sys.stderr)

    def apply(self, variables: typing.Dict[NaturalIdentifier | Identifier, typing.Callable[[str], typing.Any] | typing.Any]):
        for key, value in variables.items():
            self.set(key, value)

    def apply_re(self, variables: typing.Dict[str, typing.Callable[[str], typing.Any] | typing.Any]):
        for pattern, value in variables.items():
            found = False

            for key, elements in self.slots.items():
                match = re.search(f"^{pattern}$", key)
                if match is None:
                    continue
    
                found = True

                if callable(value):
                    value = value(key, *match.groups())
                
                self._set(elements, value, key)
            
            if not found:
                self.log(f"no element for pattern={pattern}")

    def set(self, key: NaturalIdentifier | Identifier | re.Pattern, value: typing.Callable[[str], typing.Any] | typing.Any):
        elements = self.slots.get(key)
        if elements is None:
            self.log(f"no element for key={key}")
            return
    
        if callable(value):
            value = value(key)

        return self._set(elements, value, key)

    def _set(self, elements: typing.List[Element], value: typing.Any, original_key=None):
        self.log(f"apply len(elements)={len(elements)} key='{original_key}' value='{value}'")

        for element in elements:
            if isinstance(element, Text):
                text = element
                text.content = str(value)
            elif isinstance(element, Image):
                image = element

                if isinstance(value, io.BytesIO):
                    image.bytes = value
                elif isinstance(value, matplotlib.figure.Figure):
                    figure: matplotlib.figure.Figure  = value
                    figure.suptitle("")
                    figure.gca().set_ylabel("")
                    figure.gca().set_xlabel("")
                    figure.gca().set_title("")

                    bytes = io.BytesIO()
                    figure.savefig(bytes, bbox_inches="tight")
                    bytes.seek(0)

                    image.bytes = bytes
                elif isinstance(value, str):
                    bytes = io.BytesIO()
                    with open(value, "rb") as fd:
                        shutil.copyfileobj(fd, bytes)

                    image.bytes = bytes
                else:
                    raise ValueError(f"unsupported for image: {type(value)} {value}")


class TemplateLoader:

    def load(path: str) -> Template:
        raise NotImplemented()


class TemplateRenderer:

    def render(self, template: Template, output: io.FileIO) -> Template:
        raise NotImplemented()
