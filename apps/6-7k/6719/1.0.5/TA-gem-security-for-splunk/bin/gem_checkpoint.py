class Checkpoint(object):
    def __init__(self, helper, name):
        self._helper = helper
        self._name = name

    @property
    def value(self):
        return self._helper.get_check_point(self._name)

    @value.setter
    def value(self, data):
        self._helper.log_debug("Saving checkpoint {}={}".format(self._name, data))
        self._helper.save_check_point(self._name, data)
