import json
from functools import wraps

from api.errors import BadRequest  # noqa
from constants import API_RESPONSE_HEADERS


def post(method):
    """Decorates a method to handle POST requests."""

    def response(payload, code):
        return {
            'payload': json.dumps(payload),
            'code': code,
            'headers': API_RESPONSE_HEADERS
        }

    def error(**kwargs):
        return {
            'errors': [{'type': 'fatal', **kwargs}],
            'headers': API_RESPONSE_HEADERS
        }

    @wraps(method)
    def decorated(self, request):
        try:
            request = json.loads(request)

            if request.get('method') != 'POST':
                return response({'message': 'Method not allowed.'},
                                code=405)

            result = method(self, request)

            if isinstance(result, tuple):
                return response(*result)
            else:
                return response(result, code=200)

        except BadRequest:
            payload = error(
                code='bad request',
                message='The body of a request has an invalid format.'
            )

            return response(payload, 200)

        except Exception as ex:
            payload = error(
                code='oops',
                message='Something went wrong.'
            )

            if hasattr(ex, 'data'):
                payload.update(ex.data)

            return response(payload, 200)

    return decorated
