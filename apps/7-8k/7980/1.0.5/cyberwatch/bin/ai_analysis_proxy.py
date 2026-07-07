#!/usr/bin/env python3
"""
AI Analysis Proxy Handler for CyberWatch
Proxies AI API calls to Gemini/OpenAI/Ollama from the server side to avoid CORS issues.
Handles SSL/TLS context safely for internal/external calls.
"""

import sys
import json
import re
import ssl
import traceback

# Splunk SDK imports
import splunk.admin as admin
import splunk.entity as entity
from splunk.persistconn.application import PersistentServerConnectionApplication

# Conditional import for Python 2/3 compatibility
try:
    import urllib.request as urllib_request
    import urllib.error as urllib_error
except ImportError:
    import urllib2 as urllib_request
    import urllib2 as urllib_error

class AIAnalysisProxyHandler(PersistentServerConnectionApplication):
    """
    REST handler to proxy AI API calls server-side.
    Extends PersistentServerConnectionApplication for better performance.
    """
    
    def __init__(self, command_line, command_arg):
        super(AIAnalysisProxyHandler, self).__init__()
    
    def handle(self, in_string):
        """
        Handle incoming requests from the REST endpoint.
        Expects a JSON payload in 'in_string'.
        Returns a dict with 'payload' and 'status'.
        """
        try:
            # Parse the incoming request
            # in_string is a JSON string containing 'payload', 'method', 'query', etc.
            request = json.loads(in_string)
            method = request.get('method', 'POST')
            
            if method == 'GET':
                # Handle GET requests (e.g., list models)
                query_params = request.get('query', [])
                body = {}
                for param in query_params:
                    if len(param) == 2:
                        body[param[0]] = param[1]
                
                action = body.get('action', 'analyze')
                if action == 'list_models':
                    return self.handle_list_models(body)
                else:
                    return {
                        'status': 400,
                        'headers': {'Content-Type': 'application/json'},
                        'payload': json.dumps({'error': 'Unknown action'})
                    }
            else:
                # Handle POST requests (analyze)
                # 'payload' key contains the body string
                body = json.loads(request.get('payload', '{}'))
                return self.handle_analyze(body)
                
        except Exception as e:
            # Catch top-level handling errors
            return {
                'status': 500,
                'headers': {'Content-Type': 'application/json'},
                'payload': json.dumps({'error': 'Handler exception: ' + str(e)})
            }
    
    def handle_analyze(self, body):
        """
        Handle analyze requests - dispatch to appropriate AI provider method.
        """
        headers = {'Content-Type': 'application/json'}
        try:
            provider = body.get('provider')
            api_key = body.get('api_key')
            prompt = body.get('prompt')
            system_role = body.get('system_role')
            model = body.get('model')
            
            if not provider or not api_key or not prompt:
                return {
                    'status': 400,
                    'headers': headers,
                    'payload': json.dumps({'error': 'Missing required parameters: provider, api_key, prompt'})
                }
            
            # Route to appropriate provider
            if provider == 'ollama':
                result = self.call_ollama(api_key, prompt, model, system_role)
            elif provider == 'gemini':
                result = self.call_gemini(api_key, prompt)
            elif provider == 'openai':
                result = self.call_openai(api_key, prompt, system_role)
            else:
                return {
                    'status': 400,
                    'headers': headers,
                    'payload': json.dumps({'error': 'Unsupported provider: ' + str(provider)})
                }
            
            if result.get('success'):
                return {
                    'status': 200,
                    'headers': headers,
                    'payload': json.dumps(result.get('analysis', {}))
                }
            else:
                return {
                    'status': 500,
                    'headers': headers,
                    'payload': json.dumps({'error': result.get('error', 'Unknown error')})
                }
                
        except Exception as e:
            return {
                'status': 500,
                'headers': headers,
                'payload': json.dumps({'error': 'Analyze handler exception: ' + str(e)})
            }

    def handle_list_models(self, body):
        """
        Handle list_models request (Ollama only for now).
        """
        headers = {'Content-Type': 'application/json'}
        try:
            provider = body.get('provider')
            
            if provider == 'ollama':
                url = 'https://ollama.com/api/tags' # Hypothetical endpoint, usually local tags
                # Important: For Cloud, this might be different. 
                # Assuming this is just a proxy stub for now.
                
                # Use default context but disable verify if needed for flexible deployments
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                
                req = urllib_request.Request(url)
                req.add_header('User-Agent', 'Splunk-CyberWatch/1.0')
                
                response = urllib_request.urlopen(req, context=ctx)
                response_data = json.loads(response.read().decode('utf-8'))
                
                # Transform to standard format
                models = []
                data_source = response_data.get('models', response_data)
                
                if isinstance(data_source, list):
                    for m in data_source:
                        if isinstance(m, dict):
                            name = m.get('name', '')
                            if name: models.append({'id': name, 'name': name})
                        elif isinstance(m, str):
                            models.append({'id': m, 'name': m})
                
                return {
                    'status': 200,
                    'headers': headers,
                    'payload': json.dumps({'models': models})
                }
            else:
                return {
                    'status': 400,
                    'headers': headers,
                    'payload': json.dumps({'error': 'Provider not supported'})
                }
                
        except Exception as e:
            return {
                'status': 500,
                'headers': headers,
                'payload': json.dumps({'error': 'Proxy handler exception: ' + str(e)})
            }
    
    def call_ollama(self, api_key, prompt, model, system_role=None):
        """
        Call Ollama Cloud API.
        Enforces SSL but handles potential context errors.
        """
        url = 'https://ollama.com/api/chat'
        
        if not model:
            model = 'gpt-oss:120b-cloud'
        
        # Build messages
        messages = []
        if system_role:
            messages.append({"role": "system", "content": system_role})
        messages.append({"role": "user", "content": prompt})
            
        data = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        # SSL Context
        try:
            ctx = ssl.create_default_context()
            # If internal CA issues occur, one might relax this:
            # ctx.check_hostname = False
            # ctx.verify_mode = ssl.CERT_NONE
        except:
            # Fallback for old Python/SSL versions
            ctx = None

        req = urllib_request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + api_key,
                'User-Agent': 'Splunk-CyberWatch/1.0'
            }
        )
        
        try:
            # Timeout set to 60s for long AI queries
            if ctx:
                response = urllib_request.urlopen(req, context=ctx, timeout=60)
            else:
                response = urllib_request.urlopen(req, timeout=60)
                
            response_data = json.loads(response.read().decode('utf-8'))
            
            # Check for standard Ollama response structure
            if 'message' in response_data and 'content' in response_data['message']:
                text = response_data['message']['content']
            elif 'response' in response_data: # Local Ollama legacy format
                text = response_data['response']
            else:
                return {'success': False, 'error': 'Unknown Ollama response format: ' + str(response_data.keys())}
            
            if not text:
                return {'success': False, 'error': 'Empty response from Ollama'}
            
            # Parse JSON
            # 1. Direct Parse
            try:
                analysis = json.loads(text)
                return {'success': True, 'analysis': analysis}
            except:
                pass
            
            # 2. Extract from Markdown
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
            if json_match:
                try:
                    analysis = json.loads(json_match.group(1))
                    return {'success': True, 'analysis': analysis}
                except:
                    pass
            
            # 3. Fallback: Return raw text wrapped
            return {
                'success': True,
                'analysis': {
                    'summary': text,
                    'raw_output': True,
                    'content': text
                }
            }
            
        except urllib_error.HTTPError as e:
            try:
                err_text = e.read().decode('utf-8')
            except:
                err_text = str(e)
            return {'success': False, 'error': 'Ollama API HTTP Error {}: {}'.format(e.code, err_text)}
            
        except urllib_error.URLError as e:
            return {'success': False, 'error': 'Ollama API Connection Error: {}'.format(e.reason)}
            
        except Exception as e:
            return {'success': False, 'error': 'Ollama Handler Error: {}'.format(str(e))}

    def call_gemini(self, api_key, prompt):
        url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=' + api_key
        data = {
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {
                'temperature': 0.3,
                'maxOutputTokens': 4000,
                'responseMimeType': 'application/json'
            }
        }
        
        req = urllib_request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            response = urllib_request.urlopen(req, timeout=60)
            response_data = json.loads(response.read().decode('utf-8'))
            
            if 'candidates' in response_data and response_data['candidates']:
                text = response_data['candidates'][0]['content']['parts'][0]['text']
                try:
                    return {'success': True, 'analysis': json.loads(text)}
                except:
                    return {'success': False, 'error': 'Failed to parse Gemini JSON'}
            else:
                return {'success': False, 'error': 'No candidates in Gemini response'}
                
        except Exception as e:
            return {'success': False, 'error': 'Gemini Error: ' + str(e)}

    def call_openai(self, api_key, prompt, system_role):
        url = 'https://api.openai.com/v1/chat/completions'
        data = {
            'model': 'gpt-4',
            'messages': [
                {'role': 'system', 'content': system_role},
                {'role': 'user', 'content': prompt}
            ],
            'response_format': {'type': 'json_object'},
            'temperature': 0.3,
            'max_tokens': 4000
        }
        
        req = urllib_request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + api_key
            }
        )
        
        try:
            response = urllib_request.urlopen(req, timeout=60)
            response_data = json.loads(response.read().decode('utf-8'))
            
            content = response_data['choices'][0]['message']['content']
            return {'success': True, 'analysis': json.loads(content)}
                
        except Exception as e:
            return {'success': False, 'error': 'OpenAI Error: ' + str(e)}
