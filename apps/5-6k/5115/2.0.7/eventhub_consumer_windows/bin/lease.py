from azure.eventprocessorhost.lease import Lease


class FileLease(Lease):
    def __init__(self):
        super()
        Lease.__init__(self)
        self.offset = None

    def serializable(self):
        """
        Returns serializable instance of `__dict__`.
        """
        return self.__dict__.copy()
