"""MCP Templates Handler"""
import sys, os, json, time, uuid, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
import splunk.admin as admin
from mcp_base import MCPBaseHandler, KVStoreClient
from validators import validate_string, validate_choice, ValidationError

logger = logging.getLogger(__name__)

class MCPTemplatesHandler(MCPBaseHandler):

    def setup(self):
        # spl / tags are v4 additions — optional, default to empty string for
        # back-compat with v3 templates that didn't have them.
        for arg in ('template_name', 'description', 'natural_language', 'category',
                    'spl', 'tags', 'output_mode'):
            self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        try:
            service = self._get_splunk_service()
            kv_client = KVStoreClient(service, 'mcp_query_templates')
            records = kv_client.query(limit=200)
            confInfo['templates'].append('records', json.dumps(records))
            confInfo['templates'].append('count', str(len(records)))
        except Exception as e:
            logger.exception("Failed to list templates")
            confInfo['templates'].append('error', str(e))

    def handleCreate(self, confInfo):
        try:
            self._check_license()
            self._check_template_limit()

            name = self.callerArgs.data.get('template_name', [None])[0]
            description = self.callerArgs.data.get('description', [''])[0] or ''
            natural_language = self.callerArgs.data.get('natural_language', [None])[0]
            category = self.callerArgs.data.get('category', ['Other'])[0] or 'Other'
            spl = self.callerArgs.data.get('spl', [''])[0] or ''
            tags = self.callerArgs.data.get('tags', [''])[0] or ''

            try:
                name = validate_string(name, 'template_name', max_len=200)
                natural_language = validate_string(natural_language, 'natural_language', max_len=2000)
                if description:
                    description = validate_string(description, 'description', min_len=0, max_len=1000)
                category = validate_choice(category, 'category',
                    ['Security', 'Performance', 'Network', 'Application', 'Infrastructure', 'Other'],
                    default='Other')
                if spl:
                    spl = validate_string(spl, 'spl', min_len=0, max_len=4000)
                if tags:
                    tags = validate_string(tags, 'tags', min_len=0, max_len=500)
            except ValidationError as ve:
                raise admin.ArgValidationException(str(ve))

            user = self.userName or 'unknown'
            now_ts = int(time.time())
            template_record = {
                'template_id': str(uuid.uuid4()),
                'name': name, 'description': description,
                'natural_language': natural_language, 'category': category,
                'spl': spl, 'tags': tags,
                'created_by': user, 'created_at': now_ts, 'updated_at': now_ts,
            }

            service = self._get_splunk_service()
            kv_client = KVStoreClient(service, 'mcp_query_templates')
            record_id = kv_client.insert(template_record)

            confInfo['result'].append('success', 'true')
            confInfo['result'].append('template_id', template_record['template_id'])
            confInfo['result'].append('_key', record_id)

        except admin.ArgValidationException:
            raise
        except Exception as e:
            logger.exception("Failed to create template")
            confInfo['result'].append('error', str(e))

    def handleEdit(self, confInfo):
        try:
            record_id = self.callerArgs.id
            if not record_id:
                raise admin.ArgValidationException("Template ID is required")

            update_data = {}
            for field in ['template_name', 'description', 'natural_language', 'category', 'spl', 'tags']:
                val = self.callerArgs.data.get(field, [None])[0]
                if val is not None:
                    store_field = 'name' if field == 'template_name' else field
                    try:
                        if field == 'template_name':
                            val = validate_string(val, 'template_name', max_len=200)
                        elif field == 'natural_language':
                            val = validate_string(val, 'natural_language', max_len=2000)
                        elif field == 'description':
                            val = validate_string(val, 'description', min_len=0, max_len=1000)
                        elif field == 'category':
                            val = validate_choice(val, 'category',
                                ['Security', 'Performance', 'Network', 'Application', 'Infrastructure', 'Other'],
                                default='Other')
                        elif field == 'spl':
                            val = validate_string(val, 'spl', min_len=0, max_len=4000)
                        elif field == 'tags':
                            val = validate_string(val, 'tags', min_len=0, max_len=500)
                    except ValidationError as ve:
                        raise admin.ArgValidationException(str(ve))
                    update_data[store_field] = val

            if not update_data:
                raise admin.ArgValidationException("No fields to update")
            update_data['updated_at'] = int(time.time())

            service = self._get_splunk_service()
            kv_client = KVStoreClient(service, 'mcp_query_templates')
            existing = kv_client.get_by_id(record_id)
            if not existing:
                raise admin.ArgValidationException(f"Template {record_id} not found")

            existing.update(update_data)
            kv_client.update(record_id, existing)

            confInfo['result'].append('success', 'true')
            confInfo['result'].append('message', 'Template updated successfully')

        except admin.ArgValidationException:
            raise
        except Exception as e:
            logger.exception("Failed to update template")
            confInfo['result'].append('error', str(e))

    def handleRemove(self, confInfo):
        try:
            record_id = self.callerArgs.id
            if not record_id:
                raise admin.ArgValidationException("Template ID is required")

            service = self._get_splunk_service()
            kv_client = KVStoreClient(service, 'mcp_query_templates')
            kv_client.delete(record_id)

            confInfo['result'].append('success', 'true')
            confInfo['result'].append('message', 'Template deleted successfully')

        except admin.ArgValidationException:
            raise
        except Exception as e:
            logger.exception("Failed to delete template")
            confInfo['result'].append('error', str(e))

admin.init(MCPTemplatesHandler, admin.CONTEXT_APP_AND_USER)
