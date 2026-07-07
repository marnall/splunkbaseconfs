import json
import uuid
import splunk.auth as auth
import test_runner
import environment_searches_schema

username = ''
password = ''
mgmt_scheme_host_port = ''
endpoint = 'environment_searches'
default_postargs = {
    'label': 'A Label',
    'disabled': 'False',
    'interval': '300',
    'search': 'search index="_internal" | head 3'
}

class Test(test_runner.TestRESTHandler):
    #### SETUP AND TEARDOWN #####

    def setUp(self):
        self.session_key = auth.getSessionKey(username, password)
        self.name = uuid.uuid4().hex
        self.longname = uuid.uuid4().hex*20
        self.searchtemplate1name = 'searchtemplate1'
        self.searchtemplate1search = 'search template 1'
        self.searchtemplate2name = 'searchtemplate2'
        self.searchtemplate2search = 'search template 2'
        self.endpoint = 'environment_searches'
        self.default_postargs = {
            'disabled': 'False',
            'interval': '300',
            'search': 'search index="_internal" | head 3'
        }
        self.env1_link_alternate = self.create_environment()

        template_1_postargs = {
            'name': 'searchtemplate1',
            'search_string': 'search template 1'
        }

        template_2_postargs = {
            'name': 'searchtemplate2',
            'search_string': 'search template 2'
        }
        self.search_template1_link_alt = self.create_search_template(template_1_postargs)
        self.search_template2_link_alt = self.create_search_template(template_2_postargs)

    def tearDown(self):
        # Delete environment
        response, content = self.delete_helper('environments', self.name)
        self.assertEqual(response['status'], '200', msg='Failed to delete entity with correct status code')
        retrieved_entity_after_delete = True
        try:
            response, content = self.read_helper('environments', self.name)
        except Exception as e:
            retrieved_entity_after_delete = False
        self.assertFalse(retrieved_entity_after_delete, msg='Retrieved non existent entity after deletion')

        #TODO Error handling
        self.delete_search_template(self.searchtemplate1name)
        self.delete_search_template(self.searchtemplate2name)

    #### VALID TEST CASES ####

    def test_longname(self):
        create_postargs = {
            'name': self.longname,
            'label': 'A Label',
            'environment_link_alternate': self.env1_link_alternate,
            'search': 'placeholder',
            'type': 'inline',
        }

        self.full_crud_test_helper(endpoint=endpoint, create_postargs=create_postargs, default_postargs=default_postargs, schema=environment_searches_schema.ALL_FIELDS)

    def test_inline_default_no_edit(self):
        create_postargs = {
            'name': self.name,
            'label': 'A Label',
            'environment_link_alternate': self.env1_link_alternate,
            'search': 'placeholder',
            'type': 'inline',
        }

        self.full_crud_test_helper(endpoint=endpoint, create_postargs=create_postargs, default_postargs=default_postargs, schema=environment_searches_schema.ALL_FIELDS)

    def test_inline_default_no_label_no_edit(self):
        create_postargs = {
            'name': self.name,
            'environment_link_alternate': self.env1_link_alternate,
            'search': 'placeholder',
            'type': 'inline',
        }

        self.full_crud_test_helper(endpoint=endpoint, create_postargs=create_postargs,
                                   default_postargs=default_postargs, schema=environment_searches_schema.ALL_FIELDS)

    def test_inline_hec_saved_no_exist_delete(self):
        create_postargs = {
            'name': self.name,
            'environment_link_alternate': self.env1_link_alternate,
            'search': 'placeholder',
            'type': 'inline',
        }
        schema=environment_searches_schema.ALL_FIELDS

        # Create
        response, content = self.create_helper(endpoint, create_postargs)
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['name'], create_postargs['name'], msg='Failed to create entity with matching name')

        # Read
        response, content = self.read_helper(endpoint, create_postargs['name'])
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['name'], create_postargs['name'], msg='Failed to create entity with matching name')

        for field in schema:
            if field in create_postargs:
                self.assertEqual(payload['entry'][0]['content'][field], create_postargs[field].strip(), msg='Failed to created entity with matching field: %s' % field)
            else:
                if field == 'label':
                    if create_postargs['type'] == 'inline':
                        self.assertEqual(payload['entry'][0]['content'][field], create_postargs['name'].strip(),
                                             msg='Failed to create entity with matching field: %s' % field)
                    if create_postargs['type'] == 'template':
                        # label is not in create postargs label should be the search template name
                        self.assertEqual(payload['entry'][0]['content'][field], self.searchtemplate1name,
                                             msg='Failed to create entity with matching field: %s' % field)
                    continue

                if field in environment_searches_schema.OPTIONAL_FIELDS:
                    continue

                self.assertEqual(payload['entry'][0]['content'][field], default_postargs[field].strip(),
                                 msg='Failed to create entity with matching field: %s' % field)

        # Delete HEC token
        hec_token_eai_response_payload = self.simple_request_delete(payload['entry'][0]['content']['hec_token_link_alternate'])

        # Delete Saved Searches
        saved_search_eai_response_payload = self.simple_request_delete(payload['entry'][0]['content']['savedsearch_link_alternate'])

        # Delete Environment Search
        response, content = self.delete_helper(endpoint, create_postargs['name'])
        self.assertEqual(response['status'], '200', msg='deleted entity with correct status code')
        retrieved_entity_after_delete = True
        try:
            response, content = self.read_helper(endpoint, create_postargs['name'])
        except Exception as e:
            retrieved_entity_after_delete = False
        self.assertFalse(retrieved_entity_after_delete, msg='could not retrieve non existent entity')


    def test_template_default_no_edit(self):
        create_postargs = {
            'name': self.name,
            'label': 'A Label',
            'environment_link_alternate': self.env1_link_alternate,
            'search': self.search_template1_link_alt,
            'type': 'template',
        }

        self.full_crud_test_helper(endpoint=endpoint, create_postargs=create_postargs,
                                   default_postargs=default_postargs, schema=environment_searches_schema.ALL_FIELDS)

    def test_template_default_no_label_no_edit(self):
        create_postargs = {
            'name': self.name,
            'environment_link_alternate': self.env1_link_alternate,
            'search': self.search_template1_link_alt,
            'type': 'template',
        }

        self.full_crud_test_helper(endpoint=endpoint, create_postargs=create_postargs,
                                   default_postargs=default_postargs, schema=environment_searches_schema.ALL_FIELDS)

    def test_inline_default_w_edit(self):
        create_postargs = {
            'name': self.name,
            'label': 'A Label',
            'environment_link_alternate': self.env1_link_alternate,
            'search': 'nothing',
            'type': 'inline',
        }

        update_postargs = {
            'environment_link_alternate': self.env1_link_alternate,
            'label': 'A Label changed',
            'search': '| updated | search "Test"',
            'interval': '240',
            'disabled': 'True',
            'type': 'inline',
        }

        self.full_crud_test_helper(endpoint=self.endpoint, create_postargs=create_postargs, update_postargs=update_postargs, default_postargs=self.default_postargs, schema=environment_searches_schema.ALL_FIELDS)

    def test_template_default_w_edit(self):
        create_postargs = {
            'name': self.name,
            'label': self.searchtemplate1name,
            'environment_link_alternate': self.env1_link_alternate,
            'search':  self.search_template1_link_alt,
            'type': 'template',
        }

        update_postargs = {
            'environment_link_alternate': self.env1_link_alternate,
            'label': self.searchtemplate2name,
            'search': self.search_template2_link_alt,
            'interval': '240',
            'disabled': 'True',
            'type': 'template',
        }

        self.full_crud_test_helper(endpoint=self.endpoint, create_postargs=create_postargs, update_postargs=update_postargs, default_postargs=self.default_postargs,
                                   schema=environment_searches_schema.ALL_FIELDS)

    def test_template_default_w_edit_w_switch(self):
        create_postargs = {
            'name': self.name,
            'label': 'A Label',
            'environment_link_alternate': self.env1_link_alternate,
            'search': self.search_template1_link_alt,
            'type': 'template',
        }

        update_postargs = {
            'environment_link_alternate': self.env1_link_alternate,
            'label': 'A Label changed',
            'search': self.search_template1_link_alt,
            'interval': '240',
            'disabled': 'True',
            'type': 'inline',
        }

        self.full_crud_test_helper(endpoint=self.endpoint, create_postargs=create_postargs,
                                   update_postargs=update_postargs, default_postargs=self.default_postargs,
                                   schema=environment_searches_schema.ALL_FIELDS)

    def test_inline_default_w_edit_w_switch(self):
        create_postargs = {
            'name': self.name,
            'label': 'A Label',
            'environment_link_alternate': self.env1_link_alternate,
            'search': 'basic',
            'type': 'inline',
        }

        update_postargs = {
            'environment_link_alternate': self.env1_link_alternate,
            'label': self.searchtemplate1name,
            'search': self.search_template1_link_alt,
            'interval': '240',
            'disabled': 'True',
            'type': 'template',
        }

        self.full_crud_test_helper(endpoint=self.endpoint, create_postargs=create_postargs,
                                   update_postargs=update_postargs, default_postargs=self.default_postargs,
                                   schema=environment_searches_schema.ALL_FIELDS)

    def test_template_default_no_label_w_edit(self):
        create_postargs = {
            'name': self.name,
            'environment_link_alternate': self.env1_link_alternate,
            'search': self.search_template1_link_alt,
            'type': 'template',
        }

        update_postargs = {
            'environment_link_alternate': self.env1_link_alternate,
            'search': self.search_template1_link_alt,
            'interval': '240',
            'disabled': 'True',
            'type': 'template',
        }

        self.full_crud_test_helper(endpoint=self.endpoint, create_postargs=create_postargs, update_postargs=update_postargs, default_postargs=self.default_postargs, schema=environment_searches_schema.ALL_FIELDS)

    def test_override_defaults_no_edit(self):
        create_postargs = {
            'name': self.name,
            'label': 'A Label',
            'environment_link_alternate': self.env1_link_alternate,
            'search': 'placeholder',
            'interval': '240',
            'disabled': 'True',
            'type': 'inline',
        }


        self.full_crud_test_helper(endpoint=self.endpoint, create_postargs=create_postargs, default_postargs=self.default_postargs, schema=environment_searches_schema.ALL_FIELDS)

    def test_override_defaults_w_edit(self):
        create_postargs = {
            'name': self.name,
            'label': 'A Label',
            'environment_link_alternate': self.env1_link_alternate,
            'search': 'placeholder',
            'interval': '240',
            'disabled': 'True',
            'type': 'inline',
        }

        update_postargs = {
            'label': 'A Label',
            'environment_link_alternate': self.env1_link_alternate,
            'search': '| updated | search "Test"',
            'interval': '300',
            'disabled': 'False',
            'type': 'inline',
        }

        self.full_crud_test_helper(endpoint=self.endpoint, create_postargs=create_postargs, update_postargs=update_postargs, default_postargs=self.default_postargs, schema=environment_searches_schema.ALL_FIELDS)

    #### INVALID TEST CASES ####

    def test_create_invalid_params(self):
        # Create a valid search then pass a bunch of invalid edits
        base_postargs = {
            'name': self.name,
            'environment_link_alternate': self.env1_link_alternate,
            'search': 'initial',
            'type': 'inline',
        }

        # Invalid name
        postargs_invalid_name = base_postargs.copy()
        postargs_invalid_name['name'] = ''
        response, content = self.create_helper(endpoint=self.endpoint, postargs=postargs_invalid_name)
        # this looks like something being thrown by the generic conf handler and should be caught by our validator
        self.assertEqual(response['status'], '400', msg='failed due to missing name')

        # Missing environment_link_alternate
        postargs_missing_environment_link_alternate = base_postargs.copy()
        postargs_missing_environment_link_alternate['environment_link_alternate'] = ''
        response, content = self.create_helper(endpoint=self.endpoint, postargs=postargs_missing_environment_link_alternate)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to missing environment_link_alternate')

        # Invalid environment_link_alternate
        postargs_invalid_environment_link_alternate = base_postargs.copy()
        postargs_invalid_environment_link_alternate['environment_link_alternate'] = 'htp://foo.com'
        response, content = self.create_helper(endpoint=self.endpoint, postargs=postargs_invalid_environment_link_alternate)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to invalid environment_link_alternate')

        # Invalid argument
        postargs_invalid_argument = base_postargs.copy()
        postargs_invalid_argument['blah'] = 'htp://foo.com'
        response, content = self.create_helper(endpoint=self.endpoint, postargs=postargs_invalid_argument)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '400', msg='failed due to invalid argument')

        # Invalid disabled
        postargs_disabled = base_postargs.copy()
        postargs_disabled['disabled'] = 'Tr'
        response, content = self.create_helper(endpoint=self.endpoint, postargs=postargs_disabled)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to invalid disabled')

        # Invalid interval
        postargs_interval = base_postargs.copy()
        postargs_interval['interval'] = 'Foo'
        response, content = self.create_helper(endpoint=self.endpoint, postargs=postargs_interval)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to invalid interval')

        # Invalid index
        postargs_index = base_postargs.copy()
        postargs_index['index_link_alternate'] = ' '
        response, content = self.create_helper(endpoint=self.endpoint, postargs=postargs_index)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to missing index')

        # Invalid search_string
        postargs_search_string = base_postargs.copy()
        postargs_search_string['search'] = ' '
        response, content = self.create_helper(endpoint=self.endpoint, postargs=postargs_search_string)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to missing search')

    def test_edit_invalid_params(self):
        base_postargs = {
            'name': self.name,
            'label': 'A Label',
            'environment_link_alternate': self.env1_link_alternate,
            'search': 'basic',
            'type': 'inline',
        }

        base_edit_postargs = {
            'label': 'A Label',
            'environment_link_alternate': self.env1_link_alternate,
            'interval': '60',
            'search': '| updated | search "Test"',
            'type': 'inline',
        }

        response, content = self.create_helper(endpoint, base_postargs)
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['name'], self.name,
                         msg='Failed to create entity with matching name')

        # Invalid name
        postargs_invalid_name = base_edit_postargs.copy()
        response, content = self.edit_helper(endpoint=self.endpoint, name='', postargs=postargs_invalid_name)
        # this looks like something being thrown by the generic conf handler and should be caught by our validator
        self.assertEqual(response['status'], '400', msg='failed due to missing name')

        # Invalid environment_link_alternate
        postargs_invalid_mgmt_scheme_host_port = base_edit_postargs.copy()
        postargs_invalid_mgmt_scheme_host_port['environment_link_alternate'] = ''
        response, content = self.edit_helper(endpoint=self.endpoint, name=self.name,
                                             postargs=postargs_invalid_mgmt_scheme_host_port)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to missing environment_link_alternate')

        # Invalid environment_link_alternate
        postargs_invalid_mgmt_scheme_host_port = base_edit_postargs.copy()
        postargs_invalid_mgmt_scheme_host_port['environment_link_alternate'] = 'htp://foo.com'
        response, content = self.edit_helper(endpoint=self.endpoint, name=self.name,
                                             postargs=postargs_invalid_mgmt_scheme_host_port)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500',
                         msg='failed due to invalid argument environment_link_alternate')

        # Missing type
        postargs_missing_type = base_edit_postargs.copy()
        del postargs_missing_type['type']
        response, content = self.edit_helper(endpoint=self.endpoint, name=self.name,
                                             postargs=postargs_missing_type)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to missing type')

        # Invalid argument
        postargs_invalid_mgmt_scheme_host_port = base_edit_postargs.copy()
        postargs_invalid_mgmt_scheme_host_port['mgmt_scheme_host_port'] = 'htp://foo.com'
        response, content = self.edit_helper(endpoint=self.endpoint, name=self.name,
                                             postargs=postargs_invalid_mgmt_scheme_host_port)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '400', msg='failed due to invalid argument mgmt_scheme_host_port')

        # Invalid disabled
        postargs_disabled = base_edit_postargs.copy()
        postargs_disabled['disabled'] = 'Tr'
        response, content = self.edit_helper(endpoint=self.endpoint, name=self.name, postargs=postargs_disabled)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to invalid disabled')

        # Invalid interval
        postargs_interval = base_edit_postargs.copy()
        postargs_interval['interval'] = 'Foo'
        response, content = self.edit_helper(endpoint=self.endpoint, name=self.name, postargs=postargs_interval)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to invalid interval')

        # Invalid index
        postargs_index = base_edit_postargs.copy()
        postargs_index['index_link_alternate'] = ' '
        response, content = self.edit_helper(endpoint=self.endpoint, name=self.name, postargs=postargs_index)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to missing index')

        # Invalid lookup
        postargs_lookup = base_edit_postargs.copy()
        postargs_lookup['lookup_link_alternate'] = ' '
        response, content = self.edit_helper(endpoint=self.endpoint, name=self.name, postargs=postargs_lookup)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '500', msg='failed due to missing lookup')

        # Invalid search_string
        postargs_search_string = base_edit_postargs.copy()
        postargs_search_string['search'] = ' '
        response, content = self.create_helper(endpoint=self.endpoint, postargs=postargs_search_string)
        # this looks like an invalid error code
        self.assertEqual(response['status'], '400', msg='failed due to missing search')

        # Read (ensure no changes)
        response, content = self.read_helper(endpoint=self.endpoint, name=self.name)
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['name'], self.name,
                         msg='Name of entity changed after invalid edits')
        for field in environment_searches_schema.ALL_FIELDS:
            if field in base_postargs:
                self.assertEqual(payload['entry'][0]['content'][field], base_postargs[field].strip(),
                                 msg='Field: %s of entity changed after invalid edits' % field)
            else:
                if field in environment_searches_schema.OPTIONAL_FIELDS:
                    continue
                self.assertEqual(payload['entry'][0]['content'][field], default_postargs[field].strip(),
                                 msg='Field: %s of entity changed after invalid edits' % field)

        # Delete
        response, content = self.delete_helper(endpoint=self.endpoint, name=self.name)
        self.assertEqual(response['status'], '200', msg='deleted entity with correct status code')
        retrieved_entity_after_delete = True
        try:
            response, content = self.read_helper(endpoint=self.endpoint, name=self.name)
        except Exception as e:
            retrieved_entity_after_delete = False
        self.assertFalse(retrieved_entity_after_delete, msg='could not retrieve non existent entity')

    def test_delete_whitespace_search_name(self):
        create_postargs = {
            'name': self.name + " with space",
            'label': 'A Label',
            'environment_link_alternate': self.env1_link_alternate,
            'search': 'basic',
            'type': 'inline',
        }

        update_postargs = {
            'environment_link_alternate': self.env1_link_alternate,
            'label': 'A Label',
            'interval': '60',
            'search': '| updated | search "Test"',
            'type': 'inline',
        }

        self.full_crud_test_helper(endpoint=self.endpoint, create_postargs=create_postargs,
                                   update_postargs=update_postargs, default_postargs=self.default_postargs,
                                   schema=environment_searches_schema.ALL_FIELDS)

    def test_edit_invalid_name(self):
        # Edit a nonexistent search
        magic_search_name = "THIS_SEARCH_SHOULD_NEVER_EXIST"
        base_postargs = {
            'environment_link_alternate': self.env1_link_alternate,
            'label': 'A Label',
            'search': 'basic',
            'type': 'inline',
        }

        # Invalid name
        postargs_invalid_name = base_postargs.copy()
        postargs_invalid_name['interval'] = '360'
        response, content = self.edit_helper(endpoint=self.endpoint, name=magic_search_name, postargs=postargs_invalid_name)
        # this looks like something being thrown by the generic conf handler and should be caught by our validator
        self.assertEqual(response['status'], '500', msg='Did not fail despite nonexistent name')

    def test_delete_invalid_name(self):
        # Delete an nonexistent search
        magic_index_name = "THIS_INDEX_SHOULD_NEVER_EXIST"
        # Delete
        response, content = self.delete_helper(endpoint=self.endpoint, name=magic_index_name)
        self.assertEqual(response['status'], '500', msg='Handler thinks index exists')
        retrieved_entity_after_delete = True
        try:
            response, content = self.read_helper(endpoint=self.endpoint, name=magic_index_name)
        except Exception as e:
            retrieved_entity_after_delete = False
        self.assertFalse(retrieved_entity_after_delete, msg='Entity was somehow created')

    #### TESTING UTILS ####

    def full_crud_test_helper(self, endpoint, create_postargs, schema, default_postargs, update_postargs=None):
        # List
        response, content = self.list_helper(endpoint)
        payload = json.loads(content)
        self.assertTrue(isinstance(payload['entry'], list), msg='List does not return list type')

        # Create
        response, content = self.create_helper(endpoint, create_postargs)
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['name'], create_postargs['name'], msg='Failed to create entity with matching name')

        # Read
        response, content = self.read_helper(endpoint, create_postargs['name'])
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['name'], create_postargs['name'], msg='Failed to create entity with matching name')

        for field in schema:
            if field in create_postargs:
                self.assertEqual(payload['entry'][0]['content'][field], create_postargs[field].strip(), msg='Failed to created entity with matching field: %s' % field)
            else:
                if field == 'label':
                    if create_postargs['type'] == 'inline':
                        self.assertEqual(payload['entry'][0]['content'][field], create_postargs['name'].strip(),
                                             msg='Failed to create entity with matching field: %s' % field)
                    if create_postargs['type'] == 'template':
                        # label is not in create postargs label should be the search template name
                        self.assertEqual(payload['entry'][0]['content'][field], self.searchtemplate1name,
                                             msg='Failed to create entity with matching field: %s' % field)
                    continue

                if field in environment_searches_schema.OPTIONAL_FIELDS:
                    continue

                self.assertEqual(payload['entry'][0]['content'][field], default_postargs[field].strip(),
                                 msg='Failed to create entity with matching field: %s' % field)

        if update_postargs:
            # Update
            response, content = self.edit_helper(endpoint, create_postargs['name'], update_postargs)
            payload = json.loads(content)
            self.assertEqual(payload['entry'][0]['name'], create_postargs['name'],
                             msg='Failed to create entity with matching name')

            # Read
            response, content = self.read_helper(endpoint, create_postargs['name'])
            payload = json.loads(content)
            for field in schema:
                if field in update_postargs:
                    self.assertEqual(payload['entry'][0]['content'][field], update_postargs[field].strip(),
                                         msg='Failed to create entity with matching field: %s' % field)
                else:
                    if field == 'label' and update_postargs['type'] == 'template':
                        # label is missing. label should be template name
                        self.assertEqual(payload['entry'][0]['content'][field], self.searchtemplate1name,
                                         msg='Failed to create entity with matching field: %s' % field)
                        continue
                    if field in environment_searches_schema.OPTIONAL_FIELDS:
                        continue
                    self.assertEqual(payload['entry'][0]['content'][field], default_postargs[field].strip(),
                                     msg='Failed to create entity with matching field: %s' % field)

        # Delete
        response, content = self.delete_helper(endpoint, create_postargs['name'])
        self.assertEqual(response['status'], '200', msg='deleted entity with correct status code')
        retrieved_entity_after_delete = True
        try:
            response, content = self.read_helper(endpoint, create_postargs['name'])
        except Exception as e:
            retrieved_entity_after_delete = False
        self.assertFalse(retrieved_entity_after_delete, msg='could not retrieve non existent entity')

    def create_environment(self):
        environment_postargs = {
            'name': self.name,
            'mgmt_scheme_host_port': ' https://localhost:8090 ',
            'username': ' admin ',
            'password': ' changed ',
        }
        response, content = self.create_helper('environments', environment_postargs)
        payload = json.loads(content)
        self.assertEqual(payload['entry'][0]['name'], self.name, msg='created entity with matching name')
        self.assertEqual(payload['entry'][0]['content']['mgmt_scheme_host_port'],
                         environment_postargs['mgmt_scheme_host_port'].strip(),
                         msg='created entity with matching mgmt_scheme_host_port and stripped whitespace')
        self.assertEqual(payload['entry'][0]['content']['username'], environment_postargs['username'].strip(),
                         msg='created entity with matching username and stripped whitespace')

        return payload['entry'][0]['links']['alternate']

    def create_search_template(self, postargs):
        search_templates_path = '/servicesNS/%s/%s/configs/conf-%s' % ('nobody', 'mothership', 'environment_search_templates')

        # TODO Error handling/asserts...
        response, content = self.template_create_helper(search_templates_path, postargs)

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
