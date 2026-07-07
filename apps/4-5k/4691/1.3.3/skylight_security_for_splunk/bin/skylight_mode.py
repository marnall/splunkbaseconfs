from splunk.persistconn.application import PersistentServerConnectionApplication
import json
import time
import os
import splunk.appserver.mrsparkle.lib.util as util

class ModeHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

        self.local_folder = os.path.join(util.get_apps_dir(), 'skylight_security_for_splunk','local')
        self.skylight_mode = os.path.join(util.get_apps_dir(), 'skylight_security_for_splunk','bin', 'skylight_mode')
        self.savedsearches = lambda path : os.path.join(util.get_apps_dir(), 'skylight_security_for_splunk', path, 'savedsearches.conf')
        self.poc_alerts = ["[Empire Powershell Key-Negotiation detection]\n",
                           "[Executable read/write to Windows Admin File Share]\n",
                           "[File upload to external server]\n",
                           "[HTTP beaconing detection by packet size]\n",
                           "[Port scanning activity]\n",
                           "[Possbile Empire Powershell HTTP beacon communication]\n",
                           "[Scanner's User-Agents]\n",
                           "[Scanning activity]\n",
                           "[SMB beaconing detection by packet size]\n",
                           "[SMB file enumeration]\n",
                           "[SMB Share scanning]\n",
                           "[Suspicious named pipes]\n",
                           "[Threat Activity detected(DNS)]\n",
                           "[Threat Activity detected(IP)]\n"]

    def handle(self, args):
        query = json.loads(args)['query'][0]
        action = query[0]
        mode = query[1]

        if action == 'switchMode':
            if mode == 'pocMode' or mode == 'fullMode':
                return  self.switch_mode(mode)
            elif mode == 'get':
                return  self.get_mode()
            else:
                return {"payload": "Bad parameter", "status": 404}
        else:
            return {"payload": "Bad option", "status": 404}

    def switch_mode(self, mode):
        def save_mode(mode):
            with open(self.skylight_mode, "w") as f:
                f.write(mode)
            return mode
        
        def save_savedsearches(fullMode):
            def backup():
                if os.path.isdir(self.local_folder):
                    if os.path.isfile(self.savedsearches("local")) and os.stat(self.savedsearches("local")).st_size != 0:
                        with open(self.savedsearches("local"), "r") as f:
                            data = f.readlines()
                            with open(self.savedsearches("local")+".backup-{0}".format(time.time()), "a") as a:
                                a.writelines(data)
            backup()
            
            def status_alert(line_num, name, mode="full"):
                def change_status(line, status="disabled = 0"):
                    with open(self.savedsearches("local"), "r") as f:
                        lines = f.readlines()
                        out = ''.join(lines[:line]) + status + '\n' + ''.join(lines[line + 1:])
                        
                        with open(self.savedsearches("local"), "w") as a:
                            a.writelines(out)

                if mode == "full":
                    with open(self.savedsearches("local")) as f:
                        for i, line in enumerate(f.readlines()):
                            if i > line_num:
                                if "disabled = 0" in line:
                                    return False
                                elif "disabled = 1" in line:
                                    change_status(i)
                                    return False
                                elif "[" in line:
                                    return True
                        return True
                else:
                    with open(self.savedsearches("local")) as f:
                        for i, line in enumerate(f.readlines()):
                            if i > line_num:
                                if "disabled = 0" in line and name in self.poc_alerts:
                                    return False
                                elif "disabled = 1" in line and name in self.poc_alerts:
                                    change_status(i)
                                    return False
                                if "disabled = 1" in line and not name in self.poc_alerts:
                                    return False
                                elif "disabled = 0" in line and not name in self.poc_alerts:
                                    change_status(i, "disabled = 1")
                                    return False
                                elif "[" in line:
                                    return True
                        return True

            def enable_alert(name, status="disabled = 0"):
                out = []
                with open(self.savedsearches("local"), "r") as f:
                    for line in f.readlines():
                        out.append(line)

                        if name in line:
                            out.append("%s\n" % (status))

                with open(self.savedsearches("local"), "w") as f:
                    f.writelines(out)

            def get_alerts():
                with open(self.savedsearches("default"), "r") as f:
                    data = f.readlines()
                    alerts = []
                    for i, line in enumerate(data):
                        if line == "\n":
                            if "[" and "]" in data[i+1] and not "License validation" in data[i+1]:
                                alerts.append(data[i+1])
                    return alerts

            def get_stanza(name):
                with open(self.savedsearches("local")) as f:
                    for i, line in enumerate(f.readlines()):
                        if name in line:
                            return i

            if fullMode:
                if os.path.isfile(self.savedsearches("local")) and os.stat(self.savedsearches("local")).st_size != 0:
                    for name in get_alerts():
                        include = get_stanza(name)
                        if type(include) == int:
                            if status_alert(include, name, "full"):
                                enable_alert(name)
                        else:
                            with open(self.savedsearches("local"), "a+") as f:
                                f.writelines(name)
                                f.writelines("disabled = 0\n\n")
                else:
                    if not os.path.isdir(self.local_folder): 
                        os.mkdir(self.local_folder)
                    with open(self.savedsearches("local"), "a+") as f:
                        for name in get_alerts():
                            f.writelines(name)
                            f.writelines("disabled = 0\n\n")
                
                save_mode("fullMode")
                util.restart_splunk()
            else:
                if os.path.isfile(self.savedsearches("local")) and os.stat(self.savedsearches("local")).st_size != 0:
                    for name in get_alerts():
                        include = get_stanza(name)
                        if type(include) == int:
                            if status_alert(include, name, "poc"):
                                enable_alert(name, "disabled = 1")
                        else:
                            with open(self.savedsearches("local"), "a+") as f:
                                f.writelines(name)
                                if name in self.poc_alerts:
                                    f.writelines("disabled = 0\n\n")
                                else:
                                    f.writelines("disabled = 1\n\n")
                else:
                    if not os.path.isdir(self.local_folder): 
                        os.mkdir(self.local_folderocal)
                    with open(self.savedsearches("local"), "a+") as f:
                        for name in get_alerts():
                            f.writelines(name)

                            if name in self.poc_alerts:
                                f.writelines("disabled = 0\n\n")
                            else:
                                f.writelines("disabled = 1\n\n")
                
                save_mode("pocMode")
                util.restart_splunk()

        if mode == 'fullMode':
            return {"payload": save_savedsearches(True), "status": 200}
        elif mode == 'pocMode':
            return {"payload": save_savedsearches(False), "status": 200}
        else:
            return {"payload": "Unknown mode", "status": 404}

    def get_mode(self):
        with open(self.skylight_mode, "r") as f:
            return {"payload": f.read(), "status": 200}
