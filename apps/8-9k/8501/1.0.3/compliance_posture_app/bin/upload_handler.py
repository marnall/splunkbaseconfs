#!/usr/bin/env python3
"""
Compliance Posture for Splunk - ARF Upload Handler
Custom REST endpoint for uploading CIS-CAT Pro ARF XML files through the web UI.

This endpoint receives ARF XML files via POST, parses them using parse_arf.py,
enriches events with framework_mapper.py, and ingests the resulting JSON into
the index defined in the ciscat_base macro.

INDEX CONFIGURATION:
    The target index is read automatically from the ciscat_base macro definition.
    To change the index, update the macro via Splunk Web:
        Settings > Advanced Search > Search Macros > ciscat_base
    No code changes required.

Supported formats:
    .xml - CIS-CAT Pro v4 ARF XML (Asset Reporting Format)
"""

import os
import sys
import json
import time
import logging
import tempfile
import splunk.admin as admin
import splunk.rest as rest
import splunk.entity as entity

logger = logging.getLogger("splunk.app.compliance_posture")


# Add bin directory to path for parse_arf / framework_mapper import
bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin')
if bin_dir not in sys.path:
    sys.path.insert(0, bin_dir)


class ARFUploadHandler(admin.MConfigHandler):
    """REST handler for CIS-CAT ARF XML file uploads."""

    def _get_index_from_macro(self):
        """Read the target index from the ciscat_base macro definition.
        Falls back to 'main' if macro cannot be read."""
        try:
            import re
            macro_entity = entity.getEntity(
                'admin/macros', 'ciscat_base',
                namespace='compliance_posture_app',
                owner='nobody',
                sessionKey=self.getSessionKey()
            )
            definition = macro_entity.get('definition', 'index=main sourcetype="ciscat:arf"')
            match = re.search(r'index=(\S+)', definition)
            if match:
                return match.group(1)
        except Exception:
            pass
        return 'main'

    def setup(self):
        self.supportedArgs.addOptArg('arf_data')
        self.supportedArgs.addOptArg('filename')

    def handleCreate(self, confInfo):
        """Handle POST request with ARF XML file data."""
        try:
            arf_data = self.callerArgs.data.get('arf_data', [None])[0]
            filename  = self.callerArgs.data.get('filename', ['upload.xml'])[0]

            if not arf_data:
                logger.warning("Upload rejected: no ARF data provided")
                confInfo['result'].append('status', 'error')
                confInfo['result'].append('message', 'No ARF data provided')
                return

            # Validate file extension
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext != '.xml':
                logger.warning("Upload rejected: invalid file type '%s' from file '%s'", file_ext, filename)
                confInfo['result'].append('status', 'error')
                confInfo['result'].append('message', 'Invalid file type. Expected CIS-CAT Pro ARF XML (.xml), got: %s' % file_ext)
                return

            # Write to temp file for parser
            tmp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8')
            tmp_file.write(arf_data)
            tmp_file.close()

            # Layer 1: Parse ARF XML -> normalized events
            from parse_arf import parse_arf_file
            upload_time     = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())
            upload_batch_id = 'ciscat_%s_%s' % (int(time.time()), os.path.basename(filename).replace(' ', '_'))

            events = parse_arf_file(
                tmp_file.name,
                upload_time=upload_time,
                upload_batch_id=upload_batch_id
            )

            # Layer 2: Enrich with framework mapper
            from framework_mapper import FrameworkMapper
            mapper = FrameworkMapper(framework_id='cis_benchmarks')
            events = mapper.enrich(events)

            # Clean up temp file
            os.unlink(tmp_file.name)

            if not events:
                logger.warning("Upload produced no events from file '%s'", filename)
                confInfo['result'].append('status', 'error')
                confInfo['result'].append('message', 'No events parsed from ARF file. Verify the file is a valid CIS-CAT Pro ARF XML output.')
                return

            # Serialize events as newline-delimited JSON
            json_data = '\n'.join(json.dumps(event) for event in events)

            # Ingest via receivers/simple REST endpoint
            try:
                import urllib.parse
                import http.client
                import ssl

                target_index = self._get_index_from_macro()

                params = urllib.parse.urlencode({
                    'index':      target_index,
                    'sourcetype': 'ciscat:arf',
                    'source':     'ciscat_upload:%s' % filename
                })

                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                conn = http.client.HTTPSConnection('127.0.0.1', 8089, context=ctx)
                headers = {
                    'Authorization': 'Splunk %s' % self.getSessionKey(),
                    'Content-Type': 'text/plain'
                }

                conn.request('POST', '/services/receivers/simple?%s' % params,
                             body=json_data.encode('utf-8'), headers=headers)
                resp      = conn.getresponse()
                resp_body = resp.read().decode('utf-8')
                conn.close()

                if resp.status not in (200, 201):
                    logger.error("Ingestion failed for '%s': HTTP %d", filename, resp.status)
                    confInfo['result'].append('status', 'error')
                    confInfo['result'].append('message', 'Ingestion failed with status %d: %s' % (resp.status, resp_body[:200]))
                    return

            except Exception as e:
                logger.error("Ingestion error for '%s': %s", filename, str(e))
                confInfo['result'].append('status', 'error')
                confInfo['result'].append('message', 'Ingestion error: %s' % str(e))
                return

            # Build success response with scan summary
            asset_hostname   = events[0].get('asset_hostname', 'Unknown') if events else 'Unknown'
            benchmark_title  = events[0].get('benchmark_title', 'Unknown') if events else 'Unknown'
            profile          = events[0].get('profile', '') if events else ''
            compliance_score = events[0].get('compliance_score', 0.0) if events else 0.0

            result_counts = {}
            for e in events:
                r = e.get('result', 'unknown')
                result_counts[r] = result_counts.get(r, 0) + 1

            confInfo['result'].append('status', 'success')
            confInfo['result'].append('message', 'Successfully ingested %d rule results from %s' % (len(events), filename))
            logger.info("Upload successful: %d events from '%s' (host=%s, benchmark=%s, score=%s%%)",
                        len(events), filename, asset_hostname, benchmark_title, round(compliance_score, 1))
            confInfo['result'].append('event_count', str(len(events)))
            confInfo['result'].append('asset_hostname', asset_hostname)
            confInfo['result'].append('benchmark_title', benchmark_title)
            confInfo['result'].append('profile', profile)
            confInfo['result'].append('compliance_score', str(round(compliance_score, 1)))
            confInfo['result'].append('result_summary', json.dumps(result_counts))

        except Exception as e:
            logger.error("Upload failed: %s", str(e))
            confInfo['result'].append('status', 'error')
            confInfo['result'].append('message', 'Upload failed: %s' % str(e))

    def handleList(self, confInfo):
        """Handle GET request -- return handler status/info."""
        confInfo['upload_info'].append('status', 'ready')
        confInfo['upload_info'].append('supported_formats', '.xml')
        confInfo['upload_info'].append('description', 'Upload CIS-CAT Pro ARF XML scan result files (.xml)')


admin.init(ARFUploadHandler, admin.CONTEXT_APP_AND_USER)
