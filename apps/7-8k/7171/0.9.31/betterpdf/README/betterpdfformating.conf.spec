[settings]
#worksheet.autofilter(0, 0, max_row, max_col - 1) #https://xlsxwriter.readthedocs.io/example_pandas_autofilter.html
autofilter = <boolean>
#https://xlsxwriter.readthedocs.io/format.html
font = <ASCII string>
fontsize = <ASCII string>
fontcolor = <ASCII string>
text_wrap = <ASCII string>
border = <boolean>
header_format = <ASCII string>
* contains the format settings as json serialized to string
* example {"bold": 1, "text_wrap": 1, "valign": "top", "fg_color": "#D7E4BC", "border": 1}
#https://xlsxwriter.readthedocs.io/page_setup.html
header = 
footer = 
margins_top = <ASCII string>
margins_bottom = <ASCII string>
margins_left = <ASCII string>
margins_right = <ASCII string>
pageview = <ASCII string>
paper = <ASCII string>
uselogo = <boolean>
center_horizontally = <boolean>
center_vertically = <boolean>
orientation = <ASCII string>
*[portrait|landscape]
chart = <boolean>
charttype = <ASCII string> 
charttype_subtype = <ASCII string>
footer = <ASCII string>
font = <ASCII string>
fontsize = <integer>
borders_layout = <ASCII string>
style = <ASCII string>