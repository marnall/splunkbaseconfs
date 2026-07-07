# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

import base64
import io
import os
import textwrap
from html import escape
from itertools import groupby
from zipfile import ZipFile

try:
    import http.client as httplib
except ImportError:
    import httplib

import commonmark
from lxml import html

from logging_utils import log
from ite_models.ite_model_maturity_stage import IteMaturityStage
from ite_models.ite_model_use_case import IteUseCase
from ite_models.ite_model_use_case_family import IteUseCaseFamily
from rest_handler.exception import BaseRestException

logger = log.getLogger()
is_linux_platform = True

try:
    from xhtml2pdf import pisa
except Exception as ie:
    logger.error('Unable to import pisa from xhtml2pdf: %s' % ie)
    logger.info('xhtml2pdf unavailable (possibly incompatible Python version), using fallback export.')
    is_linux_platform = False
    import subprocess
    import tempfile


class IteProcedureExporter:
    template_path = os.path.join(os.path.dirname(__file__), 'export_template', 'template.html')
    wrapper_path = os.path.join(os.path.dirname(__file__), 'export_template', 'wrapper.docx')

    @staticmethod
    def extract_node(tree, xpath):
        """
        Extracts a node in a HTML tree identified by the xpath
        """
        node = tree.xpath(xpath)[0]
        return html.tostring(node).decode("utf-8")

    @staticmethod
    def read_file(filename):
        with open(filename, mode='r') as f:
            return f.read()

    @staticmethod
    def generate_docx(content_html):
        """
        This method reads the template docx file (docx are basically zip files)
        and re-creates a new docx file in memory; the passed in HTML string is
        added to the empty content.html. Microsoft Word will process this HTML
        and populate the document when it is opened
        """
        byte_buffer = io.BytesIO()
        with ZipFile(IteProcedureExporter.wrapper_path, mode='r') as docx:
            with ZipFile(byte_buffer, mode='w') as new_docx:
                for info in docx.infolist():
                    if info.filename.endswith('content.html'):
                        new_docx.writestr(info, content_html)
                    else:
                        new_docx.writestr(info, docx.read(info.filename))

        return byte_buffer.getvalue()

    @staticmethod
    def format_spl(spl):
        """
        Chops SPL string to multiple lines if it exceeds certain number of chars
        and escapes HTML tags
        """
        wrapped_spl = []
        for line in spl.split("\n"):
            wrapped_spl.extend(textwrap.wrap(line,
                                             width=80,
                                             replace_whitespace=False,
                                             break_on_hyphens=False,
                                             drop_whitespace=False))

        return escape('\n'.join(wrapped_spl))

    @staticmethod
    def markdown_to_html(markdown):
        """
        Converts markdown formatted data into HTML
        """
        return commonmark.commonmark(markdown)

    def __init__(self, export_type='docx'):
        self.type = export_type
        self.use_case_family_lookup = {}
        self.use_case_lookup = {}
        self.maturity_stage_lookup = {}
        self.template = html.fromstring(IteProcedureExporter.read_file(IteProcedureExporter.template_path))
        self.ucf_template = IteProcedureExporter.extract_node(self.template, '//*[@class="ucf_template"]')
        self.procedure_template = IteProcedureExporter.extract_node(self.template, '//*[@class="proc_template"]')

    def _load_lookups(self, procedures):
        """
        During an export, the titles of use case family, use case, maturity stages
        are required by the template. This method loads all such objects associated
        with a procedure and stores them into lookup map as instance variables.
        If any reference is found invalid, we skip processing
        that procedure and returns the list of procedures that has valid relationships.
        This prevents a corrupted procedure from blocking a bulk export
        """
        filtered_procedures = []
        for procedure in procedures:
            try:
                uc_id = procedure['use_case_id']
                if uc_id not in self.use_case_lookup:
                    self.use_case_lookup[uc_id] = IteUseCase.get(uc_id)
                    ucf_id = self.use_case_lookup[uc_id].use_case_family_id
                    if ucf_id not in self.use_case_family_lookup:
                        self.use_case_family_lookup[ucf_id] = IteUseCaseFamily.get(ucf_id)
                ms_id = procedure['maturity_stage_id']
                if ms_id not in self.maturity_stage_lookup:
                    self.maturity_stage_lookup[ms_id] = IteMaturityStage.get(ms_id)
                filtered_procedures.append(procedure)
            except (BaseRestException, AttributeError, KeyError) as e:
                logger.error('Encountered unexpected exception in _load_lookups() during export: %s' % e)

        return filtered_procedures

    def _get_use_case_family_html(self, title, is_first):
        """
        Fill in the Use case family HTML template with actual values
        """
        # All except first use case family should have a page break before
        if is_first:
            ucf_tag = '<h2>%s</h2>' % title
        else:
            ucf_tag = '<h2 style="page-break-before: always;">%s</h2>' % title
        return self.ucf_template.format(token_use_case_family=ucf_tag)

    def _get_procedure_html(self, procedure):
        """
        Fill in the Procedure HTML template with actual values
        """
        # generate hyperlinks for datasource

        datasource_links = [
            '<a href="{link}">{text}</a>'.format(link=escape(ds['reference_url']), text=ds['title'])
            for ds in procedure['data_sources']]

        # some inline style required to reduce the space between section title and body
        formatted_how_to_implement = IteProcedureExporter.markdown_to_html(
            '**How to Implement:** ' + procedure['content']['how_to_implement'])

        formatted_spl_description = IteProcedureExporter.markdown_to_html(
            '**SPL:** ' + procedure['content']['data_playground']['spl_description'])

        # wrap long spl string
        formatted_spl = IteProcedureExporter.format_spl(procedure['content']['data_playground']['live_data_search'])

        return self.procedure_template.format(token_procedure_name=procedure['title'],
                                              token_description=IteProcedureExporter.markdown_to_html(
                                                  procedure['content']['description']),
                                              token_use_case=self.use_case_lookup[procedure['use_case_id']].title,
                                              token_maturity_stage=self.maturity_stage_lookup[
                                                  procedure['maturity_stage_id']].title,
                                              token_live_spl=formatted_spl,
                                              token_data_sources=', '.join(datasource_links),
                                              token_how_to_implement=formatted_how_to_implement,
                                              token_spl_description=formatted_spl_description)

    def _build_html(self, procedures):
        """
        Generates HTML containing the procedure data. This HTML can be
        exported as docx by embedding within a template docx file
        or as PDF by passing it to xhtml2pdf library
        """
        # first load all lookups and filter out procedures that does not has a valid references to other objects
        procedures = self._load_lookups(procedures)

        # sort procedures by use case family, use case and procedure titles
        procedures.sort(key=lambda proc: (
            self.use_case_family_lookup[self.use_case_lookup[proc['use_case_id']].use_case_family_id].title,
            self.use_case_lookup[proc['use_case_id']].title,
            proc['title']))

        generated_html = '<div>'
        is_first_ucf = True
        for ucf, p_group in groupby(procedures,
                                    lambda proc:
                                    self.use_case_family_lookup[
                                        self.use_case_lookup[proc['use_case_id']].use_case_family_id].title):

            ucf_html = self._get_use_case_family_html(ucf, is_first_ucf)
            if is_first_ucf:
                is_first_ucf = False

            procedure_html = ''
            for procedure in list(p_group):
                procedure_html += self._get_procedure_html(procedure)
            generated_html += ucf_html + procedure_html
        generated_html += '</div>'

        # clear the div in the original template (identified by id 'template_root')
        # and add the generated HTML under it
        template_root = self.template.xpath('//*[@id="template_root"]')[0]
        template_root.clear()
        template_root.extend(html.fromstring(generated_html).getchildren())
        html_string = html.tostring(self.template)
        return html_string

    @staticmethod
    def generate_pdf(html_string):
        try:
            logger.info('Creating a temporary HTML file for PDF conversion.')

            # Create temporary output directory
            temp_dir = tempfile.TemporaryDirectory()
            output_dir = temp_dir.name
            logger.info('Created temporary directory to store the PDF file: %s' % output_dir)

            # Create a temporary file to hold the HTML content
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='wb', dir=output_dir) as temp_html_file:
                temp_html_file.write(html_string)
                temp_html_file_path = temp_html_file.name
            logger.info('Successfully created temporary HTML file: %s' % temp_html_file_path)

            # Command to convert HTML to PDF using LibreOffice
            command = [
                'soffice',
                '--headless',
                '--invisible',
                '--convert-to', 'pdf',
                '--outdir', output_dir,
                temp_html_file_path
            ]

            # Execute the command
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            logger.info('Successfully executed soffice command to convert HTML file to PDF: %s' % result)
            pdf_file_path = temp_html_file_path.replace('.html', '.pdf')

            with open(pdf_file_path, mode='rb') as temp_pdf_file:
                byte_buffer = io.BytesIO(temp_pdf_file.read())
                output_bytes = byte_buffer.getvalue()

            return output_bytes

        except Exception as e:
            logger.error('An unexpected error occurred while converting HTML to PDF file: %s' % e)

        finally:
            # Clean up the temporary directory
            temp_dir.cleanup()
            logger.info('Successfully removed the temporary file.')

    def export(self, procedures):
        """
        This handles export of both bulk and individual procedures.
        We first generate an HTML file using the static html template (see export_template/template.html).
        The placeholders in that template file are filled with
        actual values from procedures and associated objects in the lookups.
        This HTML file is then passed to either docx or PDF generation methods.
        These methods generates the final bits in memory and are
        returned from here in base64 encoded format.

        Parameters:
           procedures: list of procedures to export

        Returns tuple consisting of:
           Base64 encoded binary data
           Custom HTTP headers
        """

        html_content = self._build_html(procedures)

        if self.type == 'docx':
            content_type = 'application/msword'
            output_bytes = IteProcedureExporter.generate_docx(html_content)
        elif self.type == 'pdf':
            content_type = 'application/pdf'
            if is_linux_platform:
                byte_buffer = io.BytesIO()
                pisa.CreatePDF(html_content, dest=byte_buffer)
                output_bytes = byte_buffer.getvalue()
            else:
                output_bytes = IteProcedureExporter.generate_pdf(html_content)
        else:
            raise BaseRestException(httplib.BAD_REQUEST, 'Please specify filetype param as either docx or pdf')

        headers = [
            ['Content-Type', content_type],
            ['Content-Disposition', 'attachment; filename=Splunk_ITEssentials_Learn_Procedures.%s' % self.type]
        ]
        return base64.b64encode(output_bytes).decode("ascii"), headers
