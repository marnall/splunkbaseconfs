import json
import uuid
import splunk.auth as auth
import test_runner
import six

username = ''
password = ''
mgmt_scheme_host_port = ''

class Test(test_runner.TestRESTHandler):

    def setUp(self):
        self.session_key = auth.getSessionKey(username, password)
        self.name = uuid.uuid4().hex

        self.searchtemplate1name = 'searchtemplate1'
        self.searchtemplate1search = 'search template 1'

        template_1_postargs = {
            'name': 'searchtemplate1',
            'search_string': 'search template 1'
        }

        self.search_template1_link_alt = self.create_search_template(template_1_postargs)

    def tearDown(self):
        self.delete_search_template(self.searchtemplate1name)

    def test_crud(self):
        # List
        response, content = self.list_helper('environments')
        payload = json.loads(content)
        self.assertTrue(isinstance(payload['entry'], list), msg='has entry list')

        # Create
        mgmt_scheme_host_port = ' https://localhost:8090 '
        username = ' admin '
        password = ' changed '
        postargs = {
            'name': self.name,
            'mgmt_scheme_host_port': mgmt_scheme_host_port,
            'username': username,
            'password': password,
        }
        response, content = self.create_helper('environments', postargs)
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['name'], self.name, msg='created entity with matching name')
        self.assertEqual(payload['entry'][0]['content']['mgmt_scheme_host_port'], mgmt_scheme_host_port.strip(), msg='created entity with matching mgmt_scheme_host_port and stripped whitespace')
        self.assertEqual(payload['entry'][0]['content']['username'], username.strip(), msg='created entity with matching username and stripped whitespace')

        # Read
        response, content = self.read_helper('environments', self.name)
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['name'], self.name, msg='read entity with matching')

        # Update
        splunk_web_uri = 'http://localhost:8000'
        username = 'lenoard'
        postargs = {
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': splunk_web_uri,
            'username': username,
            'password': password,
        }
        response, content = self.edit_helper('environments', self.name, postargs)
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['content']['splunk_web_uri'], splunk_web_uri, msg='updated splunk_web_uri with matching value')
        self.assertEqual(payload['entry'][0]['content']['username'], username, msg='updated username with matching value')

        # Delete
        response, content = self.delete_helper('environments', self.name)
        self.assertEqual(response['status'], '200', msg='deleted entity with correct status code')
        retrieved_entity_after_delete = True
        try:
            response, content = self.read_helper('environments', self.name)
        except Exception as e:
             retrieved_entity_after_delete = False
        self.assertFalse(retrieved_entity_after_delete, msg='could not retrieve non existent entity')

    def test_valid_params(self):
        postargs = {
            'name': self.name,
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': 'changed',
        }

        update_postargs = {
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': 'changed',
        }

        self.crud_test_helper(postargs, update_postargs)

        # Capital letters in name (space)
        postargs_valid_name_w_caps_space = postargs.copy()
        postargs_valid_name_w_caps_space['name'] = ' New Name '
        response, content = self.create_helper('environments', postargs_valid_name_w_caps_space)
        payload = json.loads(content)
        # Should create successfully and name should match user text entry exactly
        self.assertEqual(response['status'], '201', msg='failure while creating entry')
        self.assertEqual(payload['entry'][0]['name'], postargs_valid_name_w_caps_space['name'].strip(), msg='entity name does not match user entry (space)')
        response, content = self.delete_helper('environments', postargs_valid_name_w_caps_space['name'].strip())
        self.assertEqual(response['status'], '200', msg='deleted entity with correct status code')

        # Capital letters in name (dash)
        postargs_valid_name_w_caps_dash = postargs.copy()
        postargs_valid_name_w_caps_dash['name'] = ' New-Name '
        response, content = self.create_helper('environments', postargs_valid_name_w_caps_dash)
        payload = json.loads(content)
        # Should create successfully and name should match user text entry exactly
        self.assertEqual(response['status'], '201', msg='failure while creating entry')
        self.assertEqual(payload['entry'][0]['name'], postargs_valid_name_w_caps_dash['name'].strip(), msg='entity name does not match user entry (dash)')
        response, content = self.delete_helper('environments', postargs_valid_name_w_caps_dash['name'].strip())
        self.assertEqual(response['status'], '200', msg='deleted entity with correct status code')

        # Capital letters in name (underscore)
        postargs_valid_name_w_caps_underscore = postargs.copy()
        postargs_valid_name_w_caps_underscore['name'] = '  New_Name '
        response, content = self.create_helper('environments', postargs_valid_name_w_caps_underscore)
        payload = json.loads(content)
        # Should create successfully and name should match user text entry exactly
        self.assertEqual(response['status'], '201', msg='failure while creating entry')
        self.assertEqual(payload['entry'][0]['name'], postargs_valid_name_w_caps_underscore['name'].strip(), msg='entity name does not match user entry (underscore)')
        response, content = self.delete_helper('environments', postargs_valid_name_w_caps_underscore['name'].strip())
        self.assertEqual(response['status'], '200', msg='deleted entity with correct status code')

    def test_valid_tags(self):
        postargs = {
            'name': self.name,
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': 'changed',
            'tags': 'basic'
        }

        update_postargs = {
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': 'changed',
            'tags': 'basic,new'
        }

        self.crud_test_helper(postargs, update_postargs)

    def test_valid_tags_w_autogen(self):
        postargs = {
            'name': self.name,
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': 'changed',
            'tags': 'basic',
            'search_template_link_alternates': self.search_template1_link_alt
        }

        update_postargs = {
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': 'changed',
            'tags': 'basic,new'
        }

        self.crud_test_helper(postargs, update_postargs)

    def test_invalid_autogen(self):
        postargs = {
            'name': self.name,
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': 'changed',
            'tags': 'basic',
            'search_template_link_alternates': 'asdf'
        }

        # Invalid tag
        postargs_invalid_autogen = postargs.copy()
        response, content = self.create_helper('environments', postargs_invalid_autogen)
        self.assertEqual(response['status'], '409', msg='failed due to invalid search_template_link_alternates')

    def test_invalid_tags(self):
        postargs = {
            'name': self.name,
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': 'changed',
            'tags': 'will break'
        }

        # Invalid tag
        postargs_invalid_tag = postargs.copy()
        response, content = self.create_helper('environments', postargs_invalid_tag)
        self.assertEqual(response['status'], '500', msg='failed due to invalid tag')

    def test_invalid_tags_update(self):
        postargs = {
            'name': self.name,
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': 'changed',
            'tags': 'ok'
        }

        update_postargs = {
            'name': self.name,
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': 'changed',
            'tags': 'will break'
        }

        # Invalid tag
        response, content = self.create_helper('environments', postargs)
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['name'], self.name, msg='created entity with matching name')

        response, content = self.edit_helper('environments', self.name, update_postargs)
        self.assertEqual(response['status'], '500', msg='failed due to invalid tag')

        response, content = self.delete_helper('environments', postargs['name'].strip())
        self.assertEqual(response['status'], '200', msg='deleted entity with correct status code')

    def test_valid_empty_password(self):
        create_postargs = {
            'name': self.name,
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': 'changed',
        }

        update_postargs = {
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': '',
        }

        self.crud_test_helper(create_postargs, update_postargs)

    def test_invalid_params(self):
        postargs = {
            'name': self.name,
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': 'changed',
        }

        # Invalid name
        postargs_invalid_name = postargs.copy()
        postargs_invalid_name['name'] = ''
        response, content = self.create_helper('environments', postargs_invalid_name)
        # this looks like something being thrown by the generic conf handler and should be caught buy our validator
        self.assertEqual(response['status'], '400', msg='failed due to missing name')

        # Invalid mgmt_scheme_host_port
        postargs_invalid_mgmt_scheme_host_port = postargs.copy()
        postargs_invalid_mgmt_scheme_host_port['mgmt_scheme_host_port'] = ''
        response, content = self.create_helper('environments', postargs_invalid_mgmt_scheme_host_port)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to missing postargs_invalid_mgmt_scheme_host_port')

        # Invalid mgmt_scheme_host_port
        postargs_invalid_mgmt_scheme_host_port = postargs.copy()
        postargs_invalid_mgmt_scheme_host_port['mgmt_scheme_host_port'] = 'htp://foo.com'
        response, content = self.create_helper('environments', postargs_invalid_mgmt_scheme_host_port)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to invalid postargs_invalid_mgmt_scheme_host_port')

        # Invalid splunk_web_uri
        postargs_invalid_splunk_web_uri = postargs.copy()
        postargs_invalid_splunk_web_uri['splunk_web_uri'] = 'htp://foo.com'
        response, content = self.create_helper('environments', postargs_invalid_splunk_web_uri)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to invalid postargs_invalid_splunk_web_uri')

        # Invalid username
        postargs_username = postargs.copy()
        postargs_username['username'] = ''
        response, content = self.create_helper('environments', postargs_username)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to missing username')

        # Invalid password
        postargs_password = postargs.copy()
        postargs_password['password'] = ''
        response, content = self.create_helper('environments', postargs_password)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to missing password')

    def test_password_no_exist_delete(self):
        postargs = {
            'name': self.name,
            'mgmt_scheme_host_port': 'https://localhost:8090',
            'splunk_web_uri': 'http://localhost:8000',
            'username': 'admin',
            'password': 'changed',
        }

        # Create
        postargs_create = postargs.copy()
        response, content = self.create_helper('environments', postargs_create)
        payload = json.loads(content)

        # Delete associated password
        password_name = six.moves.urllib.parse.unquote(payload['entry'][0]['content']['password_link_alternate'].split('/')[-1])
        self.delete_helper('storage/passwords', password_name)

        # Delete environment with invalid password reference
        response, content = self.delete_helper('environments', postargs_create['name'])
        self.assertEqual(response['status'], '200', msg='deleted entity with correct status code')

    def crud_test_helper(self, create_postargs, update_postargs):
        # List
        response, content = self.list_helper('environments')
        payload = json.loads(content)
        self.assertTrue(isinstance(payload['entry'], list), msg='has entry list')

        # Create
        response, content = self.create_helper('environments', create_postargs)
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['name'], create_postargs['name'], msg='created entity with matching name')
        self.assertEqual(payload['entry'][0]['content']['mgmt_scheme_host_port'], create_postargs['mgmt_scheme_host_port'].strip(),
                         msg='created entity with matching mgmt_scheme_host_port and stripped whitespace')
        self.assertEqual(payload['entry'][0]['content']['username'], create_postargs['username'].strip(),
                         msg='created entity with matching username and stripped whitespace')

        # Read
        response, content = self.read_helper('environments', create_postargs['name'])
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['name'], create_postargs['name'], msg='read entity with matching')

        # Update
        response, content = self.edit_helper('environments', create_postargs['name'], update_postargs)
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['content']['splunk_web_uri'], update_postargs['splunk_web_uri'],
                         msg='updated splunk_web_uri with matching value')
        self.assertEqual(payload['entry'][0]['content']['username'], update_postargs['username'],
                         msg='updated username with matching value')

        # Delete
        response, content = self.delete_helper('environments', create_postargs['name'])
        self.assertEqual(response['status'], '200', msg='deleted entity with correct status code')
        retrieved_entity_after_delete = True
        try:
            response, content = self.read_helper('environments', create_postargs['name'])
        except Exception as e:
            retrieved_entity_after_delete = False
        self.assertFalse(retrieved_entity_after_delete, msg='could not retrieve non existent entity')

    def create_search_template(self, postargs):
        search_templates_path = '/servicesNS/%s/%s/configs/conf-%s' % ('nobody', 'mothership', 'environment_search_templates')

        # TODO Error handling/asserts...
        response, content = self.template_create_helper(search_templates_path,
                                                                                       postargs)

        payload = json.loads(content)


        return payload['entry'][0]['links']['alternate']

    def delete_search_template(self, template_name):
        # TODO Error handling/asserts...
        search_template_path = '/servicesNS/%s/%s/configs/conf-%s/%s' % (
        'nobody', 'mothership', 'environment_search_templates', template_name)
        self.template_delete_helper(search_template_path)

if __name__ == '__main__':
    args = test_runner.cli_arguments()
    username = args.username
    password = args.password
    mgmt_scheme_host_port = args.mgmt_scheme_host_port
    test_runner.run_test(Test)
