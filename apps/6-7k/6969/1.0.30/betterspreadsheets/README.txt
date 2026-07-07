Copyright Kauswagan.io 2022

Splunk Spreadsheet integration. Offers functionality to integrate into business facing standard tools.

-

Included libraries etc license:

- XLSXWriter (https://xlsxwriter.readthedocs.io/license.html):
XlsxWriter is released under a BSD 2-Clause license.

BSD 2-Clause License

Copyright (c) 2013-2022, John McNamara <jmcnamara@cpan.org> All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

- icons: https://justfuji.com/project/free-microsoft-office-365-icons

---------------------------------------------------------------------------------

test email alert like this:
| sendalert sendspreadsheet_alert param.subject="test" param.recipient="curious.sle@gmail.com" param.sender="dominique@vocat.net" param.charttype="&chart=bar&subtype=stacked" param.sid="admin__admin__Spreadsheets__realsearch_1673631197.5729" param.title="Le Test"