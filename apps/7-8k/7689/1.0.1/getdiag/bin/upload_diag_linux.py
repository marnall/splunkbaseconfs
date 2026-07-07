import pexpect
import sys

def run_diag(password, splunk_home, upload_file, case_number, upload_user, upload_description):
    command = [
        f"{splunk_home}/splunk", "diag",
        "--upload-file", upload_file,
        "--case-number", case_number,
        "--upload-user", upload_user,
        "--upload-description", upload_description
    ]

    if sys.platform.startswith("win"):
        # For Windows
        return False
        # subprocess.run(["powershell", "-Command", f"$password = '{password}'"])
        # subprocess.run(command, shell=True)
    else:
        # For Linux/macOS, use pexpect
        child = pexpect.spawn(" ".join(command))
        child.expect("(?i)password.*:")
        child.sendline(password)
        child.interact()

