"""
This module will take a JSON file and deserialize it into the KV store collection. This is designed
to import KV store collection exports into a Splunk install. Thus, you can populate a KV store
collection on a host using whatever tools you want, and then export it into an app so that it can
be included with your app.


Where do I put the data?
---------------------------------------------------------------------------------------------------
The data needs to be stored within the app in the data directory as a JSON file. Below is an
example of where the data must be to populate the collection "mycollection":

$SPLUNK_HOME/etc/apps/someapp/
   * data/
       * kvstore/
           * nobody/                      (the collection is to be populated for the nobody user)
               *  someapp/                (... and will be populated under the "someapp" context)
                   * mycollection.json    (the collection to be populated is "mycollection")


How do I make the JSON file?
---------------------------------------------------------------------------------------------------
You can dump the key store collections from the collections/data endppoint directly to a JSON file
and then include these JSON files into the app. Below is a curl example that dumps a collection:

    curl -k -u admin:changeme \
    https://localhost:8089/servicesNS/nobody/search/storage/collections/data/hosts \
    -o hosts.json


How do I use this module?
---------------------------------------------------------------------------------------------------
Here are the main functions on this module that you are most likely to use:

 1) load_data_for_app
    This loads the data for a particular app and is the most likely function that you will use.

 2) load_data_for_file
    This loads the data of a particular file.


What else should I know?
---------------------------------------------------------------------------------------------------

1) This is idempotent
   You can call these functions several times without harm.

2) This will not overwrite existing entries
   The script will ignore entries if a entry in the collection already exists with the same ID.
"""

import os
import json

import splunk.rest
from splunk import ResourceNotFound
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

class CollectionDoesntExistException(Exception):
    """
    An exception noting that the given collection doesn't exist.
    """
    pass

class KVStoreDeserializer(object):
    """
    This class takes a JSON file dump of a KV store collection and imports it.
    """

    @classmethod
    def load_data_for_app(cls, session_key, app, ignore_non_existent_collections=True, logger=None):
        """
        Load the JSON data within the given app to the KV store.
        """

        # Create the reference to the path were the data resides
        app_path = make_splunkhome_path(["etc", "apps", app, "default", "data", "kvstore"])

        # A counter of the number of rows imported
        imported_count = 0

        # traverse root directory, and list directories as dirs and files as files
        for root, dirs, files in os.walk(app_path):

            path = root.split(os.sep)

            for file_name in files:

                # Make sure this is a JSON file
                if not file_name.endswith(".json"):
                    if logger:
                        logger.info("File doesn't end with the extension; it will not be processed")
                    continue

                # Make sure this is in the correct directory
                if len(path) < 4 or path[-3] != 'kvstore':
                    continue

                # Get the app
                app = path[-1]

                # Get the owner
                owner = path[-2]

                # Get the collection name from the filename
                # The collection name is the filename without the extension
                # Thus, removing the extension results in the collection name
                collection = file_name[0:-5]

                # Get the full name of the file to import
                filename = os.path.join(root, file_name)

                # Perform the import on this file
                imported_count = imported_count + cls.load_data_for_file(session_key, filename,
                                                                         app, owner, collection,
                                                                         ignore_non_existent_collections,
                                                                         logger=logger)

        return imported_count

    @classmethod
    def load_data_for_file(cls, session_key, json_filename, app, owner, collection, ignore_non_existent_collections=True, logger=None):
        """
        Take the data from the given file and import it into the collection.

        This function returns the number of rows that were imported.
        """

        if logger:
            logger.info('Importing file="%s", app="%s", owner="%s", collection="%s"', json_filename, app, owner, collection)

        imported_count = 0

        # Make sure that the collection exists
        if not cls.does_collection_exist(session_key, owner, app, collection):

            # Ignore this collection if we are told to ignore these
            if ignore_non_existent_collections:
                if logger:
                    logger.info("Skipping import since the collection doesn't exist on this host, collection=%s, app=%s, owner=%s", app, owner, collection)

                return 0

            else:
                raise CollectionDoesntExistException("the collection doesn't exist on this host, collection=%s, app=%s, owner=%s" % (app, owner, collection))
        else:

            # Load the contents of the file
            with open(json_filename, 'r') as collection_file:
                collection_file_str = collection_file.read()

                # Parse the JSON
                collection_data = json.loads(collection_file_str)

                for row in collection_data:

                    # Do the post against the endpoint
                    if cls.populate_kv_collection(session_key, owner, app, collection, row, logger):
                        imported_count = imported_count + 1

            return imported_count

    @classmethod
    def does_collection_exist(cls, session_key, owner, app, collection):
        """
        Return a boolean indicating if the KV store collection exists.
        """

        try:
            splunk.rest.simpleRequest('/servicesNS/' + owner + '/' + app +
                                      '/storage/collections/config/' + collection,
                                      sessionKey=session_key,
                                      getargs={'output_mode': 'json'})

            # If we got here, then the exception wasnt thrown and thus the collection exists
            return True

        except ResourceNotFound:
            return False

    @classmethod
    def is_collection_empty(cls, session_key, owner, app, collection, logger):
        # See if the collection has any rows
        _, content = splunk.rest.simpleRequest('/servicesNS/' + owner + '/' + app +
                                                      '/storage/collections/data/' + collection,
                                                      sessionKey=session_key,
                                                      getargs={
                                                          'output_mode': 'json',
                                                          'limit': 1
                                                      })

        # Parse the response
        parsed_response = json.loads(content)

        if len(parsed_response) == 0:
            if logger:
                logger.info("Collection is not empty, collection=%s", collection)
            return True
        else:
            if logger:
                logger.info("Collection is empty, collection=%s", collection)
            return False

    @classmethod
    def populate_kv_collection(cls, session_key, owner, app, collection, data, logger):
        """
        Populate the KV store collection with thge given row.

        This will raise an exception if the collections endpoint reports an error.

        This function will return true if the entry was imported and false if the row was not
        imported because it already existed.
        """

        # Parse the input
        jsonargs = json.dumps(data)

        # Do the import
        response, content = splunk.rest.simpleRequest('/servicesNS/' + owner + '/' + app +
                                                      '/storage/collections/data/' + collection,
                                                      jsonargs=jsonargs,
                                                      sessionKey=session_key,
                                                      getargs={'output_mode': 'json'})

        # Get the ID
        entry_id = data.get('_key', 'undefined')

        # Handle the case where the row already existed
        if response.status == 409:

            if logger:
                logger.debug('Row already existed and thus will be skipped, key="%s", app="%s", \
                             owner="%s", collection="%s"', entry_id, app, owner, collection)

            return False # Was not imported

        # Handle the case where the import failed
        elif response.status != 200 and response.status != 201:
            raise Exception("Unable to make the collection entry (response_code=%r)"
                            % (response.status))

        # Handle the case where the import was successful
        else:

            # Parse the response
            parsed_response = json.loads(content)

            # Parse out the ID from the response
            entry_id = parsed_response.get('_key', 'undefined')

            if logger:
                logger.debug('Row created, key="%s", app="%s", owner="%s", collection="%s"',
                             entry_id, app, owner, collection)

            return True # Was imported
