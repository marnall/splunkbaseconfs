# Copyright (c) 2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import csv
import io
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from tabularreportgenerator_soar import get_custom_list


def load_image_dict(connector, image_list_name):
    image_list_str = get_custom_list(connector, image_list_name)
    list_reader = csv.reader(io.StringIO(image_list_str))
    image_dict = {rows[0]: rows[1] for rows in list_reader}
    return image_dict


def make_email(connector, report, report_html, from_email, to_email, subject, image_list_name=None) -> str:
    IMAGE_DICT = None

    msg_mixed = MIMEMultipart("mixed")
    html_part = MIMEText(report_html, "html")
    msg_mixed.attach(html_part)

    msg_mixed["From"] = from_email
    msg_mixed["To"] = to_email
    msg_mixed["Subject"] = subject

    for row in report.rows:
        if row.type == "image_row":
            if image_list_name is None:
                raise Exception("No image list was configured but an image block was passed in the report specification")

            if IMAGE_DICT is None:
                IMAGE_DICT = load_image_dict(connector, image_list_name)

            attachment_part = MIMEBase("image", "jpeg")
            image_name = row.cid
            image_contents = IMAGE_DICT.get(image_name)
            if image_contents is None:
                raise Exception("Image referenced in report specification was not found in the configured image list")

            attachment_part.set_payload(image_contents)
            attachment_part.add_header("Content-Transfer-Encoding", "base64")
            attachment_part["Content-Disposition"] = f'attachment; filename="{image_name}"'
            attachment_part.add_header("Content-ID", f"<{image_name}>")
            msg_mixed.attach(attachment_part)

    return msg_mixed.as_string()
