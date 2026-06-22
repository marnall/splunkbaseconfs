#!/usr/bin/env python3
"""
REST handler for applying themes to dashboards
Uses PersistentServerConnectionApplication for Splunk compatibility
"""
import sys
import os
import json
import xml.etree.ElementTree as ET
import urllib.parse
import urllib.request
import ssl

# Splunk SDK imports
from splunk.persistconn.application import PersistentServerConnectionApplication

class ApplyThemeHandler(PersistentServerConnectionApplication):
    """REST handler to apply themes to dashboards"""
    
    def __init__(self, command_line, command_arg):
        super(ApplyThemeHandler, self).__init__()
    
    def _load_themes_metadata(self):
        """Load theme metadata from themes_metadata.json"""
        try:
            splunk_home = os.environ.get('SPLUNK_HOME', '/Applications/Splunk')
            metadata_path = os.path.join(
                splunk_home, 'etc', 'apps', 'dashboard_theme_manager',
                'appserver', 'static', 'themes_metadata.json'
            )
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Extract theme IDs and modes
            theme_ids = []
            theme_modes = {}
            
            for theme in metadata.get('themes', []):
                theme_id = theme.get('id')
                mode = theme.get('mode', 'dark').lower()  # Convert to lowercase
                if theme_id:
                    theme_ids.append(theme_id)
                    theme_modes[theme_id] = mode
            
            return theme_ids, theme_modes
        except Exception as e:
            # Fallback to empty lists if file not found
            return [], {}

    
    def handle(self, in_string):
        """Handle POST request - in_string is JSON from Splunk"""
        try:
            # Parse the incoming JSON request
            request = json.loads(in_string)
            method = request.get('method', 'POST')
            
            if method != 'POST':
                return {
                    'status': 405,
                    'headers': {'Content-Type': 'application/json'},
                    'payload': json.dumps({
                        'success': False,
                        'error': 'Method not allowed. Use POST.'
                    })
                }
            
            # Get payload from request
            payload_str = request.get('payload', '')
            
            # Parse form data from payload
            params = {}
            if payload_str:
                for param in payload_str.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        # URL decode
                        params[urllib.parse.unquote_plus(key)] = urllib.parse.unquote_plus(value)
            
            # Check for action parameter
            action = params.get('action', 'apply').strip()
            
            if action == 'remove':
                return self.handle_remove(params, request)
            else:
                return self.handle_apply(params, request)
        
        except Exception as e:
            import traceback
            return {
                'status': 500,
                'headers': {'Content-Type': 'application/json'},
                'payload': json.dumps({
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
            }
    
    def handle_remove(self, params, request):
        """Handle remove theme request"""
        try:
            dashboard = params.get('dashboard', '').strip()
            source_app = params.get('source_app', 'dashboard_theme_manager').strip()
            
            if not dashboard:
                return {
                    'status': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'payload': json.dumps({
                        'success': False,
                        'error': 'Missing required parameter: dashboard'
                    })
                }
            
            # Get Splunk home
            splunk_home = os.environ.get('SPLUNK_HOME', '/Applications/Splunk')
            
            # Paths to check for dashboard file
            paths = [
                os.path.join(splunk_home, 'etc', 'apps', source_app, 'local', 'data', 'ui', 'views', f'{dashboard}.xml'),
                os.path.join(splunk_home, 'etc', 'apps', source_app, 'default', 'data', 'ui', 'views', f'{dashboard}.xml'),
            ]
            
            dashboard_path = None
            for path in paths:
                if os.path.exists(path):
                    dashboard_path = path
                    break
            
            if not dashboard_path:
                return {
                    'status': 404,
                    'headers': {'Content-Type': 'application/json'},
                    'payload': json.dumps({
                        'success': False,
                        'error': f'Dashboard {dashboard} not found'
                    })
                }
            
            # Check if file has XML declaration
            has_declaration = False
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                if first_line.strip().startswith('<?xml'):
                    has_declaration = True
            
            # Read dashboard XML
            tree = ET.parse(dashboard_path)
            root = tree.getroot()
            
            # Load theme IDs dynamically from themes_metadata.json
            theme_panel_ids, _ = self._load_themes_metadata()
            
            if not theme_panel_ids:
                # Fallback to empty list if metadata not loaded
                theme_panel_ids = []
            
            rows_to_remove = []
            for row in root.findall('.//row'):
                for panel in row.findall('panel'):
                    ref = panel.get('ref')
                    if ref in theme_panel_ids:
                        rows_to_remove.append(row)
                        break
            
            if not rows_to_remove:
                return {
                    'status': 404,
                    'headers': {'Content-Type': 'application/json'},
                    'payload': json.dumps({
                        'success': False,
                        'error': 'No theme found on this dashboard'
                    })
                }
            
            for row in rows_to_remove:
                root.remove(row)
            
            # Reset theme attribute to default dark
            root.set('theme', 'dark')
            
            # Save to local directory
            local_path = os.path.join(splunk_home, 'etc', 'apps', source_app, 'local', 'data', 'ui', 'views', f'{dashboard}.xml')
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Write XML
            if has_declaration:
                tree.write(local_path, encoding='utf-8', xml_declaration=True)
            else:
                tree.write(local_path, encoding='utf-8', xml_declaration=False)
            
            # Trigger cache refresh for the dashboard
            try:
                session_key = request.get('session', {}).get('authtoken', '')
                if session_key:
                    # Get splunkd URI from environment or use default
                    splunkd_uri = os.environ.get('SPLUNKD_URI', 'https://localhost:8089')
                    
                    # Reload views in the source app to refresh cache
                    reload_url = f'{splunkd_uri}/servicesNS/nobody/{source_app}/data/ui/views/_reload'
                    reload_req = urllib.request.Request(reload_url, method='POST')
                    reload_req.add_header('Authorization', f'Splunk {session_key}')
                    
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    
                    try:
                        urllib.request.urlopen(reload_req, context=ctx, timeout=5)
                    except Exception as reload_error:
                        # Reload failed but theme was removed - not critical
                        pass
            except Exception as refresh_error:
                # Cache refresh failed but theme was removed successfully
                pass
            
            return {
                'status': 200,
                'headers': {'Content-Type': 'application/json'},
                'payload': json.dumps({
                    'success': True,
                    'message': f'Theme removed from dashboard {dashboard}'
                })
            }
            
        except Exception as e:
            import traceback
            return {
                'status': 500,
                'headers': {'Content-Type': 'application/json'},
                'payload': json.dumps({
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
            }
    
    def handle_apply(self, params, request):
        """Handle apply theme request"""
        try:
            dashboard = params.get('dashboard', '').strip()
            theme_id = params.get('theme_id', '').strip()
            source_app = params.get('source_app', 'dashboard_theme_manager').strip()
            
            if not dashboard or not theme_id:
                return {
                    'status': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'payload': json.dumps({
                        'success': False,
                        'error': 'Missing required parameters: dashboard and theme_id'
                    })
                }
            
            # Get Splunk home
            splunk_home = os.environ.get('SPLUNK_HOME', '/Applications/Splunk')
            theme_app = 'dashboard_theme_manager'  # App where themes are stored
            
            # Load theme IDs and modes dynamically from themes_metadata.json
            theme_panel_ids, theme_mode_map = self._load_themes_metadata()
            
            # Get the mode for the selected theme (default to dark if not found)
            theme_mode = theme_mode_map.get(theme_id, 'dark')
            
            # Paths to check for dashboard file - look in the source app
            paths = [
                os.path.join(splunk_home, 'etc', 'apps', source_app, 'local', 'data', 'ui', 'views', f'{dashboard}.xml'),
                os.path.join(splunk_home, 'etc', 'apps', source_app, 'default', 'data', 'ui', 'views', f'{dashboard}.xml'),
            ]
            
            dashboard_path = None
            for path in paths:
                if os.path.exists(path):
                    dashboard_path = path
                    break
            
            if not dashboard_path:
                return {
                    'status': 404,
                    'headers': {'Content-Type': 'application/json'},
                    'payload': json.dumps({
                        'success': False,
                        'error': f'Dashboard {dashboard} not found'
                    })
                }
            
            # Check if file has XML declaration
            has_declaration = False
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                if first_line.strip().startswith('<?xml'):
                    has_declaration = True
            
            # Read dashboard XML
            tree = ET.parse(dashboard_path)
            root = tree.getroot()
            
            # Remove existing theme panel rows (using theme_panel_ids loaded above)
            rows_to_remove = []
            for row in root.findall('.//row'):
                for panel in row.findall('panel'):
                    ref = panel.get('ref')
                    if ref in theme_panel_ids:
                        rows_to_remove.append(row)
                        break
            
            for row in rows_to_remove:
                root.remove(row)
            
            # Update theme attribute in root element
            # Only update the theme attribute value, preserve everything else
            current_theme = root.get('theme', 'dark')  # Get current value, default to dark
            if current_theme != theme_mode:
                root.set('theme', theme_mode)
            
            # Add new theme panel row
            new_row = ET.SubElement(root, 'row')
            new_panel = ET.SubElement(new_row, 'panel')
            new_panel.set('ref', theme_id)
            new_panel.set('app', 'dashboard_theme_manager')
            new_panel.set('depends', '$alwaysHideCSS$')
            new_panel.text = ''  # Force explicit closing tag instead of self-closing
            
            # Save to local directory of the source app
            local_path = os.path.join(splunk_home, 'etc', 'apps', source_app, 'local', 'data', 'ui', 'views', f'{dashboard}.xml')
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Write XML - only include declaration if original had one
            if has_declaration:
                tree.write(local_path, encoding='utf-8', xml_declaration=True)
            else:
                tree.write(local_path, encoding='utf-8', xml_declaration=False)
            
            # Post-process to fix self-closing panel tags
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace self-closing panel tags with explicit closing tags
            import re
            content = re.sub(r'<panel([^>]*)/>', r'<panel\1></panel>', content)
            content = re.sub(r'<row([^>]*)/>', r'<row\1></row>', content)
            
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Refresh the dashboard cache using _reload endpoint
            try:
                # Get session info from request
                session_key = request.get('session', {}).get('authtoken', '')
                
                if session_key:
                    # Get splunkd URI from environment or use default
                    splunkd_uri = os.environ.get('SPLUNKD_URI', 'https://localhost:8089')
                    
                    # Reload views in the source app to refresh cache
                    reload_url = f'{splunkd_uri}/servicesNS/nobody/{source_app}/data/ui/views/_reload'
                    req = urllib.request.Request(reload_url, method='POST')
                    req.add_header('Authorization', f'Splunk {session_key}')
                    
                    # Create SSL context that doesn't verify certificates
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    
                    try:
                        urllib.request.urlopen(req, context=ctx, timeout=5)
                    except Exception as reload_error:
                        # Reload failed but theme was applied - not critical
                        pass
            except Exception as refresh_error:
                # Cache refresh failed but theme was applied successfully
                pass
            
            # Return success
            return {
                'status': 200,
                'headers': {'Content-Type': 'application/json'},
                'payload': json.dumps({
                    'success': True,
                    'message': f'Theme {theme_id} applied to dashboard {dashboard}',
                    'dashboard_path': local_path
                })
            }
            
        except Exception as e:
            import traceback
            return {
                'status': 500,
                'headers': {'Content-Type': 'application/json'},
                'payload': json.dumps({
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
            }
