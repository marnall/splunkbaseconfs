import date as date_service


class KVStore:
    def __init__(self, helper):
        self._helper = helper

    def get(self, key):
        return self._helper.get_check_point(key)

    def put(self, key, value):
        self._helper.save_check_point(key, value)


class AppStore:
    START_DATE_KEY = 'start_date'
    END_DATE_KEY = 'end_date'
    CURRENT_POSITION_KEY = 'current_position'

    def __init__(self, store: KVStore):
        self._store = store

        start_date = self.get_start_date()
        if (start_date is None):
            start_date = date_service.two_weeks_ago()
            self._store.put(self.START_DATE_KEY, start_date)

        end_date = self.get_end_date()
        if (end_date is None):
            end_date = date_service.now()
            self._store.put(self.END_DATE_KEY, end_date)

        current_position = self.get_current_position()
        if (current_position is None or current_position < start_date):
            current_position = end_date
            self.set_current_position(current_position)

    def get_start_date(self):
        return self._store.get(self.START_DATE_KEY)

    def get_end_date(self):
        return self._store.get(self.END_DATE_KEY)

    def get_current_position(self):
        return self._store.get(self.CURRENT_POSITION_KEY)

    def set_current_position(self, timestamp):
        self._store.put(self.CURRENT_POSITION_KEY, timestamp)

    def success(self):
        self._store.put(self.START_DATE_KEY, self.get_end_date())
        self._store.put(self.END_DATE_KEY, None)
        self.set_current_position(None)
