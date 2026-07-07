import os
import platform
import subprocess
import sys

def get_script_binary():
    os_type = platform.system().lower()

    if os_type == 'linux':
        return 'nordpass_activities_app-linux'
    elif os_type == 'darwin':
        return 'nordpass_activities_app-darwin'
    elif os_type == 'windows':
        return 'nordpass_activities_app-windows.exe'
    else:
        return 'nordpass_activities_app-linux'

def main():
    try:
        script_binary = get_script_binary()
        script_path = os.path.join(os.path.dirname(__file__), script_binary)
        result = subprocess.run([script_path] + sys.argv[1:], check=True, capture_output=True, text=True)

        print(result.stdout)
        print(result.stderr, file=sys.stderr)
    except Exception as e:
        pass  # Do nothing and let the script exit successfully

if __name__ == "__main__":
    main()
