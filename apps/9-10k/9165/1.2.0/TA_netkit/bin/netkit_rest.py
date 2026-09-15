# Shared REST handler base: validate the payload before UCC's create/edit, surfacing a ValueError as HTTP 400.
try:
    import import_declare_test
except ImportError:
    pass

from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError


class ValidatingHandler(AdminExternalHandler):
    def _validate(self):
        raise NotImplementedError

    def _guard(self):
        try:
            self._validate()
        except ValueError as exc:
            raise RestError(400, str(exc))

    def handleCreate(self, confInfo):
        self._guard()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo):
        self._guard()
        AdminExternalHandler.handleEdit(self, confInfo)
