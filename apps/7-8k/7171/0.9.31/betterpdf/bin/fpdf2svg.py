import os,sys
#load own libs from ../lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from fpdf import FPDF
from fpdf.template import FlexTemplate

import os
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

def create_chartpdf():
    from fpdf import FPDF

    class TestFPDF(FPDF):
        def header(self):
            #pdf.image('splunk_logo_smaller.png', 10, 8, 69)
            # Set the font and size
            pdf.set_font('Arial', 'B', 12)
            # Add the header text
            pdf.cell(0, 10, 'Report generated using betterPDF', 0, 0, 'C')
            # Add a line break
            pdf.ln(20)

        def footer(self):
            self.set_y(-15)
            self.set_font("helvetica", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}} - Trial version, please check out kauswagan.io for more", align="C")
            
            # -- watermark
            cell_width = 80
            cell_height = 80
            # Calculate the x and y positions to center the cell
            x = (pdf.w - cell_width) / 2
            y = (pdf.h - cell_height) / 2
            # Set the position and write the cell
            pdf.set_xy(x, y)

            # Set the font and size for the watermark
            pdf.set_font('Arial', 'B', 50)
            # Set the opacity for the watermark
            pdf.set_text_color(128, 128, 128)
            #pdf.set_alpha(0.5)
            # Rotate the coordinate system
            pdf.rotate(45, self.w / 2, self.h / 2)
            # Write the watermark text
            pdf.cell(0, 0, 'trial version', align='C', fill=True)
            # Reset the coordinate system and opacity
            pdf.rotate(0)
            #pdf.set_alpha(1.0)

    elements = [
        {"name":"company_logo", "type":"I", "x1":0, "y1":0, "x2":150, "y2":50,},
        {'name': 'company_name', 'type': 'T', 'x1': -17.0, 'y1': -32.5, 'x2': 115.0, 'y2': 37.5, 'font': 'helvetica', 'size': 12.0, 'bold': 1, 'italic': 0, 'underline': 0,'align': 'C', 'text': '', 'priority': 2, 'multiline': False},
    ]
    pdf = TestFPDF()
    from io import BytesIO
    img_bytesio = BytesIO()
    import cairosvg
    cairosvg.svg2png("tmpchart.svg", write_to=img_bytesio, dpi=96)

    pdf.add_page() #coverpage

    pdf.image(img_bytesio, w=100)
    pdf.output("fpdf2svg.pdf")

create_chartpdf()
