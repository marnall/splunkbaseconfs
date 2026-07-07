import dbx_connection_diag
import getpass
import pytest
from unittest.mock import patch

@patch("getpass.getpass")
def test_dbx_connection_diag_mssql_success(getpass, capsys):
	input_values = ["admin",0,2,"n","y","q"]
	pass_values = ["Chang3d!"]

	def mock_input(s):
		return input_values.pop(0)
	def mock_pass(s):
		return pass_values.pop(0)

	getpass.return_value = pass_values.pop(0)
	dbx_connection_diag.input = mock_input
	
	dbx_connection_diag.main()
	out, err = capsys.readouterr()
	validConnectionString = "This connection appears to valid!"
	assert validConnectionString in out

@patch("getpass.getpass")
def test_dbx_connection_diag_mssql_bad_port(getpass,capsys):
	input_values = ["admin",3,2,"n","y"]
	pass_values = ["Chang3d!"]

	def mock_input(s):
		return input_values.pop(0)

	with pytest.raises(SystemExit) as pytest_wrapped_e:
		getpass.return_value = pass_values.pop(0)
		dbx_connection_diag.input = mock_input
		dbx_connection_diag.main()
	
	resolutionString = "Make sure the server is up, and you have access to it (not blocked by a firewall for example"
	out, err = capsys.readouterr()
	print(out)
	assert resolutionString in out

@patch("getpass.getpass")
def test_dbx_connection_diag_mssql_bad_database(getpass,capsys):
	input_values = ["admin",7,2,"n","y","q"]
	pass_values = ["Chang3d!"]

	def mock_input(s):
		return input_values.pop(0)

	getpass.return_value = pass_values.pop(0)
	dbx_connection_diag.input = mock_input
	dbx_connection_diag.main()
	out, err = capsys.readouterr()
	diagnosisString = "com.microsoft.sqlserver.jdbc.SQLServerException: Cannot open database"
	assert diagnosisString in out