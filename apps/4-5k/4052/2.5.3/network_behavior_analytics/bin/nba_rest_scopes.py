import sys

# add nba bin to sys.path so we can use nbalib package
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'network_behavior_analytics', 'bin']))

import cgi
import csv
import datetime

from collections import OrderedDict
from contextlib import closing

import splunk.rest

from nbalib import scopes
from nbalib import rest
from nbalib import validators
from nbalib import yaml

from nbalib.asoc3.six.moves import StringIO
from nbalib.asoc3 import six

class Groups(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        s = scopes.Scope()
        rest.Response.set(self.response, {'groups': s.groups_list()})

    def handle_POST(self):
        group_name = self.args.get('group', '')

        if not isinstance(group_name, six.string_types):
            rest.Response.error(self.response, "Group name is invalid.")
            return

        group_name = group_name.strip()
        if not group_name:
            rest.Response.error(self.response, "Group name is required.")
            return

        s = scopes.Scope()
        try:
            s.group_add(group_name)
        except ValueError as exc:
            rest.Response.error(self.response, str(exc))
            return

        s.save()
        rest.Response.set(self.response, {'added': True})

    def handle_DELETE(self):
        group_name = self.args.get('group', '')

        if not isinstance(group_name, six.string_types):
            rest.Response.error(self.response, "Group name is invalid.")
            return

        group_name = group_name.strip()
        if not group_name:
            rest.Response.error(self.response, "Group name is required.")
            return

        s = scopes.Scope()
        result = s.group_remove(group_name)
        if result:
            s.save()

        rest.Response.set(self.response, {'removed': result})


class GroupsEntries(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        s = scopes.Scope()
        if not s.groups_list():
            rest.Response.set(self.response, {})
            return

        try:
            group_name, entries_type, _ = self._validate_args(self.args, with_entry=False)
            entries = s.entries_list(group_name, entries_type)
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        payload = {'group': group_name, 'type': entries_type, 'entries': entries}
        rest.Response.set(self.response, payload)

    def handle_POST(self):
        try:
            group_name, entries_type, entry = self._validate_args(self.args)
        except ValueError as exc:
            rest.Response.error(self.response, str(exc))
            return

        description = self.args.get('description')

        s = scopes.Scope()
        try:
            s.entry_add(group_name, entries_type, entry, description)
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        s.save()
        rest.Response.set(self.response, {'added': True})

    def handle_DELETE(self):
        try:
            group_name, entries_type, entry = self._validate_args(self.args)
        except ValueError as exc:
            rest.Response.error(self.response, str(exc))
            return

        s = scopes.Scope()
        try:
            result = s.entry_remove(group_name, entries_type, entry)
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        s.save()
        rest.Response.set(self.response, {'removed': result})

    def _validate_args(self, args, with_entry=True):
        group_name = args.get('group', '')
        group_name = self._validate_arg(group_name, 'Group name')

        entries_type = args.get('type', '')
        entries_type = self._validate_arg(entries_type, 'Entries type')

        entry = None
        if with_entry:
            entry = args.get('entry', '')
            entry = self._validate_arg(entry, 'Entry')

        return group_name, entries_type, entry

    @staticmethod
    def _validate_arg(arg, name):
        if not isinstance(arg, six.string_types):
            raise ValueError("{0} is invalid.".format(name))

        arg = arg.strip()
        if not arg:
            raise ValueError("{0} is required.".format(name))

        return arg


class GroupsAnomaly(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        s = scopes.Scope()
        if not s.groups_list():
            rest.Response.set(self.response, {'checked': False})
            return

        try:
            group_name, anomaly_type, _ = self._validate_args(self.args, with_checked=False)
            checked = s.anomaly_enabled(group_name, anomaly_type)
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        payload = {'group': group_name, 'checked': checked}
        rest.Response.set(self.response, payload)

    def handle_POST(self):
        try:
            group_name, anomaly_type, checked = self._validate_args(self.args)
        except ValueError as exc:
            rest.Response.error(self.response, str(exc))
            return

        s = scopes.Scope()
        try:
            s.anomaly_set(group_name, anomaly_type, checked)
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        s.save()
        rest.Response.set(self.response, {'added': True})

    def _validate_args(self, args, with_checked=True):
        group_name = args.get('group', '')
        group_name = self._validate_arg(group_name, 'Group name')

        anomaly_type = args.get('type', '')
        anomaly_type = self._validate_arg(anomaly_type, 'Anomaly detection type')

        checked = False
        if with_checked:
            checked = args.get('checked', '')
            checked = self._validate_arg(checked, 'Anomaly detection value')

        return group_name, anomaly_type, checked

    @staticmethod
    def _validate_arg(arg, name):
        if not isinstance(arg, six.string_types):
            raise ValueError("{0} is invalid.".format(name))

        arg = arg.strip()
        if not arg:
            raise ValueError("{0} is required.".format(name))

        return arg


class GroupsExport(splunk.rest.BaseRestHandler):
    def _parse_boundary(self):
        content_type = self.request['headers'].get('content-type')

        boundary_index = content_type.find('boundary=')
        if boundary_index == -1:
            raise ValueError("Invalid Content-Type, expected multipart/form-data.")

        boundary = content_type[boundary_index + len('boundary='):]
        semicolon_index = boundary.find(';')
        if semicolon_index != -1:
            boundary = boundary[:semicolon_index]

        if not boundary:
            raise ValueError("Boundary not found in Content-Type.")

        return boundary

    def _get_content(self, boundary, field_name):
        pdict = {
            'CONTENT-LENGTH': int(self.request['headers'].get('content-length', "0")),
            'boundary': six.ensure_binary(boundary),
        }

        payload = six.ensure_binary(self.request['payload'])
        content = cgi.parse_multipart(six.BytesIO(payload), pdict)

        file_content = content.get(field_name)
        if file_content is None:
            raise ValueError('File upload failed.')

        if isinstance(file_content, list):
            file_content = file_content[0]

        return file_content


class GroupsCSV(GroupsExport):
    ENTRY_TYPES = {
        "ips_in_scope": scopes.EntryType.IN_SCOPE,
        "excluded_ips": scopes.EntryType.OUT_SCOPE,
        "whitelisted_domains": scopes.EntryType.TRUSTED_DOMAINS,
        "whitelisted_ips": scopes.EntryType.TRUSTED_IPS,
    }

    ANOMALY_TYPES = {
        "anomaly_domains": scopes.EntryType.TRUSTED_DOMAINS,
        "anomaly_ips": scopes.EntryType.TRUSTED_IPS,
    }

    ALL_TYPES = list(ENTRY_TYPES.keys()) + list(ANOMALY_TYPES.keys())

    def handle_GET(self):
        file_name = "alphasoc-monitoring-scope-{0}.csv".format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))

        self.response.setStatus(200)
        self.response.setHeader('content-type', 'text/csv; charset=utf-8')
        self.response.setHeader('content-disposition', 'attachment; filename="{0}"'.format(file_name))

        self._write_csv()

    def handle_POST(self):
        try:
            entries, errors = self._read_csv()
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        if errors:
            payload = {'error': 'Error parsing CSV file.', 'errors': errors}
            rest.Response.set(self.response, payload, 400)
            return

        scope = scopes.Scope()
        scope.importing = True

        errors = self._insert_entries(scope, entries)
        if errors:
            payload = {'error': 'Error inserting entries from CSV file.', 'errors': errors}
            rest.Response.set(self.response, payload, 400)
            return

        scope.importing = False
        scope.save()

        rest.Response.set(self.response, {})

    def _write_csv(self):
        scope = scopes.Scope()
        groups = scope.groups_list()

        writer = csv.writer(self.response, delimiter=",", quotechar='"')
        writer.writerow(["Group name", "Entry type", "Entry", "Description"])

        for group_name in groups:
            for csv_entry_type, entry_type in six.iteritems(self.ENTRY_TYPES):
                for entry, desc in scope.entries_list(group_name, entry_type):
                    desc = '' if not desc else six.ensure_text(desc)
                    writer.writerow([group_name, csv_entry_type, entry, desc])

            for csv_entry_type, anomaly_type in six.iteritems(self.ANOMALY_TYPES):
                anomaly = scope.anomaly_enabled(group_name, anomaly_type)
                writer.writerow([group_name, csv_entry_type, anomaly, ''])

    def _read_csv(self):
        boundary = self._parse_boundary()
        csv_content = self._get_content(boundary, 'csv-import-file')

        try:
            csv_content = six.ensure_text(csv_content)
        except UnicodeDecodeError:
            raise ValueError("Unsupported encoding type. Only UTF-8 encoding is allowed.")

        file_csv = six.StringIO(csv_content)
        reader = csv.reader(file_csv)

        try:
            self._validate_header(reader)
            entries, errors = self._parse_entries(reader)
        finally:
            file_csv.close()

        return entries, errors

    @staticmethod
    def _validate_header(reader):
        try:
            header = six.next(reader)
        except:
            raise ValueError("Unrecognized file type.")

        header = tuple([x.lower() for x in header[:4]])
        if header != ('group name', 'entry type', 'entry', 'description'):
            raise ValueError("Invalid header. Expected at least 4 columns: Group name, Entry type, Entry, Description.")

    def _parse_entries(self, reader):
        entries = []
        errors = {}

        for n, row in enumerate(reader):
            try:
                row_decoded = [six.ensure_text(entry.strip()) for entry in row]
            except UnicodeDecodeError:
                errors.setdefault("Non UTF-8 characters", []).append(n + 2)
                continue

            columns = len(row_decoded)
            if columns == 0 or not row_decoded[0]:
                continue  # omit empty entries

            if columns < 3:
                errors.setdefault("Not enough parameters", []).append(n + 2)
                continue

            if row_decoded[1] not in self.ALL_TYPES:
                errors.setdefault("Unrecognized entry type", []).append(n + 2)
                continue

            if columns == 3:
                row_decoded.append('')  # add missing description (which is optional in csv)

            entries.append(row_decoded)

        return entries, errors

    def _insert_entries(self, scope, entries):
        errors = {}
        for n, (group_name, csv_entry_type, entry, description) in enumerate(entries):
            if csv_entry_type in self.ANOMALY_TYPES:
                try:
                    anomaly_type = self.ANOMALY_TYPES[csv_entry_type]
                    scope.anomaly_set(group_name, anomaly_type, entry)
                except scopes.GroupNotExists:
                    pass
                except:
                    errors.setdefault('Invalid entry', []).append(n + 2)
            else:
                try:
                    entry_type = self.ENTRY_TYPES[csv_entry_type]
                    scope.entry_add(group_name, entry_type, entry, description)
                except scopes.EntryAlreadyExists:
                    pass
                except:
                    errors.setdefault('Invalid entry', []).append(n + 2)

        return errors


class GroupsYAML(GroupsExport):
    ENTRY_TYPES = [
        ("in_scope", scopes.EntryType.IN_SCOPE),
        ("out_scope", scopes.EntryType.OUT_SCOPE),
        ("trusted_domains", scopes.EntryType.TRUSTED_DOMAINS),
        ("trusted_ips", scopes.EntryType.TRUSTED_IPS),
    ]

    def handle_GET(self):
        file_name = "alphasoc-monitoring-scope-{0}.yml".format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))

        self.response.setStatus(200)
        self.response.setHeader('content-type', 'text/x-yaml; charset=utf-8')
        self.response.setHeader('content-disposition', 'attachment; filename="{0}"'.format(file_name))

        self._write_yaml()

    def handle_POST(self):
        try:
            content = self._read_yaml()
        except yaml.YAMLError as exc:
            if hasattr(exc, 'problem_mark'):
                mark = exc.problem_mark
                msg = "Error loading yaml - line: %s, column: %s." % (mark.line + 1, mark.column + 1)
            else:
                msg = str(exc)

            rest.Response.error(self.response, msg)
            return
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        scope = scopes.Scope()
        scope.importing = True

        try:
            self._insert_content(scope, content)
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        scope.importing = False
        scope.save()

        rest.Response.set(self.response, {})

    def _write_yaml(self):
        scope = scopes.Scope()
        groups_labels = scope.groups_list()

        content = {'groups': {}}

        for group_label in groups_labels:
            group_id = scopes.Group.id_from_label(group_label)
            group = self._init_group(group_label)

            for yaml_type, entry_type in self.ENTRY_TYPES:
                for entry, _ in scope.entries_list(group_label, entry_type):
                    entry = self._format_as_cidr(entry)
                    group[yaml_type].append(entry)

            content['groups'][group_id] = group

        yaml_content = self.ordered_dump(content, default_flow_style=False, allow_unicode=False, tags=False)
        self.response.write(yaml_content)

    @staticmethod
    def ordered_dump(data, stream=None, Dumper=yaml.SafeDumper, **kwargs):
        class OrderedDumper(Dumper):
            pass

        def _dict_representer(dumper, data):
            return dumper.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, list(data.items()))

        OrderedDumper.add_representer(OrderedDict, _dict_representer)
        return yaml.dump(data, stream, OrderedDumper, **kwargs)

    def _init_group(self, label):
        group = OrderedDict()
        group['label'] = label

        for yaml_type, _ in self.ENTRY_TYPES:
            group[yaml_type] = []

        return group

    @staticmethod
    def _format_as_cidr(entry):
        try:
            ip = validators.IP.check(entry)
        except:
            return entry

        network = "/32" if ip.find('.') > 0 else "/128"
        return ip if "/" in ip else ip + network

    def _read_yaml(self):
        boundary = self._parse_boundary()
        yaml_content = self._get_content(boundary, 'yaml-import-file')

        try:
            yaml_content = six.ensure_text(yaml_content)
        except UnicodeDecodeError:
            raise ValueError("Unsupported encoding type. Only UTF-8 encoding is allowed.")

        with closing(StringIO(yaml_content)) as file_yaml:
            content = yaml.safe_load(file_yaml)

        return content

    def _insert_content(self, scope, content):
        if not isinstance(content, dict):
            raise ValueError("Invalid file format: main content is not a dictionary.")

        groups = content.get('groups')
        if not isinstance(groups, dict):
            raise ValueError("Invalid file format: groups key not found.")

        for yaml_id, details in six.iteritems(groups):
            label = details.get('label')
            if not label:
                raise ValueError("Invalid file format: label key not found in group '{0}'.".format(yaml_id))

            for yaml_type, entry_type in self.ENTRY_TYPES:
                entries = details.get(yaml_type)
                if not entries:
                    continue
                elif not isinstance(entries, (list, dict)):
                    raise ValueError(
                        "Invalid file format: '{0}' key not found in group '{1}'.".format(yaml_type, yaml_id))

                for entry in entries:
                    try:
                        scope.entry_add(label, entry_type, entry)
                    except scopes.EntryAlreadyExists:
                        pass
