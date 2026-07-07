Copyright Kauswagan.io 2022-2024

Splunk PDF integration. Offers functionality to create audit evidence as PDF as well as improved charts.

-

Included libraries etc license:
- CasperJS https://github.com/casperjs/casperjs and PhantomJS https://phantomjs.org/ to generate png from svg
- PyGal (https://github.com/Kozea/pygal) to generate SVG graphs 
- icons: <a href="https://www.flaticon.com/free-icons/pdf" title="pdf icons">Pdf icons created by Retinaicons - Flaticon</a>
- icons: <a href="https://www.flaticon.com/free-icons/pdf" title="pdf icons">Pdf icons created by surang - Flaticon</a>

---------------------------------------------------------------------------------

test email alert like this:
| sendalert sendspreadsheet_alert param.subject="test" param.recipient="curious.sle@gmail.com" param.sender="dominique@vocat.net" param.charttype="&chart=bar&subtype=stacked" param.sid="admin__admin__Spreadsheets__realsearch_1673631197.5729" param.title="Le Test"

# Binary File Declaration

lib/PIL/_imagingmath.cpython-37m-x86_64-linux-gnu.so: https://github.com/python-pillow/Pillow/blob/main/src/_imagingmath.c
lib/PIL/_webp.cpython-37m-x86_64-linux-gnu.so: https://github.com/python-pillow/Pillow/blob/main/src/_webp.c
lib/PIL/_imagingtk.cpython-37m-x86_64-linux-gnu.so: https://github.com/python-pillow/Pillow/blob/main/src/_imagingtk.c
lib/PIL/_imagingmorph.cpython-37m-x86_64-linux-gnu.so: https://github.com/python-pillow/Pillow/blob/main/src/_imagingmorph.c
lib/PIL/_imagingft.cpython-37m-x86_64-linux-gnu.so: https://github.com/python-pillow/Pillow/blob/main/src/_imagingft.c
lib/PIL/_imagingcms.cpython-37m-x86_64-linux-gnu.so: https://github.com/python-pillow/Pillow/blob/main/src/_imagingcms.c
lib/PIL/_imaging.cpython-37m-x86_64-linux-gnu.so: https://github.com/python-pillow/Pillow/blob/main/src/_imaging.c
lib/Pillow.libs/libwebp-e2184a5a.so.7.1.6: https://github.com/webmproject/libwebp
lib/Pillow.libs/libjpeg-2caf4b68.so.62.3.0: https://github.com/libjpeg-turbo/libjpeg-turbo
lib/Pillow.libs/libbrotlidec-97e69943.so.1.0.9: https://github.com/google/brotli
lib/Pillow.libs/libwebpmux-66cd43f5.so.3.0.11: https://github.com/webmproject/libwebp
lib/Pillow.libs/libsharpyuv-0ce1224c.so.0.0.0: https://github.com/webmproject/libwebp
lib/Pillow.libs/liblzma-72f7b2a5.so.5.4.2: https://github.com/xz-mirror/xz
lib/Pillow.libs/libtiff-ac0c3d92.so.6.0.0: https://gitlab.com/libtiff/libtiff
lib/Pillow.libs/libfreetype-e831c4c2.so.6.19.0: https://gitlab.freedesktop.org/freetype/freetype
lib/Pillow.libs/libharfbuzz-a3d224ae.so.0.60710.0: https://github.com/harfbuzz/harfbuzz
lib/Pillow.libs/libXau-00ec42fe.so.6.0.0: https://gitlab.freedesktop.org/xorg/lib/libxau
lib/Pillow.libs/libwebpdemux-8172cb3a.so.2.0.12: https://github.com/webmproject/libwebp
lib/Pillow.libs/libbrotlicommon-cf2297e4.so.1.0.9: https://github.com/google/brotli
lib/Pillow.libs/liblcms2-faac3155.so.2.0.15: https://github.com/mm2/Little-CMS
lib/Pillow.libs/libopenjp2-fca9bf24.so.2.5.0: https://github.com/uclouvain/openjpeg
lib/Pillow.libs/libxcb-421a6fdb.so.1.1.0: https://gitlab.freedesktop.org/xorg/lib/libxcb
lib/Pillow.libs/libpng16-021811b1.so.16.39.0: https://github.com/glennrp/libpng

For generating the pdf and embeding the image fpdf2 requires CasperJS and PhantomJS ( https://github.com/casperjs/casperjs | https://phantomjs.org/)
Sourcecode is availale at https://github.com/casperjs/casperjs | https://github.com/ariya/phantomjs. 