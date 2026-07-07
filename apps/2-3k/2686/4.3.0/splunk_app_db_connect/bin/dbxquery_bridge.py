import socket
import sys
import threading
import uuid
import select
from dbx2.logger_factory import LoggerFactory
from dbx2.query_server_configuration_provider import QueryServerConfigurationProvider
from dbx2.configuration_provider import ConfigurationProvider


# Read from stdin. when length=None, read first line(header) only.


# DBX-5233:
# In Python3, stdin.read() reads strings rather than bytes,
# then string length does not match bytes length in chunk header,
# which may cause search hanging.
def read_from_standard_input(length):
    data = sys.stdin.buffer.read(length)
    return data.decode("utf-8")


# Write bytes instead of strings


# DBX-5169:
# Search expects bytes.
# Decode message to string may break the decoding boundaries
def write_to_standard_output(data):
    sys.stdout.buffer.write(data)
    sys.stdout.flush()


def encode_standard_output_for_windows():
    if is_on_windows_platform():
        sys.stdout = open(
            sys.__stdout__.fileno(),
            mode=sys.__stdout__.mode,
            buffering=1,
            encoding=sys.__stdout__.encoding,
            errors=sys.__stdout__.errors,
            newline="\n",
            closefd=False,
        )


def is_on_windows_platform():
    return sys.platform.startswith("win")


class DbxQueryBridge(object):
    DEFAULT_SOCKET_TIMEOUT = 0  # Default value for socket timeout, 0 means no timeout
    DEFAULT_STDIN_TIMEOUT = 0  # Default value for stdin timeout, 0 means no timeout

    def __init__(self, args):
        self.args = args
        self.port = QueryServerConfigurationProvider().get_configuration()
        self.socket_timeout = self.DEFAULT_SOCKET_TIMEOUT
        self.stdin_timeout = self.DEFAULT_STDIN_TIMEOUT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("localhost", self.port))
        self.trace_id = uuid.uuid4()
        self.logger = LoggerFactory.create()

    def connect(self):
        self.socket_timeout, self.stdin_timeout = self._get_timeout_configuration()
        self.logger.debug(
            f"feature=query component=bridge action=connect message=started, port={self.port}, socket_timeout={self.socket_timeout}, stdin_timeout={self.stdin_timeout}, trace_id={self.trace_id}, python_version={sys.version}"
        )
        th = threading.Thread(target=self.send_to_server)

        self.logger.debug(
            f"feature=query component=bridge action=connect message=sending to server, trace_id={self.trace_id}"
        )
        th.start()

        self.logger.debug(
            f"feature=query component=bridge action=connect message=receiving from server, trace_id={self.trace_id}"
        )
        self.receive_from_server()

        self.logger.debug(
            f"feature=query component=bridge action=connect message=waiting for sending to server, trace_id={self.trace_id}"
        )
        th.join()

        self.logger.debug(
            f"feature=query component=bridge action=connect message=closing socket, trace_id={self.trace_id}"
        )
        self.sock.close()

        self.logger.debug(
            f"feature=query component=bridge action=connect message=closing standard input, trace_id={self.trace_id}"
        )
        sys.stdin.close()

        self.logger.debug(
            f"feature=query component=bridge action=connect message=closing standard output, trace_id={self.trace_id}"
        )

        self.logger.debug(
            f"feature=query component=bridge action=connect status=success message=successfully connected, trace_id={self.trace_id}"
        )

    def send_to_server(self):
        try:
            while True:
                head = self._read_head_from_standard_input()
                if not head:
                    break

                head_fields = head.split(",")
                meta_len = int(head_fields[1])
                data_len = int(head_fields[2])
                meta_data = read_from_standard_input(meta_len)

                data = ""
                if data_len:
                    data = read_from_standard_input(data_len)

                # ADDON-70463:
                # Function scoped (not global) timeout for the
                # socket communication.
                # It helps to avoid scheduled searches to get stuck
                if self.socket_timeout == self.DEFAULT_SOCKET_TIMEOUT:
                    available = True
                else:
                    _, available, _ = select.select([], [self.sock], [], self.socket_timeout)

                if available:
                    data = head + meta_data + data
                    self.sock.sendall(data.encode("utf-8"))
                else:
                    self.logger.warning(
                        f"feature=query component=bridge action=send_to_server status=failed message=server not available, trace_id={self.trace_id}"
                    )
                    break

        except Exception as e:
            self.logger.error(
                f"feature=query component=bridge action=send_to_server status=failed message=failed to send to server, trace_id={self.trace_id}, cause={e}"
            )

    def receive_from_server(self):
        try:
            # DBX-4889:
            # For windows, text mode stdout write will generate one more
            # carriage return '\r' which corrupts the data.
            encode_standard_output_for_windows()

            while True:
                # ADDON-70463:
                # Function scoped (not global) timeout for the
                # socket communication.
                # It helps to avoid scheduled searches to get stuck
                if self.socket_timeout == self.DEFAULT_SOCKET_TIMEOUT:
                    available = True
                else:
                    available, _, _ = select.select([self.sock], [], [], self.socket_timeout)

                data = None
                if available:
                    data = self.sock.recv(1024 * 1024)
                else:
                    self.logger.warning(
                        f"feature=query component=bridge action=receive_from_server status=failed message=server not available, trace_id={self.trace_id}"
                    )

                if not data:
                    break

                write_to_standard_output(data)

        except Exception as e:
            self.logger.error(
                f"feature=query component=bridge action=receive_from_server status=failed message=failed to receive from server, trace_id={self.trace_id}, cause={e}"
            )

    def _read_head_from_standard_input(self):
        try:
            # ADDON-70463:
            # Timeout for read from standard input.
            # It helps to avoid scheduled searches to get stuck
            if is_on_windows_platform() or self.stdin_timeout == self.DEFAULT_STDIN_TIMEOUT:
                # On Windows select.select(...) only has support for sockets
                ready = True
            else:
                ready, _, _ = select.select([sys.stdin], [], [], self.stdin_timeout)

            if ready:
                data = sys.stdin.buffer.readline()
                return data.decode("utf-8")
            else:
                self.logger.warning(
                    f"feature=query component=bridge action=read_head_from_standard_input status=failed message=standard input not ready, trace_id={self.trace_id}"
                )
        except Exception as e:
            self.logger.error(
                f"feature=query component=bridge action=read_head_from_standard_input status=failed message=failed to read from standard input, cause={e}"
            )

    def _get_timeout_configuration(self):
        try:
            configuration = ConfigurationProvider().get_configuration("dbx_settings", "java")
            socket_timeout = configuration.get("queryServerSocketTimeout")
            stdin_timeout = configuration.get("queryServerStdinTimeout")

            return int(socket_timeout), int(stdin_timeout)
        except Exception as e:
            self.logger.warning(
                f"feature=query component=bridge action=get_timeout_configuration status=failed, cause={e}"
            )
            return self.DEFAULT_SOCKET_TIMEOUT, self.DEFAULT_STDIN_TIMEOUT


def main():
    bridge = DbxQueryBridge(sys.argv)
    bridge.connect()


if __name__ == "__main__":
    main()
