class StateRefresh(object):
    def __init__(self, refresh_rate_days, check_point_name, collection_name):
        self.refresh_rate_days = refresh_rate_days
        self.check_point_name = check_point_name
        self.collection_name = collection_name
