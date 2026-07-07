import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from fpdf import FPDF

class MyPDF(FPDF):
    def header(self):
        # Custom header method
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'My Custom Header', 0, 1, 'C')

    def footer(self):
        # Custom footer method
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def set_page_layout(self, orientation='P', unit='mm', format='A4'):
        # Method to set page layout
        self.add_page(orientation=orientation, format=format)

    def add_html_table(self, html):
        # Method to add an HTML table
        self.write_html(html)

    def add_centered_png(self, png_path, x=None, y=None, w=0, h=0):
        # Method to add a PNG image centered on the page
        self.image(png_path, x=x, y=y, w=w, h=h)
        img_width = w if w else 10  # Default width if not specified, adjust as needed
        if not x:
            x = (self.w - img_width) / 2  # Center the image
        if not y:
            self.ln(10)  # Add a line break if y not specified, adjust as needed
        self.image(png_path, x, y, w, h)

# Create an instance of the extended class
pdf = MyPDF()

# Set the page layout
pdf.set_page_layout()

# Adding a header, footer, and page layout is handled automatically by the class methods

# Example HTML table (simplified for demonstration; FPDF's HTML support is basic)
html = """
<b>HTML Table</b><br>
<table border="1" align="center">
<tr><th width="40%">Header 1</th><th width="60%">Header 2</th></tr>
<tr><td>Cell 1</td><td>Cell 2</td></tr>
</table>
"""

# Add an HTML table to the document
pdf.add_page()
pdf.add_html_table(html)

# Add a PNG image centered on a new page
pdf.add_page()
pdf.add_centered_png('./etc/apps/betterpdf/bin/splunk_logo_smaller.png', w=100)  # Adjust path and dimensions as needed

# Save the PDF to a file
pdf.output('./etc/apps/betterpdf/bin/mypdf.pdf')