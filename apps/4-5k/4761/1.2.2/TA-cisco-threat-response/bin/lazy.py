class Lazy(object):
    """
    Wraps a lazy object, i.e. the object does not even exist initially,
    but will be properly built and cached on first attribute access.
    """

    NONE = object()  # sentinel

    def __init__(self, builder, *args, **kwargs):
        self._builder = builder
        self._args = args
        self._kwargs = kwargs

        self._object = self.NONE

    @property
    def object(self):
        if self._object is self.NONE:
            self._object = self._build()

        return self._object

    def __getattr__(self, key):
        return getattr(self.object, key)

    def _build(self):
        return self._builder(*self._args, **self._kwargs)
