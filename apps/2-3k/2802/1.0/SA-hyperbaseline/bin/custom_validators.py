from splunklib.searchcommands.validators import Validator

class Float(Validator):
    """ Validates Float option values.
    """

    def __call__(self, value):
        try:
            value
        except NameError:
            value = None
        if value is not None:
            try:
                value = float(value)
            except ValueError:
                raise ValueError('Cannot convert value to float: %s' % value)
        return value

class OutlierMethod(Validator):
    """ Validates Boolean option values.
    """
    outlier_methods = ["ESD", "Hampel", "SBR", "ASBR"]

    def __call__(self, value):
        if value not in OutlierMethod.outlier_methods:
            raise ValueError('Unrecognized outlier method value: %s' % value)
        return value
