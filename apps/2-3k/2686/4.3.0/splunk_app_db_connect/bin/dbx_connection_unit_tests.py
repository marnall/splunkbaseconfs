#!/usr/bin/env python
# -*- coding: utf-8 -*-
# run as python3 -m unittest dbx_connection_unit_tests
import unittest
import dbx_connection_diag as troubleshoot
import csv

class TestDbxConnectionDiag(unittest.TestCase):

    def test_normalize_to_boolean(self):
        self.assertEqual(troubleshoot._normalize_to_boolean('1'), True)
        self.assertEqual(troubleshoot._normalize_to_boolean('yes'), True)
        self.assertEqual(troubleshoot._normalize_to_boolean('Yes'), True)
        self.assertEqual(troubleshoot._normalize_to_boolean('y'), True)
        self.assertEqual(troubleshoot._normalize_to_boolean('T'), True)
        self.assertEqual(troubleshoot._normalize_to_boolean('True'), True)
        self.assertEqual(troubleshoot._normalize_to_boolean('true'), True)

        self.assertEqual(troubleshoot._normalize_to_boolean('0'), False)
        self.assertEqual(troubleshoot._normalize_to_boolean('N'), False)

    def test_read_rulebook(self):
        path = 'rulebook.csv'

        db = 'oracle'
        msg = 'java.sql.SQLException: ORA-01017: invalid username/password; logon denied'
        diag = 'The database username/password is incorrect.'
        res = 'Please provide the correct database username and password'
        self.assertEqual(troubleshoot.read_rulebook(msg, db, path), (diag, res), "0. Failed for DB: "+db+" and error: "+msg)

        """ Remove comment after adding rules in the rulebook
        db = 'mysql'
        msg = 'java.sql.SQLException: No suitable driver found for jdbc:mysql://qa-centos7x64-035.sv.splunk.com:3307/sys'
        diag = 'Not yet entered in the rulebook'
        res = 'Not yet entered in the rulebook'
        self.assertEqual(troubleshoot.read_rulebook(msg, db, path), (diag, res), "1. Failed for DB: "+db+" and error: "+msg)

        db = 'mysql'
        msg = 'java.sql.SQLNonTransientConnectionException: Public Key Retrieval is not allowed'
        diag = 'Not yet entered in the rulebook'
        res = 'Not yet entered in the rulebook'
        self.assertEqual(troubleshoot.read_rulebook(msg, db, path), (diag, res),
                         "2. Failed for DB: " + db + " and error: " + msg)

        #mysql8 has a different error signature
        db = 'mysql'
        msg = "com.mysql.jdbc.exceptions.jdbc4.MySQLSyntaxErrorException: Unknown database 'sy'"
        diag = 'Not yet entered in the rulebook'
        res = 'Not yet entered in the rulebook'
        self.assertEqual(troubleshoot.read_rulebook(msg, db, path), (diag, res),
                         "3. Failed for DB: " + db + " and error: " + msg)

        db = 'mysql'
        msg = "com.mysql.jdbc.exceptions.jdbc4.CommunicationsException: Communications link failure \nThe last packet sent successfully to the server was 0 milliseconds ago. The driver has not received any packets from the server."
        diag = 'Not yet entered in the rulebook'
        res = 'Not yet entered in the rulebook'
        self.assertEqual(troubleshoot.read_rulebook(msg, db, path), (diag, res),
                         "4. Failed for DB: " + db + " and error: " + msg)

        db = 'mssql'
        msg = 'com.microsoft.sqlserver.jdbc.SQLServerException: Cannot open database "maste" requested by the login. The login failed. ClientConnectionId:8b3da9d6-fb51-4288-998f-b6fa1a1d31fa'
        diag = 'Not yet entered in the rulebook'
        res = 'Not yet entered in the rulebook'
        self.assertEqual(troubleshoot.read_rulebook(msg, db, path), (diag, res),
                         "5. Failed for DB: " + db + " and error: " + msg)

        db = 'mssql'
        msg = 'com.microsoft.sqlserver.jdbc.SQLServerException: The TCP/IP connection to the host qa-centos7x64-035, port 1433 has failed. Error: "qa-centos7x64-035. Verify the connection properties. Make sure that an instance of SQL Server is running on the host and accepting TCP/IP connections at the port. Make sure that TCP connections to the port are not blocked by a firewall."'
        diag = 'Not yet entered in the rulebook'
        res = 'Not yet entered in the rulebook'
        self.assertEqual(troubleshoot.read_rulebook(msg, db, path), (diag, res),
                         "6. Failed for DB: " + db + " and error: " + msg)

        db = 'oracle'
        msg = 'java.sql.SQLException: ORA-28009: connection as SYS should be as SYSDBA or SYSOPER'
        diag = 'Not yet entered in the rulebook'
        res = 'Not yet entered in the rulebook'
        self.assertEqual(troubleshoot.read_rulebook(msg, db, path), (diag, res),
                         "7. Failed for DB: " + db + " and error: " + msg)
        """
        with open(path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            i = 8
            for row in reader:
                db = row['DB']
                msg = row['Error']
                diag = row['Diagnosis']
                res = row['Resolution']
                self.assertEqual(troubleshoot.read_rulebook(msg, db, path), (diag, res), str(i)+". Failed for DB: "+db+" and error: "+msg)
                i = i+1


if __name__ == '__main__':
    unittest.main()
