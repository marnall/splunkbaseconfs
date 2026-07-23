import os
import platform
import subprocess
import sys

class UnsupportedPlatformError(Exception):
    pass

class BinaryNotFoundError(Exception):
    pass

def _binary_subdir():
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == 'linux':
        if machine in ('x86_64', 'amd64'):
            return 'linux_amd64'
        if machine in ('aarch64', 'arm64'):
            return 'linux_arm64'
    elif system == 'darwin':
        if machine in ('x86_64', 'amd64'):
            return 'darwin_amd64'
        if machine in ('arm64', 'aarch64'):
            return 'darwin_arm64'
    elif system == 'windows':
        if machine in ('amd64', 'x86_64'):
            return 'windows_amd64'
    raise UnsupportedPlatformError('unsupported platform {}/{}; supported: linux/{{amd64,arm64}}, darwin/{{amd64,arm64}}, windows/amd64'.format(system, machine))

def binary_path(binary_name='k8s_search'):
    here = os.path.dirname(os.path.abspath(__file__))
    arch_dir = _binary_subdir()
    ext = '.exe' if platform.system().lower() == 'windows' else ''
    binary = os.path.join(here, 'platform', arch_dir, binary_name + ext)
    if not os.path.isfile(binary):
        raise BinaryNotFoundError('Kubernetes Search binary for this platform was not found in the app package ({}). Reinstall the app, or contact support@outcoldsolutions.com if the problem persists.'.format(binary))
    return binary

def exec_command(binary_name, subcommand):
    try:
        binary = binary_path(binary_name)
    except (UnsupportedPlatformError, BinaryNotFoundError) as exc:
        sys.stderr.write('k8s_search launcher: {}\n'.format(exc))
        sys.exit(2)
    args = [binary, subcommand] + sys.argv[1:]
    if platform.system().lower() == 'windows':
        completed = subprocess.run(args, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        sys.exit(completed.returncode)
    else:
        os.execv(binary, args)
