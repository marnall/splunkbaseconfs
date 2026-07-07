from gzip import GzipFile
from collections import Mapping, Iterable
from hashlib import sha1
import json, platform, os, sys, io, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'niddel2_imports'))

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option
from magnetsdk2 import Connection
from magnetsdk2.validation import is_valid_uuid
from niddelutil import get_api_key, get_proxy_config, get_app_config, get_splunk_version
import boto3, botocore, botocore.config, botocore.exceptions, six
#from boto import s3
#from smart_open import smart_open
from unicodecsv import DictWriter

def process_field_name(name):
    if not isinstance(name, six.string_types):
        raise ValueError('field name should be a string')

    if name == 'net_l7proto_user_agent':
        return 'net.l7proto.user_agent'
    elif name == 'net_l7proto_content_type':
        return 'net.l7proto.content_type'
    else:
        return name.replace('_', '.')


def process_event(obj):
    if isinstance(obj, six.string_types):
        return obj
    if isinstance(obj, Mapping):
        return {process_field_name(k): process_event(v) for k, v in obj.iteritems()}
    elif isinstance(obj, Iterable):
        return [process_event(v) for v in obj]
    else:
        return obj

# Copied and adapted from https://github.com/RaRe-Technologies/smart_open/blob/master/smart_open/s3.py
class BufferedOutputBase(io.BufferedIOBase):
    """Writes bytes to S3.

    Implements the io.BufferedIOBase interface of the standard library."""

    def __init__(self, obj, min_part_size=50 * 1024**2):
        self._object = obj
        self._min_part_size = min_part_size
        self._mp = self._object.initiate_multipart_upload()

        self._buf = io.BytesIO()
        self._total_bytes = 0
        self._total_parts = 0
        self._parts = []

        #
        # This member is part of the io.BufferedIOBase interface.
        #
        self.raw = None

    #
    # Override some methods from io.IOBase.
    #
    def close(self):
        logging.debug("closing")
        if self._buf.tell():
            self._upload_next_part()

        if self._total_bytes:
            self._mp.complete(MultipartUpload={'Parts': self._parts})
            logging.debug("completed multipart upload")
        elif self._mp:
            #
            # AWS complains with "The XML you provided was not well-formed or
            # did not validate against our published schema" when the input is
            # completely empty => abort the upload, no file created.
            #
            # We work around this by creating an empty file explicitly.
            #
            logging.info("empty input, ignoring multipart upload")
            assert self._mp, "no multipart upload in progress"
            self._mp.abort()

            self._object.put(Body=b'')
        self._mp = None
        logging.debug("successfully closed")

    @property
    def closed(self):
        return self._mp is None

    def writable(self):
        """Return True if the stream supports writing."""
        return True

    def tell(self):
        """Return the current stream position."""
        return self._total_bytes

    #
    # io.BufferedIOBase methods.
    #
    def detach(self):
        raise io.UnsupportedOperation("detach() not supported")

    def write(self, b):
        """Write the given bytes (binary string) to the S3 file.

        There's buffering happening under the covers, so this may not actually
        do any HTTP transfer right away."""
        if not isinstance(b, six.binary_type):
            raise TypeError("input must be a binary string, got: %r", b)

        # logger.debug("writing %r bytes to %r", len(b), self._buf)

        self._buf.write(b)
        self._total_bytes += len(b)

        if self._buf.tell() >= self._min_part_size:
            self._upload_next_part()

        return len(b)

    def terminate(self):
        """Cancel the underlying multipart upload."""
        assert self._mp, "no multipart upload in progress"
        self._mp.abort()
        self._mp = None

    #
    # Internal methods.
    #
    def _upload_next_part(self):
        part_num = self._total_parts + 1
        logging.info("uploading part #%i, %i bytes (total %.3fGB)",
                    part_num, self._buf.tell(), self._total_bytes / 1024.0 ** 3)
        self._buf.seek(0)
        part = self._mp.Part(part_num)
        upload = part.upload(Body=self._buf)
        self._parts.append({'ETag': upload['ETag'], 'PartNumber': part_num})
        logging.debug("upload of part #%i finished" % part_num)

        self._total_parts += 1
        self._buf = io.BytesIO()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.terminate()
        else:
            self.close()

def boto3_object_exists(obj):
    try:
        obj.load()
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            six.reraise(*sys.exc_info())


@Configuration(local=True, overrides_timeorder=True, maxinputs=500000)
class NiddelSend(StreamingCommand):
    def __init__(self):
        super(NiddelSend, self).__init__()
        self._slots = {}
        self._organization = None
        self._expiration = None
        self._connection = None
        self._bucket = None
        self._headers = None
        self._comment_line = None

    @Option()
    def organization(self):
        """ **Syntax:** organization=<UUID>
            **Description:** sends the logs to given organization on the Niddel Magnet back-end. If omitted, will
            send to the organization configured on the log collection setup page on the Niddel app.
            """
        if self._organization is None:
            self._organization = self.service.confs['niddel2']['collection']['organization']

        if isinstance(self._organization, six.string_types):
            self._organization = self.connection.get_organization(self._organization)
            self.logger.info('Got details about organization {}'.format(self._organization['id']))

        return self._organization

    @organization.setter
    def organization(self, value):
        if value:
            if not is_valid_uuid(value):
                raise ValueError('organization must be a valid UUID string')
            self._organization = value.lower()
            self.logger.info('Using organization {}'.format(self._organization))
        else:
            self.logger.info('No organization argument provided')

    @property
    def connection(self):
        if not self._connection:
            api_key = get_api_key(self.service)
            if not api_key:
                raise Exception("API key was not found, please configure the Niddel app before using this command")
            appcfg = get_app_config()
            splversion = get_splunk_version()
            _user_agent = "Splunk App/v%s-build_%s; %s" % (appcfg['app_version'], appcfg['app_build'], str(splversion))
            self._connection = Connection(api_key=api_key, user_agent=_user_agent)
            proxy = get_proxy_config(self.service)
            if proxy:
                self._connection.set_proxy(**proxy)
        return self._connection

    @property
    def bucket(self):
        if not self._bucket or not self._expiration or self._expiration != self.connection.get_organization_credentials(self.organization['id']):
            creds = self.connection.get_organization_credentials(self.organization['id'])
            if self.connection._proxies:
                s3 = boto3.resource('s3', aws_access_key_id=creds['accessKeyId'],
                                    aws_secret_access_key=creds['secretAccessKey'],
                                    aws_session_token=creds['sessionToken'],
                                    region_name=creds['bucketRegion'],
                                    config=botocore.config.Config(proxies=self.connection._proxies))
            else:
                s3 = boto3.resource('s3', aws_access_key_id=creds['accessKeyId'],
                                    aws_secret_access_key=creds['secretAccessKey'],
                                    aws_session_token=creds['sessionToken'],
                                    region_name=creds['bucketRegion'])

            self._bucket = s3.Bucket(creds['bucket'])

        return self._bucket

    @property
    def comment_line(self):
        """ Logs information about the environment and app configuration, and summarizes them into a comment
        line that will be added to the top of the CSV file to help troubleshooting activities.
        """

        if not self._comment_line:
            # Get app and system basic info to add as commented lines on each CSV
            # file for debugging and parsing purposes
            appcfg = get_app_config()
            self.logger.info("Niddel App version %s build %s" %
                             (appcfg['app_version'], appcfg['app_build']))
            self._comment_line = "# " + json.dumps(appcfg) + "\n"

        return self._comment_line

    def _open_slot(self, slot):
        """ Opens connection and compression state for the given slot.
        :param slot: the slot string in YYYYMMDDHH format
        """

        if slot not in self._slots:
            # iterate until we find a key that is not in use yet
            count = 1
            upload_path = (self.organization['properties']['bucketUploadPrefix'] +
                           '/splunk-%s/%s.%d.%d.gz' % (sha1(platform.node()).hexdigest(), slot, os.getpid(), count))
            while True:
                obj = self.bucket.Object(upload_path)
                if not boto3_object_exists(obj):
                    break
                count += 1
                upload_path = (self.organization['properties']['bucketUploadPrefix'] +
                               '/splunk-%s/%s.%d.%d.gz' % (sha1(platform.node()).hexdigest(), slot, os.getpid(), count))
            self.logger.info('writing events from %s to s3://%s/%s' % (slot, self.bucket.name, upload_path))

            # open the file and the gzip writer, and write the comment line immediately
            sos3 = BufferedOutputBase(obj)
            gzfile = GzipFile(os.path.basename(upload_path), 'wb', fileobj=sos3)
            gzfile.write(self.comment_line)
            self._slots[slot] = {'s3': sos3, 'gzfile': gzfile, 'count': 0}

        return self._slots[slot]

    def _close_slot(self, slot):
        """ Removes all local data and state associated with the given slot.
        :param slot: the slot string in YYYYMMDDHH format
        """
        if slot in self._slots:
            if isinstance(self._slots[slot], dict):
                if 'count' in self._slots[slot]:
                    self.logger.info('closing slot %s with %d events' % (slot, self._slots[slot]['count']))
                if 'gzfile' in self._slots[slot]:
                    try:
                        self._slots[slot]['gzfile'].close()
                    except:
                        self.logger.exception('error closing gzip writer for slot %s' % slot)
                if 's3' in self._slots[slot]:
                    try:
                        self._slots[slot]['s3'].close()
                    except:
                        self.logger.exception('error closing S3 writer for slot %s' % slot)
            del self._slots[slot]

    def _close(self):
        """ Cleans up any state objects in self._slots """
        for slot in self._slots.keys():
            self._close_slot(slot)

    def stream(self, events):
        """ Processes a batch of events by writing them in streaming mode to S3 in compressed GZIP format.
        :param events: the events sent to this command by the search
        """
        try:
            for e in events:
                fixed_e = process_event(dict(e))
                if 'slot' not in e:
                    raise ValueError('event is missing slot attribute: %s' % repr(e))
                slot = self._open_slot(fixed_e['slot'])

                if 'csvwriter' not in slot:
                    slot['csvwriter'] = DictWriter(slot['gzfile'], fieldnames=fixed_e.keys(), restval='NA')
                    slot['csvwriter'].writeheader()

                slot['csvwriter'].writerow(fixed_e)
                slot['count'] += 1
                yield e
        except:
            self.logger.exception('exception raised during stream processing')
            raise
        finally:
            self._close()


dispatch(NiddelSend, sys.argv, sys.stdin, sys.stdout, __name__)
