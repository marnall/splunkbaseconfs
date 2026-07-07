import sqlite3
from datetime import datetime, timedelta

class SentryWireStore:
    def __init__(self, database: str = 'sentrywire.local.db', max_saved_searches: int = 25):
        """Create a local database and populate it with tables for user search storage

        Args:
            database (str, optional): The name of the database file. Defaults to 'sentrywire.local.db'.
            max_saved_searches (int, optional): Maximum number of saved searches per user. Defaults to 25.
        """
        self._db = database
        self._init_search_store()
        self._max_saved_searches = max_saved_searches

    def _init_search_store(self) -> None:
        """Creates saved searches table
        """
        conn = sqlite3.connect(self._db)
        with conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS SearchStore (
                    search_id TEXT PRIMARY KEY,
                    splunk_user TEXT NOT NULL,
                    search_filter TEXT,
                    begin_time DATETIME,
                    end_time DATETIME,
                    submitted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    check_status_link TEXT,
                    get_pcaps_link TEXT,
                    metadata_link TEXT,
                    objects_link TEXT
                )
                ''')
            conn.commit()
    
    # SearchStore Functions
    def get_searches(self, splunk_user: str) -> list:
        """Retrieve a list of searches that the user has submitted.
        Args:
            splunk_user (str): Unique id

        Returns:
            list: Search history
        """
        entries = []
        conn = sqlite3.connect(self._db)
        with conn:
            cursor = conn.cursor()
            query = '''
            SELECT * 
            FROM SearchStore 
            WHERE splunk_user = ?
            '''
            cursor.execute(query, (splunk_user,))
            entries = cursor.fetchall()
        return entries


    def store_search(self, splunk_user: str, search_id: str, search_filter: str, begin_time: datetime, end_time: datetime, check_status_link: str, get_pcaps_link: str, metadata_link: str, objects_link: str) -> None:
        """Store search in user's search history

        Args:
            splunk_user (str): Unique id
            search_id (str): Unique id provided as part of the SentryWire search result
            search_filter (str): Search filter used for search 
            begin_time (datetime): Begin time used for search 
            end_time (datetime): End time used for search 

        Raises:
            LookupError: User wasn't created in the TokenStore prior to trying to store the search.
        """
        conn = sqlite3.connect(self._db)
        with conn:
            cursor = conn.cursor()
            query = '''
            INSERT INTO SearchStore (search_id, splunk_user, search_filter, begin_time, end_time, check_status_link, get_pcaps_link, metadata_link, objects_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            cursor.execute(query, (search_id, splunk_user, search_filter, begin_time, end_time, check_status_link, get_pcaps_link, metadata_link, objects_link))

    def remove_expired(self, splunk_user: str):
        """Removes searches if a user's max saved searches is reached

        Args:
            splunk_user (str): Unique id
        """
        searches = self.get_searches(splunk_user)
        r_index = len(searches)
        if r_index > self._max_saved_searches:
            to_remove = searches[0:r_index - self._max_saved_searches]
            conn = sqlite3.connect(self._db)
            with conn:
                cursor = conn.cursor()
                for search in to_remove:
                    query = '''
                    DELETE FROM SearchStore
                    WHERE search_id = ?
                    '''
                    cursor.execute(query, (search[0],))
                conn.commit()