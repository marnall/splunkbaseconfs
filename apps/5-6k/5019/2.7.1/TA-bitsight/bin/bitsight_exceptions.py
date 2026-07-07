class BitsightException(Exception):
    """Bitsight custom exception class."""

    def __init__(self, *args):
        """Init method."""
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        """Override output function."""
        if self.message:
            msg = "Bitsight Exception: {0} ".format(self.message)
        else:
            msg = "An unxepected error occurred while collecting Bitsight data."
        return msg
