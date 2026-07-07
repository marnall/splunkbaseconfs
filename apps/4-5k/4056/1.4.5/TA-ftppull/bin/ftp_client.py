""" Simple FTP client for downloading files """
from ftplib import FTP, FTP_TLS
import fnmatch


class FTPClient(object):  # pylint: disable=too-few-public-methods
    """ FTP client wrapper """
    def __init__(self, hostname, username, password,  # pylint: disable-msg=too-many-arguments
                 disable_wildcards, force_tls):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.disable_wildcards = disable_wildcards in ["1", 1, "True", "true", True]
        self.force_tls = force_tls in ["1", 1, "True", "true", True]
        if self.force_tls:
            self.ftp = FTP_TLS(hostname)
        else:
            self.ftp = FTP(hostname)
        self.ftp.login(user=username, passwd=password)

    def download(self, path, filename):
        """ Download file(s) from path """
        self.ftp.cwd(path)
        if not self.disable_wildcards:
            files = self.ftp.nlst()
            matched_files = fnmatch.filter(files, filename)
            for f in matched_files:
                lines = []
                self.ftp.retrlines('RETR %s' % f, lines.append) #pylint: disable=consider-using-f-string
                yield {'filename': f, 'contents': '\n'.join(lines)}
        else:
            lines = []
            self.ftp.retrlines('RETR %s' % filename, lines.append) #pylint: disable=consider-using-f-string
            yield {'filename': filename, 'contents': '\n'.join(lines)}
