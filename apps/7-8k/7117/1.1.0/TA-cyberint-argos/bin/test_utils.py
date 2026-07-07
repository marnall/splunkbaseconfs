import datetime
from unittest.mock import mock_open, patch

import pytest
import pytz

# def load_mock_response(file_name: str) -> str:
#     """
#     Load mock file that simulates an API response.
#     Args:
#         file_name (str): Name of the mock response JSON file to return.
#     Returns:
#         str: Mock file content.
#     """
#     file_path = os.path.join("test_data", file_name)
#     with open(file_path, mode="r", encoding="utf-8") as mock_file:
#         return json.loads(mock_file.read())


# @pytest.fixture(autouse=True)
# def mock_client(version: str) -> Client:
#     """Create a test client for V1/V2.

#     Args:
#         version (str): Version (V1/V2).

#     Returns:
#         Client: Fortieweb VM Client.
#     """
#     client_class = ClientV1 if version == ClientV1.API_VER else ClientV2
#     client: Client = client_class("http://1.1.1.1/", "usn", "pwd", version, True, False)
#     return client


def test_remove_empty_elements():
    """
    Scenario: Create a Protected hostname group.
    Given:
     - User has provided correct parameters.
    When:
     - fortiwebvm-protected-hostname-group-create called.
    Then:
     - Ensure that Protected hostname created.
    """
    from utils import remove_empty_elements

    data = {"types": None, "severities": "low|high"}
    result = remove_empty_elements(data)
    assert result == {"severities": "low|high"}


@pytest.mark.parametrize(
    ("time_frame", "expected"),
    (
        ("last_1h", "1999-12-31T23:00:00"),
        ("last_24h", "1999-12-31T00:00:00"),
        ("last_7d", "1999-12-25T00:00:00"),
        ("last_30d", "1999-12-02T00:00:00"),
        ("last_90d", "1999-10-03T00:00:00")
    ),
)
def test_convert_time_frame_to_utc(time_frame: str, expected: str):
    from utils import convert_time_frame_to_utc

    fixed_datetime = datetime.datetime(2000, 1, 1, tzinfo=pytz.utc)

    # Mock datetime.datetime
    with patch('datetime.datetime') as mock_datetime:
        # Create a mock for datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        mock_utcnow = mock_datetime.utcnow.return_value
        mock_utcnow.replace.return_value = fixed_datetime

        result = convert_time_frame_to_utc(time_frame=time_frame)

        assert result == expected


@patch('builtins.open', new_callable=mock_open, read_data='{"key": "value"}')
def test_load_checkpoint_valid_file(mock_file_open):
    from utils import load_checkpoint
    result = load_checkpoint(file_path='input_name.json')

    assert result == {"key": "value"}


@patch('builtins.open', side_effect=FileNotFoundError)
def test_load_checkpoint_not_exist_file(mock_file_open):
    from utils import load_checkpoint

    result = load_checkpoint(file_path='input_name.json')

    assert result is None


@patch('builtins.open', new_callable=mock_open, read_data=b'test')
def test_load_checkpoint_error(mock_file_open):
    from utils import load_checkpoint
    result = load_checkpoint(file_path='input_name.json')

    assert result is None


@pytest.mark.parametrize(
    ("date", "expected"),
    (
        ("1999-12-31T23:00:00", True),
        ("1999-12-91T23:00:00", False),
        ("1999-42-31T02:00:00", False),
        ("1999e-42-31T02:00:00", False),
        ("1999-12-3123:00:00", False)
    ),
)
def test_is_valid_date(date: str, expected: bool):
    from utils import is_valid_date

    result = is_valid_date(str_date=date)

    assert result == expected
