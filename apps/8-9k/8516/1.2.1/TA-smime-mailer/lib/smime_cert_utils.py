"""
Certificate parsing and validation utilities for S/MIME Mailer.
Uses the cryptography library (bundled in lib/).
"""

import datetime
import hashlib
import logging
import urllib.request
import urllib.error
import ssl

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID, ExtensionOID

logger = logging.getLogger('smime_mailer.cert_utils')


def parse_certificate_pem(pem_text):
    """
    Parse a PEM-encoded X.509 certificate and return a dict of metadata.
    
    Args:
        pem_text: str, PEM-encoded certificate.
    
    Returns:
        dict with keys: cn, serial, not_before, not_after, issuer,
                        fingerprint_sha256, key_usage, email_addresses.
    """
    if isinstance(pem_text, str):
        pem_bytes = pem_text.encode('utf-8')
    else:
        pem_bytes = pem_text

    cert = x509.load_pem_x509_certificate(pem_bytes, default_backend())

    # Subject CN
    try:
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    except (IndexError, Exception):
        cn = str(cert.subject)

    # Issuer
    try:
        issuer = cert.issuer.rfc4514_string()
    except Exception:
        issuer = str(cert.issuer)

    # Serial
    serial = format(cert.serial_number, 'X')

    # Validity
    not_before = cert.not_valid_before_utc.isoformat() if hasattr(cert, 'not_valid_before_utc') else cert.not_valid_before.isoformat()
    not_after = cert.not_valid_after_utc.isoformat() if hasattr(cert, 'not_valid_after_utc') else cert.not_valid_after.isoformat()

    # Fingerprint
    fingerprint = cert.fingerprint(hashes.SHA256()).hex(':')

    # Email addresses from SAN
    email_addresses = []
    try:
        san = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        email_addresses = san.value.get_values_for_type(x509.RFC822Name)
    except Exception:
        pass

    # Also check subject email
    try:
        subj_emails = cert.subject.get_attributes_for_oid(NameOID.EMAIL_ADDRESS)
        for attr in subj_emails:
            if attr.value not in email_addresses:
                email_addresses.append(attr.value)
    except Exception:
        pass

    # Key usage
    key_usage_info = {}
    try:
        ku = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
        key_usage_info = {
            'digital_signature': ku.value.digital_signature,
            'key_encipherment': ku.value.key_encipherment,
        }
    except Exception:
        pass

    return {
        'cn': cn,
        'serial': serial,
        'not_before': not_before,
        'not_after': not_after,
        'issuer': issuer,
        'fingerprint_sha256': fingerprint,
        'email_addresses': email_addresses,
        'key_usage': key_usage_info,
    }


def validate_certificate(pem_text):
    """
    Validate a certificate: check it's parseable, check expiry.
    
    Returns:
        dict: {'valid': bool, 'error': str or None, 'cert_info': dict}
    """
    try:
        cert_info = parse_certificate_pem(pem_text)
    except Exception as e:
        return {'valid': False, 'error': f'Cannot parse certificate: {str(e)}', 'cert_info': None}

    # Check if expired
    try:
        not_after_str = cert_info.get('not_after', '')
        if not_after_str:
            not_after = datetime.datetime.fromisoformat(not_after_str.replace('Z', '+00:00'))
            now = datetime.datetime.now(datetime.timezone.utc)
            if not_after < now:
                return {
                    'valid': False,
                    'error': f'Certificate expired on {not_after_str}',
                    'cert_info': cert_info,
                }
    except Exception:
        pass  # If we can't parse the date, skip expiry check

    return {'valid': True, 'error': None, 'cert_info': cert_info}


def load_certificate_from_pem(pem_text):
    """Load and return a cryptography x509.Certificate object."""
    if isinstance(pem_text, str):
        pem_bytes = pem_text.encode('utf-8')
    else:
        pem_bytes = pem_text
    return x509.load_pem_x509_certificate(pem_bytes, default_backend())


def load_private_key_from_pem(pem_text, password=None):
    """Load and return a private key object."""
    if isinstance(pem_text, str):
        pem_bytes = pem_text.encode('utf-8')
    else:
        pem_bytes = pem_text
    if password and isinstance(password, str):
        password = password.encode('utf-8')
    return serialization.load_pem_private_key(pem_bytes, password=password, backend=default_backend())


def parse_pfx(pfx_bytes, password=None):
    """
    Parse a PFX/PKCS#12 file and extract the certificate, private key, and
    any CA chain certificates.

    Args:
        pfx_bytes: bytes, raw PFX/PKCS#12 file content.
        password:  str or bytes or None, password protecting the PFX.

    Returns:
        dict with keys:
            cert_pem  (str)  — PEM-encoded leaf certificate
            key_pem   (str)  — PEM-encoded private key (unencrypted)
            cert_info (dict) — parsed certificate metadata
            chain_pem (str)  — PEM-encoded CA chain (may be empty)
            chain_count (int) — number of CA certificates in the chain

    Raises:
        ValueError if the PFX cannot be parsed or is missing cert/key.
    """
    from cryptography.hazmat.primitives.serialization import pkcs12

    if password and isinstance(password, str):
        password = password.encode('utf-8')
    if password == b'':
        password = None

    try:
        private_key, certificate, chain = pkcs12.load_key_and_certificates(
            pfx_bytes, password, default_backend()
        )
    except Exception as e:
        raise ValueError(
            f'Cannot parse PFX/PKCS#12 file: {e}. '
            f'Check the file and password.'
        )

    if certificate is None:
        raise ValueError('PFX file does not contain a certificate.')
    if private_key is None:
        raise ValueError('PFX file does not contain a private key.')

    # Serialize certificate to PEM
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode('utf-8')

    # Serialize private key to PEM (unencrypted — will be stored in Splunk credential store)
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')

    # Serialize chain certs
    chain_pems = []
    if chain:
        for ca_cert in chain:
            chain_pems.append(
                ca_cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
            )

    # Parse metadata from the leaf certificate
    cert_info = parse_certificate_pem(cert_pem)

    return {
        'cert_pem': cert_pem,
        'key_pem': key_pem,
        'cert_info': cert_info,
        'chain_pem': '\n'.join(chain_pems),
        'chain_count': len(chain_pems),
    }


# =====================================================================
# CRL (Certificate Revocation List) checking
# =====================================================================

def _extract_crl_urls(cert):
    """Extract CRL Distribution Point URLs from a certificate object.

    Returns a list of HTTP/HTTPS URLs (ignores LDAP and other schemes).
    """
    urls = []
    try:
        cdp_ext = cert.extensions.get_extension_for_oid(
            ExtensionOID.CRL_DISTRIBUTION_POINTS
        )
        for dp in cdp_ext.value:
            if dp.full_name:
                for name in dp.full_name:
                    if isinstance(name, x509.UniformResourceIdentifier):
                        url = name.value
                        if url.lower().startswith(('http://', 'https://')):
                            urls.append(url)
    except x509.ExtensionNotFound:
        pass
    except Exception as e:
        logger.debug(f'Could not extract CRL URLs: {e}')
    return urls


def _download_crl(url, timeout=10):
    """Download a CRL from the given URL.

    Returns a ``cryptography.x509.CertificateRevocationList`` or raises.
    """
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method='GET')
    req.add_header('User-Agent', 'TA-smime-mailer CRL checker')

    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        data = resp.read()

    # Try DER first, then PEM
    try:
        return x509.load_der_x509_crl(data, default_backend())
    except Exception:
        pass
    return x509.load_pem_x509_crl(data, default_backend())


def check_crl_revocation(pem_text, timeout=10):
    """Check whether a certificate has been revoked via its CRL Distribution Points.

    This function:
      1. Extracts CRL Distribution Point URLs from the certificate.
      2. Downloads the first reachable CRL.
      3. Checks if the certificate's serial number appears on the CRL.

    Args:
        pem_text:  str or bytes, PEM-encoded certificate.
        timeout:   int, HTTP timeout in seconds for CRL download.

    Returns:
        dict with keys:
            checked   (bool)  — True if a CRL was successfully downloaded and checked.
            revoked   (bool)  — True if the cert serial was found on the CRL.
            crl_url   (str)   — The CRL URL that was used (or '' if none).
            reason    (str)   — Human-readable revocation reason (or '').
            revocation_date (str) — ISO date of revocation (or '').
            error     (str)   — Error message if CRL check could not be performed.
            crl_urls  (list)  — All CRL Distribution Point URLs found in the cert.
    """
    result = {
        'checked': False,
        'revoked': False,
        'crl_url': '',
        'reason': '',
        'revocation_date': '',
        'error': '',
        'crl_urls': [],
    }

    # Load cert
    try:
        if isinstance(pem_text, str):
            pem_bytes = pem_text.encode('utf-8')
        else:
            pem_bytes = pem_text
        cert = x509.load_pem_x509_certificate(pem_bytes, default_backend())
    except Exception as e:
        result['error'] = f'Cannot parse certificate: {e}'
        return result

    serial = cert.serial_number

    # Extract CRL URLs
    crl_urls = _extract_crl_urls(cert)
    result['crl_urls'] = crl_urls

    if not crl_urls:
        result['error'] = 'No CRL Distribution Points found in certificate'
        return result

    # Try each CRL URL until one succeeds
    last_error = ''
    for url in crl_urls:
        try:
            crl = _download_crl(url, timeout=timeout)
            result['crl_url'] = url
            result['checked'] = True

            # Look up our serial in the CRL
            revoked_cert = crl.get_revoked_certificate_by_serial_number(serial)
            if revoked_cert is not None:
                result['revoked'] = True

                # Revocation date
                rev_date = (
                    revoked_cert.revocation_date_utc
                    if hasattr(revoked_cert, 'revocation_date_utc')
                    else revoked_cert.revocation_date
                )
                if rev_date:
                    result['revocation_date'] = rev_date.isoformat()

                # Revocation reason
                try:
                    reason_ext = revoked_cert.extensions.get_extension_for_oid(
                        x509.oid.CRLEntryExtensionOID.CRL_REASON
                    )
                    result['reason'] = reason_ext.value.reason.name
                except Exception:
                    result['reason'] = 'unspecified'

            return result

        except Exception as e:
            last_error = f'{url}: {e}'
            logger.debug(f'CRL download failed for {url}: {e}')
            continue

    # None of the CRL URLs worked
    result['error'] = f'All CRL downloads failed. Last error: {last_error}'
    return result


def check_crl_revocation_cached(pem_text, cache=None, timeout=10):
    """Like ``check_crl_revocation`` but with an optional in-memory cache.

    *cache* should be a dict that persists for the lifetime of the caller
    (e.g. a single REST request).  The cache key is the cert fingerprint.
    """
    if cache is None:
        return check_crl_revocation(pem_text, timeout=timeout)

    # Compute a quick cache key
    if isinstance(pem_text, str):
        key = hashlib.sha256(pem_text.encode('utf-8')).hexdigest()
    else:
        key = hashlib.sha256(pem_text).hexdigest()

    if key in cache:
        return cache[key]

    result = check_crl_revocation(pem_text, timeout=timeout)
    cache[key] = result
    return result
