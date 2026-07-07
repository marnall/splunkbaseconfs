#!/usr/bin/env python3

import os
import platform
import subprocess
import sys
import tempfile
import time

from splunklib.searchcommands import Configuration, GeneratingCommand, Option, dispatch


@Configuration(local=True, distributed=False)
class gencsrCommand(GeneratingCommand):
    common_name = Option(require=True)
    country = Option(require=False, default="US")
    state = Option(require=False, default="NA")
    locality = Option(require=False, default="NA")
    organization = Option(require=False, default="NA")
    organizationalunit = Option(require=False, default="NA")
    password = Option(require=False, default="dummypassword")
    subjectaltname = Option(require=False, default=None)

    def generate(self):
        domain = self.common_name.strip()
        country = self.country.strip()
        state = self.state.strip()
        locality = self.locality.strip()
        organization = self.organization.strip()
        organizational_unit = self.organizationalunit.strip()
        password = self.password.strip()
        subject_alt_name = self.subjectaltname.strip() if self.subjectaltname else None

        splunk_bin = "splunk.exe" if platform.system() == "Windows" else "splunk"
        openssl_cmd = [
            os.path.join(os.environ["SPLUNK_HOME"], "bin", splunk_bin),
            "cmd",
            "openssl",
        ]

        try:
            key_cmd = openssl_cmd + [
                "genrsa",
                "-des3",
                "-passout",
                f"pass:{password}",
                "2048",
            ]

            key_output = subprocess.check_output(key_cmd, stderr=subprocess.STDOUT)

            decrypt_cmd = openssl_cmd + [
                "rsa",
                "-passin",
                f"pass:{password}",
                "-outform",
                "PEM",
            ]

            key_pem = subprocess.check_output(
                decrypt_cmd, input=key_output, stderr=subprocess.STDOUT
            )

            key_pem_decoded = key_pem.decode().replace("writing RSA key", "").strip()

            with tempfile.NamedTemporaryFile(
                delete=False, mode="wb", suffix=".key"
            ) as key_file:
                key_file.write(key_pem)
                key_file.flush()
                key_file_path = key_file.name

            try:
                if subject_alt_name:
                    san_entries = [
                        f"DNS:{san.strip()}" for san in subject_alt_name.split(",")
                    ]
                    san_string = ", ".join(san_entries)

                    openssl_config = f"""
                                            [ req ]
                                            default_bits = 2048
                                            distinguished_name = req_distinguished_name
                                            req_extensions = req_ext
                                            prompt = no

                                            [ req_distinguished_name ]
                                            C  = {country}
                                            ST = {state}
                                            L  = {locality}
                                            O  = {organization}
                                            OU = {organizational_unit}
                                            CN = {domain}

                                            [ req_ext ]
                                            subjectAltName = {san_string}
                                        """

                    with tempfile.NamedTemporaryFile(
                        delete=False, mode="w", suffix=".cnf"
                    ) as cfg_file:
                        cfg_file.write(openssl_config)
                        cfg_file.flush()
                        cfg_file_path = cfg_file.name

                    csr_cmd = openssl_cmd + [
                        "req",
                        "-new",
                        "-key",
                        key_file_path,
                        "-passin",
                        f"pass:{password}",
                        "-config",
                        cfg_file_path,
                    ]

                else:
                    csr_cmd = openssl_cmd + [
                        "req",
                        "-new",
                        "-key",
                        key_file_path,
                        "-passin",
                        f"pass:{password}",
                        "-subj",
                        f"/C={country}/ST={state}/L={locality}/O={organization}/OU={organizational_unit}/CN={domain}",
                    ]

                csr_output = subprocess.check_output(csr_cmd, stderr=subprocess.STDOUT)

            finally:
                os.unlink(key_file_path)
                if subject_alt_name:
                    os.unlink(cfg_file_path)

            yield {
                "_time": time.time(),
                "message": "CSR and Key generated successfully",
                "csr": csr_output.decode().strip(),
                "key": key_pem_decoded,
            }

        except subprocess.CalledProcessError as e:
            yield {
                "_time": time.time(),
                "message": "Error during CSR generation",
                "error": e.output.decode().strip(),
                "return_code": e.returncode,
            }

        except Exception as ex:
            yield {
                "_time": time.time(),
                "message": "Unexpected error",
                "error": str(ex).strip(),
            }


dispatch(gencsrCommand, sys.argv, sys.stdin, sys.stdout, __name__)
