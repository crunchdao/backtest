import random
import fpdf
import fpdf.drawing
import os
import typing
import dataclasses
import json
# import logging

# logging.basicConfig(format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
#                     datefmt="%H:%M:%S", level=logging.DEBUG)
WHITE = 0xFFFFFF
BLACK = 0x000000
GRAY = 0xededed
RED = 0xff0000


print()
print()
print()
print()
print()

document = json.load(open("tearsheet/pages/38D296C9-D260-4EC7-9D17-B1D9738AF00D.json"))
root = document["layers"][0]
root["frame"]["x"] = 0
root["frame"]["y"] = 0
print("loaded")

pdf = fpdf.FPDF(
    format=(
        root["frame"]["width"],
        root["frame"]["height"],
    ),
    unit="pt"
)
pdf.set_compression(False)
pdf.set_text_color(255, 0, 0)
pdf.set_fill_color(0, 255, 0)
pdf.set_auto_page_break(False)
pdf.add_font("LucidaGrande", '', "Lucida Grande Regular.ttf")
pdf.add_font("LucidaGrande-Bold", '', "LucidaGrandeBold.ttf")
pdf.add_page()

debug_rectangles = []

def draw(layer: dict, start_x: int, start_y: int, clipping_path: fpdf.drawing.ClippingPath):
    x = start_x + max(0, layer["frame"]["x"])
    y = start_y + max(0, layer["frame"]["y"])
    width = layer["frame"]["width"]
    height = layer["frame"]["height"]
    object_id = layer["do_objectID"]
    class_ = layer["_class"]

    pdf.set_xy(x, y)

    debug_rectangles.append((x, y, width, height, class_, object_id))
    if class_ == "shapePath":
        fill = next(iter(layer["style"]["fills"]), None)
        print(layer["do_objectID"], clipping_path, layer["hasClippingMask"])

        color = '#%02x%02x%02x' % (
            int(fill["color"]["red"] * 255),
            int(fill["color"]["green"] * 255),
            int(fill["color"]["blue"] * 255)
        ) if fill else "#000000"

        with pdf.new_path(x, y) as path:
            path.style.fill_color = color
            # if clipping_path:
            #     path.style.stroke_color = fpdf.drawing.gray8(210)
            # else:
            #     path.style.stroke_color = fpdf.drawing.gray8(10)
            
            path.style.stroke_color = fpdf.drawing.gray8(0, 0)
            path.style.stroke_width = 0
            path.style.stroke_opacity = 0
            # path.style.stroke_join_style = "round"

            if clipping_path:
                path.clipping_path = clipping_path

            for point in layer["points"]:
                x_, y_ = tuple(map(float, point["curveTo"].replace("{", "").replace("}", "").split(", ")))
                path.line_to(
                    x + x_ * width,
                    y + y_ * height
                )
            
            path.close()

    elif class_ == "text":
        content = layer["attributedString"]["string"]
        content = content.replace("\uFB01", "fi")
        content = content.replace("\uFB02", "fl")
        content = content.replace("\t", " ")
        content = content.replace("\n", " ")

        pdf.set_font("Arial", '', 8)
        font_family = layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringFontAttribute"]["attributes"]["name"]
        font_size = layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringFontAttribute"]["attributes"]["size"]

        pdf.set_text_color(
            layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringColorAttribute"]["red"] * 255,
            layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringColorAttribute"]["green"] * 255,
            layer["style"]["textStyle"]["encodedAttributes"]["MSAttributedStringColorAttribute"]["blue"] * 255
        )
        
        if font_family.lower() in pdf.fonts:
            pdf.set_font(font_family, '', font_size)
        else:
            print("unknown", font_family)
        
        pdf.set_xy(pdf.x - 3, pdf.y + 1)
        pdf.cell(width, height, content)
    
    elif class_ == "bitmap":
        path = layer["image"]["_ref"]

        pdf.image(
            os.path.join("tearsheet", path),
            x, y, width, height
        )

    clipping_path = None
    for sublayer in layer.get("layers", []):
        if sublayer["hasClippingMask"]:
            clipping_path = fpdf.drawing.ClippingPath()
            clipping_path.rectangle(x, y, width, height)
        else:
            draw(sublayer, x, y, clipping_path)
            clipping_path = None


draw(root, 0, 0, None)

# for x, y, width, height, class_, object_id in debug_rectangles:
#     pdf.set_draw_color(255, 0, 0)
#     pdf.rect(x, y, width, height)
    # pdf.set_xy(x, y)
    # pdf.cell(0, 0, f"{class_}: {object_id}")

with open("output.pdf", "wb") as fd:
    buffer = pdf.output(fd)
os.system("cmd.exe /c output.pdf")
