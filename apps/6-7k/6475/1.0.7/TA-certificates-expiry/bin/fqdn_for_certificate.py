import import_declare_test

import os
import sys
import time
import datetime
import json
import collections
import socket
import ssl
import uuid
import hashlib

from pathlib import Path

from splunklib import modularinput as smi
from splunktaucclib.modinput_wrapper import base_modinput as base_mi

from cryptography.hazmat.backends import default_backend
from cryptography import x509
from cryptography.x509.oid import ExtensionOID, ExtendedKeyUsageOID

def get_extended_key_usage(pem_cert_str, helper=None):
    try:
        cert = x509.load_pem_x509_certificate(pem_cert_str.encode(), default_backend())
        eku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE)
        eku_oids = []
        for oid in eku_ext.value:
            if oid == ExtendedKeyUsageOID.SERVER_AUTH:
                eku_oids.append("Server Authentication")
            elif oid == ExtendedKeyUsageOID.CLIENT_AUTH:
                eku_oids.append("Client Authentication")
            else:
                eku_oids.append(oid.dotted_string)
        eku_oids = list(set(eku_oids))
        return eku_oids
    except x509.ExtensionNotFound:
        if helper:
            helper.log_debug("No Extended Key Usage found for cert.")
        return []
    except Exception as e:
        if helper:
            helper.log_debug(f"Error parsing EKU: {e}")
        return []


# ------------------------------------------------------------------------
# Certificate retrieval (direct)
# ------------------------------------------------------------------------
def get_cert(fqdn_or_hostname, port=443, helper=None):  
    try:
        port = int(port) if port else 443
    except Exception:
        port = 443
    start_total = time.perf_counter()
    tcp_start = time.perf_counter()
    conn = socket.create_connection((fqdn_or_hostname, port),timeout=10)
    tcp_end = time.perf_counter()
    # Use an explicit SSL context with max compatibility
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    tls_start = time.perf_counter()
    sock = context.wrap_socket(conn, server_hostname=fqdn_or_hostname)
    tls_end = time.perf_counter()
    #get peer IP
    peer_ip = sock.getpeername()[0]
    #get raw DER certificate
    der_cert = sock.getpeercert(True)
    # sha256 fingerprint
    fingerprint = hashlib.sha256(der_cert).hexdigest()
    cert = ssl.DER_cert_to_PEM_cert(der_cert)
    ciphers = sock.cipher()
    versions = sock.version()

    temp_filename = Path(__file__).parent / str(uuid.uuid4())
    with open(temp_filename, "w") as f:
        f.write(cert)
    try:
        parsed_cert = ssl._ssl._test_decode_cert(temp_filename)
    except Exception as ex:
        if helper:
            helper.log_debug(f"Failed to parse certificate for {fqdn_or_hostname}:{port} - {ex}")
        temp_filename.unlink(missing_ok=True)
        sock.close()
        conn.close()
        return None, None, None, []
    try:
        with open(temp_filename, "r") as f:
            cert_pem = f.read()
        eku_list = get_extended_key_usage(cert_pem, helper)
    except Exception as ex:
        if helper:
            helper.log_debug(f"Failed to parse EKU for {fqdn_or_hostname}:{port} - {ex}")
        eku_list = []
    finally:
        temp_filename.unlink(missing_ok=True)
        sock.close()
        conn.close()
    tcp_time_ms = round((tcp_end - tcp_start) * 1000, 2)
    tls_time_ms = round((tls_end - tls_start) * 1000, 2)
    total_time_ms = round((tls_end - start_total) * 1000, 2)
    return parsed_cert, ciphers, versions, eku_list, fingerprint, peer_ip, tcp_time_ms, tls_time_ms, total_time_ms


# ------------------------------------------------------------------------
# Certificate retrieval (via proxy)
# ------------------------------------------------------------------------
def get_cert_via_proxy(cn, endpoint, ep_port, p, helper=None):  
    CONNECT = f"CONNECT {endpoint}:{ep_port or 443} HTTP/1.0\r\nConnection: close\r\n\r\n"
    proxy_connect = p["proxy_url"], int(p["proxy_port"])
    # proxy timing
    start_total = time.perf_counter()

    # TCP to proxy
    tcp_start = time.perf_counter()
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.connect(proxy_connect)
    tcp_end = time.perf_counter()

    #connect tunnel
    proxy_start = time.perf_counter()
    connection.send(str.encode(CONNECT))
    response = connection.recv(4096)
    proxy_end = time.perf_counter()

    if b"200" not in response:
        helper.log_info(f"Proxy CONNECT failed for {endpoint}:{ep_port}")
        connection.close()
        raise Exception(f"Proxy CONNECT failed for {endpoint}:{ep_port}")
    else:
        helper.log_debug(f"Successful proxy connection for {endpoint}:{ep_port}")

    #TLS handshake
    tls_start = time.perf_counter()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    sock = context.wrap_socket(connection, server_hostname=cn)
    tls_end = time.perf_counter()

    peer_ip = sock.getpeername()[0]
    ciphers = sock.cipher()
    versions = sock.version()
    # get DER certificate
    der_cert = sock.getpeercert(True)

    # generate SHA256 fingerprint
    fingerprint = hashlib.sha256(der_cert).hexdigest()
    # convert to PEM
    certificate = ssl.DER_cert_to_PEM_cert(der_cert)
    temp_filename = Path(__file__).parent / str(uuid.uuid4())
    with open(temp_filename, "w") as f:
        f.write(certificate)
    try:
        parsed_cert = ssl._ssl._test_decode_cert(temp_filename)
    except Exception as ex:
        helper.log_debug(f"Failed to parse certificate for {endpoint}:{ep_port} - {ex}")
        temp_filename.unlink(missing_ok=True)
        sock.close()
        connection.close()
        return None, None, None, []
    try:
        with open(temp_filename, "r") as f:
            cert_pem = f.read()
        eku_list = get_extended_key_usage(cert_pem, helper)
    except Exception as ex:
        if helper:
            helper.log_debug(f"Failed to parse EKU for {endpoint}:{ep_port} - {ex}")
        eku_list = []
    finally:
        temp_filename.unlink(missing_ok=True)
        sock.close()
        connection.close()
    tcp_time_ms = round((tcp_end - tcp_start) * 1000, 2)
    proxy_time_ms = round((proxy_end - proxy_start) * 1000, 2)
    tls_time_ms = round((tls_end - tls_start) * 1000, 2)
    total_time_ms = round((tls_end - start_total) * 1000, 2)
    return parsed_cert, ciphers, versions, eku_list, fingerprint, peer_ip,tcp_time_ms, proxy_time_ms, tls_time_ms, total_time_ms


# ------------------------------------------------------------------------
# Main collection logic for Splunk modular input
# ------------------------------------------------------------------------
class ModInputfqdn_for_certificate(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = True
        super(ModInputfqdn_for_certificate, self).__init__("ta_certificates_expiry", "fqdn_for_certificate", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputfqdn_for_certificate, self).get_scheme()
        scheme.title = ("fqdn for certificate")
        scheme.description = ("Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        """
        For customized inputs, hard code the arguments here to hide argument detail from users.
        For other input types, arguments should be get from input_module. Defining new input types could be easier.
        """
        scheme.add_argument(smi.Argument("fully_qualified_domain_name", title="Fully Qualified Domain Name",
                                         description="Please enter Fully Qualified Domain Name (FQDN)",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("port", title="Endpoint Port number",
                                         description="Enter port number",
                                         required_on_create=False,
                                         required_on_edit=False))
#        scheme.add_argument(smi.Argument("enabled", title="Enabled",
#                                         description="Tick to enable, Untick to disable",
#                                         required_on_create=False,
#                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("use_proxy", title="Use Proxy",
                                         description="Tick to enable proxy use for input",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-certificates-expiry"

    def validate_input(helper, definition):
        """Implement your own validation logic to validate the input stanza configurations"""
        pass
    
    
    # ------------------------------------------------------------------------
    # Extended Key Usage extraction
    # ------------------------------------------------------------------------

    def collect_events(helper, ew):
        log_level = helper.get_log_level()
        helper.set_log_level(log_level)
        proxy_settings = helper.get_proxy()
        proxy_enabled = bool(proxy_settings)
        helper.log_debug(f"Checking if Proxy is enabled: {proxy_enabled}")
    
        input_type = helper.get_input_type()
        if proxy_enabled:
            helper.log_debug(f"proxy_settings: {proxy_settings}")
    
        length_name = len(helper.get_arg('fully_qualified_domain_name'))
        helper.log_debug(f"Total number of inputs: {length_name}")
    
        # Iterate over the configured stanzas
        for (k, v), (k1, v1), (k2, v2), (k3, v3) in zip(
            helper.get_arg('use_proxy').items(),
            helper.get_arg('fully_qualified_domain_name').items(),
            helper.get_arg('port').items(),
            helper.get_arg('index').items()
        ):
            helper.log_debug(f"{k}->{v}, {k1}->{v1}, {k2}->{v2}, {k3}->{v3}")
            now = time.time()
            nowstamp = datetime.datetime.now()
            returnedcert = None
            used_cipher_tuples = ('None', 'None', 'None')
            ssl_version = 'None'
            eku = 'None'
    
            try:
                if v and proxy_settings:
                    returnedcert, used_cipher_tuples, ssl_version, eku, fingerprint, peer_ip, proxy_time_ms, tcp_time_ms, tls_time_ms, total_time_ms = get_cert_via_proxy(
                        k, v1, v2, proxy_settings, helper
                    )
                else:
                    returnedcert, used_cipher_tuples, ssl_version, eku, fingerprint, peer_ip, tcp_time_ms, tls_time_ms, total_time_ms = get_cert(
                        v1, v2, helper
                    )
            except Exception as ex:
                helper.log_error(
                    f'Communications issue - check setup for Input_Stanza={k1} fqdn={v1} port={v2} exception="{ex}"'
                )
                continue
    
            # skip if certificate retrieval failed
            if not returnedcert:
                helper.log_error(f"Failed to retrieve certificate for {v1}:{v2} (stanza={k1})")
                continue
    
            # Process and send to Splunk
            expiretime = ssl.cert_time_to_seconds(returnedcert["notAfter"])
            diff = (expiretime - now) // 86400
            days = int(diff)
            if days < 0:
                expiry_status = "EXPIRED"
                expiry_bucket = "Expired"
            elif days <= 7:
                expiry_status = "CRITICAL"
                expiry_bucket = "7_Days"
            elif days <= 30:
                expiry_status = "WARNING"
                expiry_bucket = "30_Days"
            elif days <= 60:
                expiry_status = "CAUTION"
                expiry_bucket = "60_Days"
            else:
                expiry_status = "OK"
                expiry_bucket = "Ok"
            issuer = dict(x[0] for x in returnedcert['issuer'])
            SAN_list = []
            try:
                for entry in returnedcert["subjectAltName"]:
                    SAN_list.append(entry[1])
            except Exception as ex:
                helper.log_debug(f"TA issue extracting subjectAltName - {ex}")
                SAN_list.append("None found")
            issuer_commonname = ''
            try:
                issuer_commonname = issuer['commonName']
            except Exception as ex:
                helper.log_debug("TA finds no issuer_commonname in certificate")
                issuer_commonname = 'None found'
            issuer_organization = issuer.get('organizationName') or ''
            used_cipher = used_cipher_tuples[0] or 'None'
            ssl_cipher_version = used_cipher_tuples[1] or 'None'
            cipher_secret_bits = str(used_cipher_tuples[2]) or 'None'
    
            returnedcert['expiry_status'] = expiry_status
            returnedcert['expiry_bucket'] = expiry_bucket
            returnedcert['cipher'] = used_cipher
            returnedcert['protocol'] = ssl_version
            returnedcert['secret_bits'] = cipher_secret_bits
            returnedcert.pop('subject', None)
            returnedcert.pop('issuer', None)
            returnedcert['issuer'] = issuer_organization
            returnedcert['organizationName'] = issuer_organization
            returnedcert['commonName'] = issuer_commonname
            returnedcert['subjectAltName'] = SAN_list
            returnedcert['expiredays'] = round(diff)
            returnedcert['port'] = v2
            returnedcert['fqdn'] = v1
            returnedcert['peer_ip'] = peer_ip
            returnedcert['fingerprint_sha256'] = str(fingerprint)
            returnedcert['inputstanza_name'] = k
            returnedcert['time'] = nowstamp.strftime("%d/%m/%Y %H:%M:%S.%f")
            returnedcert['use_proxy'] = str(v)
            if v and proxy_time_ms is not None:
                returnedcert['proxy_connect_time_ms'] = proxy_time_ms
            returnedcert['tcp_connect_time_ms'] = tcp_time_ms
            returnedcert['tls_handshake_time_ms'] = tls_time_ms
            returnedcert['total_connection_time_ms'] = total_time_ms
            returnedcert['extended_key_usage'] = ", ".join(sorted(eku)) if eku else "None"
    
            od = collections.OrderedDict(sorted(returnedcert.items()))
            od.move_to_end('time', False)
            data = json.dumps(od)
    
            event = helper.new_event(
                source=input_type,
                index=v3,
                sourcetype=helper.get_sourcetype(k),
                data=data
            )
            ew.write_event(event)
            helper.log_debug(f"Wrote certificate event for {v1}:{v2}")

    def get_account_fields(self):
        account_fields = []
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        checkbox_fields.append("enabled")
        checkbox_fields.append("use_proxy")
        return checkbox_fields

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error('Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields

if __name__ == "__main__":
    exitcode = ModInputfqdn_for_certificate().run(sys.argv)
    sys.exit(exitcode)
