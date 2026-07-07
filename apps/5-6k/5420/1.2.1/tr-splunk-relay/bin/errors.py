from http import HTTPStatus


class ShellError(Exception):
    def __init__(self, message):
        self.message = message


class ApiClientError(Exception):
    def __init__(self, status, message):
        self.status_code = status
        self.message = message


class DeviceAlreadyExists(ApiClientError):
    def __init__(self):
        super().__init__(
            HTTPStatus.BAD_REQUEST,
            'Your device already exist.'
        )


class ConnectorNotFound(ApiClientError):
    def __init__(self):
        super().__init__(
            HTTPStatus.NOT_FOUND,
            'SSE Connector not launched on localhost:<your_port>.'
            'Please check if the port is correct, or run SSE Connector.'
        )


class ConnectorClientError(Exception):
    def __init__(self, message):
        self.message = message


class NotSupportedAction(ConnectorClientError):
    def __init__(self, action, supported_actions):
        super().__init__(
            f'<{action}> is not supported. Please choose one '
            f'of the supported actions: {supported_actions}'
        )


class ConnectorAlreadyLaunched(ConnectorClientError):
    def __init__(self):
        super().__init__(
            'SSE Connector already launched.'
        )
