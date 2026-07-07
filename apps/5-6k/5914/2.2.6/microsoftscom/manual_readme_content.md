Windows Remote Management(WinRM) should be enabled on the MS SCOM Server for the app to run commands
remotely. To allow HTTP communication, WinRM config parameter **AllowUnencrypted** should be changed
to true on SCOM server.

By default WinRM HTTP uses port 80. On Windows 7 and higher the default port is 5985.\
By default WinRM HTTPS uses port 443. On Windows 7 and higher the default port is 5986.

This app uses NTLM authorization. The use of the HTTP_PROXY and HTTPS_PROXY environment variables is
currently unsupported.
