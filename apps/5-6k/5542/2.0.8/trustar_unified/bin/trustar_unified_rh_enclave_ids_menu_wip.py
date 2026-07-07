# # encoding = utf-8
#
# """
# TODO:  FINISH IMPLEMENTING THIS.
#
# NOT CURRENTLY USED.
#
# IT IS IN THE REPO, BUT NOT IN THE PROD ARTIFACT.
#
# Rest handler that powers the Enclave IDs drop-down menu in the
# modinput config menu.
#
# 'in_bytes' is bytes of JSON.
#
# {
#     "output_mode": "json",
#     "output_mode_explicit": true,
#     "server": {
#         "rest_uri": "https://127.0.0.1:8089",
#         "hostname": "ip-10-10-0-160.ec2.internal",
#         "servername": "ip-10-10-1-146.ec2.internal",
#         "guid": "25090FB6-4A35-4A86-A5EB-75D1357C08FB"
#     },
#     "restmap": {
#         "name": "script:trustar_download_enclaves",
#         "conf": {
#             "handler": "trustar_unified_rh_enclave_ids_menu.EnclaveIdsMenuHandlerScript",
#             "match": "/trustar_unified_enclave_ids_menu",
#             "python.version": "python3",
#             "script": "trustar_unified_rh_enclave_ids_menu.py",
#             "scripttype": "persist"
#         }
#     },
#     "query": [
#         [
#             "count",
#             "-1"
#         ]
#     ],
#     "connection": {
#         "src_ip": "24.17.108.180",
#         "ssl": true,
#         "listening_port": 8000
#     },
#     "session": {
#         "user": "schamales",
#         "authtoken": "REDACTED - SPLUNK AUTH TOKEN."
#     },
#     "rest_path": "/trustar_unified_enclave_ids_menu",
#     "lang": "en-US",
#     "method": "GET",
#     "ns": {
#         "app": "trustar_unified",
#         "user": "nobody"
#     }
# }
#
#
# msg = {"command_line": self.command_line,
#                "command_line_type": str(type(self.command_line)),
#                "command_arg": self.command_arg,
#                "command_arg_type": str(type(self.command_arg)),
#                "in_bytes_raw": in_bytes,
#                "in_bytes_type": str(type(in_bytes)),
#                "in_bytes_dict": json.loads(str(in_bytes))}
# """
# import json
# import sys
# from os.path import dirname, join
#
# paths = sys.path
# new_paths = [dirname(__file__)]
# new_paths.extend(paths)
# sys.path = new_paths
#
# declare_error = None
# # try:
# #    import trustar_unified_declare
# # except Exception as e:
# #    declare_error = e
#
# analysis_error = None
#
# from splunk.persistconn.application import PersistentServerConnectionApplication
#
# OUTFILE_PATH = join(dirname(__file__), "i_was_launched.txt")
# REPORTFILE_PATH = join(dirname(__file__), "report.json")
#
# # with open(OUTFILE_PATH, 'a') as f:
# #     f.write("\n\n loading file. \n\n")
# #
# #     if declare_error:
# #         f.write("\n\ndeclare error:  {}\n\n".format(str(declare_error)))
# #
# #     if analysis_error:
# #         f.write("\n\nanalysis error:  {}\n\n".format(str(analysis_error)))
#
#
# class EnclaveIdsMenuHandlerScript(PersistentServerConnectionApplication):
#     """ Enables Enclave IDs drop-down menu in modinput config menu. """
#
#     def __init__(self, command_line, command_arg):
#         PersistentServerConnectionApplication.__init__(self)
#         self.command_line = command_line
#         self.command_arg = command_arg
#
#         with open(OUTFILE_PATH, 'a') as f:
#             f.write('\n\n initializing an instance.\n\n')
#
#     def handle(self, in_bytes):  # type: (bytes) -> str or dict
#
#         try:
#             return self.go(in_bytes)
#         except Exception as e:
#             with open(OUTFILE_PATH, 'a') as f:
#                 f.write("\n\n\n{}\n\n".format(str(e)))
#
#     def go(self, in_bytes):
#
#         try:
#             import analysis
#             analysis.go(__file__)
#         except Exception as e:
#             analysis_error = e
#
#         with open(OUTFILE_PATH, 'a') as f:
#             f.write('\n\n starting handle. \n\n')
#
#         payload_a = {
#             "items": [
#                 {'label': 'abuse', 'value': '12jadk-323k-323'},
#                 {'label': 'blah', 'value': '2134324lk23ljk'}
#             ]
#         }
#
#         # a_1 yields stuff in CLI,  nothing in Splunk Search.
#         response_a_1 = json.dumps({'payload': payload_a, 'status': 200})
#
#         # a_2 yields stuff in Splunk Search and through the CLI.
#         response_a_2 = json.dumps({'payload': json.dumps(payload_a), 'status': 200})
#
#
#
#         payload_b = [{'label': 'abuse', 'value': '12jadk-323k-323'},
#                      {'label': 'blah', 'value': '2134324lk23ljk'}]
#
#         response_b = {'payload': str(payload_b), 'status': 200}
#
#
#
#
#
#         response = response_a_2
#
#         msg = {}
#         try:
#             msg['command_line'] = self.command_line
#         except:
#             pass
#
#         try:
#             msg['command_line_type'] = str(type(self.command_line))
#         except:
#             pass
#
#         try:
#             msg['command_arg'] = self.command_arg
#         except:
#             pass
#
#         try:
#             msg['command_arg_type'] = str(type(self.command_arg))
#         except:
#             pass
#
#         try:
#             msg['in_bytes_raw'] = in_bytes.decode('utf-8')
#         except:
#             pass
#
#         try:
#             msg['in_bytes_type'] = str(type(in_bytes))
#         except:
#             pass
#
#         try:
#             msg['in_bytes_dict'] = json.loads(in_bytes.decode('utf-8'))
#         except:
#             pass
#
#         with open(OUTFILE_PATH, 'a') as f:
#             f.write("\n\n")
#             f.write("writing report. keys: \n")
#             keys_ = str(msg.keys())
#             f.write(keys_)
#             f.write("\n\n")
#
#         try:
#             with open(REPORTFILE_PATH, 'w') as f:
#                 json.dump(msg, f, indent=4)
#
#         except Exception as e:
#             with open(OUTFILE_PATH, 'a') as f:
#                 f.write('\n\n' + str(e) + '\n\n')
#
#         with open(OUTFILE_PATH, 'a') as f:
#             f.write("\n\nDONE.\n\n")
#
#         return response
#
