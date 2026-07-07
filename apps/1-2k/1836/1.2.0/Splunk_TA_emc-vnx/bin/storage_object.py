"""
Base stuff for Storage
"""

from re import compile as reco


class VnxProxy(object):
    def __init__(self, name, value):
        setattr(self, name, value)


class StorageObject(object):
    """
    Base class for storage objects
    """

    def __init__(self, metric_time):
        self._metric_time = metric_time

    def _do_parse(self, output, rex):
        for name in rex:
            rex[name] = reco(rex[name])

        for lin in output:
            for name, value in self.__dict__.iteritems():
                if value is None:
                    match = rex[name].search(lin)
                    if match:
                        setattr(self, name, "_".join(match.groups()).strip())
                        break
                elif isinstance(value, list):
                    match = rex[name].search(lin)
                    if match:
                        val = "_".join(match.groups()).strip()
                        getattr(self, name).append(val)
                        break

    def _to_tag_value(self, timestamp, idx, sourcetype):
        evt_fmt = ("<event><time>%s</time><source>vnx</source>"
                   "<sourcetype>%s</sourcetype>"
                   "<index>%s</index><data>%s</data></event>")
        tag_vals = ",".join(("%s=%s" % (name, str(val))
                             for name, val in self.__dict__.iteritems()
                             if not name.startswith("_")))
        if getattr(self, "_agent", None):
            serial_no = "array_serial_no=%s" % self._agent.array_serial_no
        elif getattr(self, "_filer", None):
            serial_no = "nas_frame=%s" % self._filer.serial_no
        else:
            assert 0
        return evt_fmt % (self._metric_time, sourcetype, idx,
                          "%s,%s" % (tag_vals, serial_no))

    def is_valid(self):
        """
        @return: True if all properties are well populated, otherwise False
        """

        for _, value in self.__dict__.iteritems():
            if value is None:
                return False
        return True

    def _verify(self):
        """
        For debug only. Assert None properties
        """

        for name, value in self.__dict__.iteritems():
            if value is None:
                raise Exception("None value for %s" % name)
