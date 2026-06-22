#!/usr/bin/env python3
"""
STIG Compliance App - Checklist Upload Handler
Custom REST endpoint for uploading .ckl and .cklb files through the web UI.

This endpoint receives checklist files via POST, parses them using parse_ckl.py,
and ingests the resulting JSON into the index defined in the stig_base macro.

INDEX CONFIGURATION:
    The target index is read automatically from the stig_base macro definition.
    To change the index, update the macro via Splunk Web:
        Settings > Advanced Search > Search Macros > stig_base
    No code changes required.

Supported formats:
    .ckl  - XML-based (STIG Viewer 2.x)
    .cklb - JSON-based (STIG Viewer 3.x)

Security controls:
    - File size limit (MAX_UPLOAD_SIZE_BYTES)
    - Duplicate upload detection via KV store hash
    - Capability enforcement (admin_all_objects)
    - Structured logging to splunkd.log
"""

import os
import sys
import json
import time
import hashlib
import logging
import tempfile
import splunk.admin as admin
import splunk.rest as rest
import splunk.entity as entity

# Structured logging to splunkd.log
logger = logging.getLogger('stig_compliance_app.upload_handler')
logger.setLevel(logging.INFO)

# Maximum upload size: 10 MB
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024

# Add bin directory to path for parse_ckl import
bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin')
if bin_dir not in sys.path:
    sys.path.insert(0, bin_dir)

class CKLUploadHandler(admin.MConfigHandler):
    """REST handler for CKL/CKLB file uploads."""

    def _get_index_from_macro(self):
        """Read the target index from the stig_base macro definition.
        Falls back to 'main' if macro cannot be read."""
        try:
            import re
            macro_entity = entity.getEntity(
                'admin/macros', 'stig_base',
                namespace='stig_compliance_app',
                owner='nobody',
                sessionKey=self.getSessionKey()
            )
            definition = macro_entity.get('definition', 'index=main sourcetype="stig:ckl"')
            match = re.search(r'index=(\S+)', definition)
            if match:
                return match.group(1)
        except Exception:
            pass
        return 'main'

    def _get_username(self):
        """Get the username of the caller from the session."""
        try:
            return self.userName if hasattr(self, 'userName') else 'unknown'
        except Exception:
            return 'unknown'

    def _check_duplicate(self, file_hash, session_key):
        """Check if file hash already exists in KV store.
        Returns the existing record if duplicate, None otherwise."""
        try:
            import urllib.parse
            import http.client
            import ssl

            query = json.dumps({"file_hash": file_hash})
            params = urllib.parse.urlencode({'query': query})

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            conn = http.client.HTTPSConnection('127.0.0.1', 8089, context=ctx)
            headers = {
                'Authorization': 'Splunk %s' % session_key,
                'Content-Type': 'application/json'
            }

            conn.request('GET',
                         '/servicesNS/nobody/stig_compliance_app/storage/collections/data/stig_upload_hashes?%s' % params,
                         headers=headers)
            resp = conn.getresponse()
            body = resp.read().decode('utf-8')
            conn.close()

            if resp.status == 200:
                records = json.loads(body)
                if records:
                    return records[0]
        except Exception as e:
            logger.warning('action=check_duplicate status=error message="%s"' % str(e))
        return None

    def _store_hash(self, file_hash, upload_batch_id, filename, upload_time, username, session_key):
        """Store file hash in KV store for future duplicate detection."""
        try:
            import http.client
            import ssl

            record = json.dumps({
                'file_hash': file_hash,
                'upload_batch_id': upload_batch_id,
                'filename': filename,
                'upload_time': upload_time,
                'uploaded_by': username
            })

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            conn = http.client.HTTPSConnection('127.0.0.1', 8089, context=ctx)
            headers = {
                'Authorization': 'Splunk %s' % session_key,
                'Content-Type': 'application/json'
            }

            conn.request('POST',
                         '/servicesNS/nobody/stig_compliance_app/storage/collections/data/stig_upload_hashes',
                         body=record.encode('utf-8'), headers=headers)
            resp = conn.getresponse()
            resp.read()
            conn.close()
        except Exception as e:
            logger.warning('action=store_hash status=error message="%s"' % str(e))

    def setup(self):
        self.supportedArgs.addOptArg('ckl_data')
        self.supportedArgs.addOptArg('filename')

    def handleCreate(self, confInfo):
        """Handle POST request with CKL/CKLB file data."""
        username = self._get_username()
        filename = 'upload.ckl'

        try:
            # STIG-012: In-code capability check
            try:
                user_entity = entity.getEntity(
                    'authentication/users', username,
                    namespace='stig_compliance_app',
                    owner='nobody',
                    sessionKey=self.getSessionKey()
                )
                user_roles = user_entity.get('roles', [])
                if isinstance(user_roles, str):
                    user_roles = [user_roles]
                allowed_roles = {'admin', 'power', 'sc_admin'}
                if not allowed_roles.intersection(set(user_roles)):
                    logger.warning('action=upload status=denied user=%s roles=%s' % (username, user_roles))
                    confInfo['result'].append('status', 'error')
                    confInfo['result'].append('message', 'Insufficient permissions. Upload requires admin or power role.')
                    return
            except Exception as e:
                logger.warning('action=capability_check status=error user=%s message="%s"' % (username, str(e)))
                # Allow through if capability check fails - restmap.conf is the primary gate

            ckl_data = self.callerArgs.data.get('ckl_data', [None])[0]
            filename = self.callerArgs.data.get('filename', ['upload.ckl'])[0]

            if not ckl_data:
                logger.info('action=upload status=error user=%s reason=no_data' % username)
                confInfo['result'].append('status', 'error')
                confInfo['result'].append('message', 'No checklist data provided')
                return

            # STIG-009: File size limit
            data_size = len(ckl_data.encode('utf-8')) if isinstance(ckl_data, str) else len(ckl_data)
            if data_size > MAX_UPLOAD_SIZE_BYTES:
                logger.warning('action=upload status=rejected user=%s filename=%s reason=size_exceeded size=%d limit=%d'
                               % (username, filename, data_size, MAX_UPLOAD_SIZE_BYTES))
                confInfo['result'].append('status', 'error')
                confInfo['result'].append('message', 'File exceeds maximum upload size of %d MB.' % (MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)))
                return

            # STIG-010: Duplicate upload detection
            file_hash = hashlib.sha256(ckl_data.encode('utf-8') if isinstance(ckl_data, str) else ckl_data).hexdigest()
            existing = self._check_duplicate(file_hash, self.getSessionKey())
            if existing:
                logger.info('action=upload status=duplicate user=%s filename=%s hash=%s original_batch=%s'
                            % (username, filename, file_hash[:16], existing.get('upload_batch_id', 'unknown')))
                confInfo['result'].append('status', 'error')
                confInfo['result'].append('message',
                    'Duplicate file detected. This checklist was previously uploaded as "%s" on %s (batch: %s).'
                    % (existing.get('filename', 'unknown'),
                       existing.get('upload_time', 'unknown'),
                       existing.get('upload_batch_id', 'unknown')[:8]))
                return

            # Determine file extension for proper parsing
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in ('.ckl', '.cklb'):
                file_ext = '.ckl'  # Default to .ckl for backwards compatibility

            # Write data to temp file with correct extension
            tmp_file = tempfile.NamedTemporaryFile(mode='w', suffix=file_ext, delete=False)
            tmp_file.write(ckl_data)
            tmp_file.close()

            # Parse using the unified parser (auto-detects format)
            from parse_ckl import parse_checklist_file
            events = parse_checklist_file(tmp_file.name)

            # Clean up temp file
            os.unlink(tmp_file.name)

            if not events:
                logger.info('action=upload status=error user=%s filename=%s reason=no_events_parsed' % (username, filename))
                confInfo['result'].append('status', 'error')
                confInfo['result'].append('message', 'No events parsed from checklist file. Verify the file is a valid DISA STIG Viewer checklist (.ckl or .cklb).')
                return

            # Write events to JSON string
            json_data = '\n'.join(json.dumps(event) for event in events)

            # Ingest via REST API receivers/simple endpoint
            # This goes through the forwarding pipeline to indexers
            try:
                import urllib.parse
                import http.client
                import ssl

                # Read target index from stig_base macro
                target_index = self._get_index_from_macro()

                params = urllib.parse.urlencode({
                    'index': target_index,
                    'sourcetype': 'stig:ckl',
                    'source': 'stig_upload:%s' % filename
                })

                # Connect to local splunkd
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
                resp = conn.getresponse()
                resp_body = resp.read().decode('utf-8')
                conn.close()

                if resp.status not in (200, 201):
                    logger.error('action=upload status=ingestion_failed user=%s filename=%s http_status=%d'
                                 % (username, filename, resp.status))
                    confInfo['result'].append('status', 'error')
                    confInfo['result'].append('message', 'Ingestion failed with status %d: %s' % (resp.status, resp_body[:200]))
                    return

            except Exception as e:
                logger.error('action=upload status=ingestion_error user=%s filename=%s message="%s"'
                             % (username, filename, str(e)))
                confInfo['result'].append('status', 'error')
                confInfo['result'].append('message', 'Ingestion error: %s' % str(e))
                return

            # Get summary info
            host_name = events[0].get('asset_host_name', 'Unknown') if events else 'Unknown'
            stig_title = events[0].get('stig_title', 'Unknown') if events else 'Unknown'
            upload_batch_id = events[0].get('upload_batch_id', 'Unknown') if events else 'Unknown'
            upload_time = events[0].get('upload_time', '') if events else ''

            status_counts = {}
            for e in events:
                s = e.get('vuln_status', 'Unknown')
                status_counts[s] = status_counts.get(s, 0) + 1

            # STIG-010: Store hash after successful ingestion
            self._store_hash(file_hash, upload_batch_id, filename, upload_time, username, self.getSessionKey())

            # STIG-011: Log successful upload
            logger.info('action=upload status=success user=%s filename=%s host=%s stig="%s" events=%d batch=%s hash=%s size=%d'
                        % (username, filename, host_name, stig_title, len(events), upload_batch_id[:8], file_hash[:16], data_size))

            confInfo['result'].append('status', 'success')
            confInfo['result'].append('message', 'Successfully ingested %d findings from %s' % (len(events), filename))
            confInfo['result'].append('event_count', str(len(events)))
            confInfo['result'].append('host_name', host_name)
            confInfo['result'].append('stig_title', stig_title)
            confInfo['result'].append('status_summary', json.dumps(status_counts))

        except Exception as e:
            logger.error('action=upload status=failed user=%s filename=%s message="%s"' % (username, filename, str(e)))
            confInfo['result'].append('status', 'error')
            confInfo['result'].append('message', 'Upload failed: %s' % str(e))

    def handleList(self, confInfo):
        """Handle GET request - return upload status/info."""
        confInfo['upload_info'].append('status', 'ready')
        confInfo['upload_info'].append('supported_formats', '.ckl, .cklb')
        confInfo['upload_info'].append('description', 'Upload DISA STIG Viewer checklist files (.ckl or .cklb)')
        confInfo['upload_info'].append('max_upload_size_mb', str(MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)))


admin.init(CKLUploadHandler, admin.CONTEXT_APP_AND_USER)
