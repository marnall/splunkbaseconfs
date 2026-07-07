import os,sys,subprocess
#load own libs from ../lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from fpdf import FPDF
try:
    import cairosvg
except:
    print("cairo not available")
    exit(1) #pass

def convert_svg_to_ps(input_svg, output_ps):
    # Convert SVG to PostScript
    cairosvg.svg2ps(url=input_svg, write_to=output_ps, output_width=2400, output_height=1400)

def add_ps_to_pdf(pdf, ps_file, x, y, width, height):
    # Add the PS file to the PDF at the specified position and size
    pdf.image(ps_file, x=x, y=y, w=width, h=height)

import xml.etree.ElementTree as ET

from xml.etree import ElementTree as etree

def add_margins_to_svg(input_svg, output_svg, top_margin_percentage=25, right_margin_percentage=25):
    # Parse the SVG file
    tree = ET.parse(input_svg)
    root = tree.getroot()

    # Get the height and width of the existing SVG content
    svg_height = float(root.attrib.get('height', '0').replace('px', ''))
    svg_width = float(root.attrib.get('width', '0').replace('px', ''))

    # Calculate the top and right margins
    top_margin = (top_margin_percentage / 100) * svg_height
    right_margin = (right_margin_percentage / 100) * svg_width

    # Create a new 'rect' element for the top margin
    top_margin_rect = ET.Element('rect')
    top_margin_rect.attrib['width'] = '100%'
    top_margin_rect.attrib['height'] = str(top_margin)
    top_margin_rect.attrib['fill'] = 'none'

    # Insert the top margin element at the beginning of the SVG
    root.insert(0, top_margin_rect)

    # Create a new 'rect' element for the right margin
    right_margin_rect = ET.Element('rect')
    right_margin_rect.attrib['width'] = str(right_margin)
    right_margin_rect.attrib['height'] = '100%'
    right_margin_rect.attrib['fill'] = 'none'

    # Insert the right margin element at the end of the SVG
    root.append(right_margin_rect)

    # Save the modified SVG content to a new file
    tree.write(output_svg)

# Example usage:
input_svg_file = '/opt/splunk/etc/apps/betterpdf/bin/tmpchart.svg'
output_svg_file = '/opt/splunk/etc/apps/betterpdf/bin/tmpchart2.svg'
output_ps_file = '/opt/splunk/etc/apps/betterpdf/bin/output.ps'
output_pdf_file = '/opt/splunk/etc/apps/betterpdf/bin/output.pdf'

#add whitespace on top to hack the odd .ps placement behaviour of fpdf2
add_margins_to_svg(input_svg_file, output_svg_file, top_margin_percentage=25, right_margin_percentage=25)

# Convert SVG to PS
convert_svg_to_ps(output_svg_file, output_ps_file)

# Create PDF
pdf = FPDF()
pdf.add_page()
page_width = pdf.w - 2 * pdf.l_margin
page_height = pdf.h - 2 * pdf.t_margin

# Add PS chart to PDF
x_position = 10  # Adjust as needed
y_position = 10  # Adjust as needed
chart_width = 1000  # Adjust as needed
chart_height = 1000  # Adjust as needed
#add_ps_to_pdf(pdf, output_ps_file, x_position, y_position, page_width, page_height)
pdf.image(output_ps_file, w=page_width)
pdf.image('/opt/splunk/etc/apps/betterpdf/bin/tmpchart.png', w=page_width)
pdf.image('/opt/splunk/etc/apps/betterpdf/bin/test2.svg', w=page_width)

# Output the PDF
pdf.output(output_pdf_file)