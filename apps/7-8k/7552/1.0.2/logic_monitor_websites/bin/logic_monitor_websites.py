import os
import sys
import json
import time
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import Script, Scheme, Argument, EventWriter, Event


class Input(Script):
    MASK = "<encrypted>"
    APP = "logic_monitor_websites"

    def get_scheme(self):
        scheme = Scheme("Logic Monitor Website Response Metrics")
        scheme.description = "Pull website response time metrics"
        scheme.use_external_validation = False
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            Argument(
                name="org",
                title="Organisation Subdomain",
                data_type=Argument.data_type_string,
                required_on_create=True,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                name="token",
                title="Bearer Token",
                data_type=Argument.data_type_string,
                required_on_create=True,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                name="history",
                title="Days of historical data",
                data_type=Argument.data_type_number,
                required_on_create=False,
                required_on_edit=False,
            )
        )
        return scheme

    def stream_events(self, inputs, ew):
        self.service.namespace["app"] = self.APP
        # Get Variables
        input_name, input_items = inputs.inputs.popitem()
        kind, name = input_name.split("://")

        url = f"https://{input_items['org']}.logicmonitor.com/santaba/rest/website/websites"
        source = f"{input_items['org']}.logicmonitor.com"
        checkpointfile = os.path.join(
            self._input_definition.metadata["checkpoint_dir"], name
        )

        # Password Encryption
        updates = {}

        for item in ["token"]:
            stored_password = [
                x
                for x in self.service.storage_passwords
                if x.username == item and x.realm == name
            ]
            if input_items[item] == self.MASK:
                if len(stored_password) != 1:
                    ew.log(
                        EventWriter.ERROR,
                        f"Encrypted {item} was not found for {input_name}, reconfigure its value.",
                    )
                    return
                input_items[item] = stored_password[0].content.clear_password
            else:
                if stored_password:
                    ew.log(EventWriter.DEBUG, "Removing Current password")
                    self.service.storage_passwords.delete(username=item, realm=name)
                ew.log(EventWriter.DEBUG, "Storing password and updating Input")
                self.service.storage_passwords.create(input_items[item], item, name)
                updates[item] = self.MASK
        if updates:
            self.service.inputs.__getitem__((name, kind)).update(**updates)

        headers = {
            "X-Version": "3",
            "Authorization": f"Bearer {input_items['token']}",
        }

        end = int(time.time())
        end = end - (end % 60)
        start = end - 60 * 60 * 24

        with requests.session() as s:
            r1 = s.get(
                url,
                headers=headers,
            )
            if not r1.ok:
                ew.log(
                    EventWriter.ERROR,
                    f"Failed to get websites, status={r1.status_code}",
                )
                return

            for website in r1.json()["items"]:
                # Status
                ew.write_event(
                    Event(
                        host=website["domain"],
                        source=source,
                        sourcetype="logicmonitor:website:status",
                        data=f"status={website['status']} alert={website['alertStatus']} name=\"{website['name']}\"",
                    )
                )

                # Checkpoint
                websitecheckpointfile = checkpointfile + str(website["id"])
                try:
                    with open(websitecheckpointfile, "r", encoding="utf8") as f:
                        start = json.load(f)
                except Exception:
                    ew.log(
                        EventWriter.INFO, f"Checkpoint not found for {website['name']}"
                    )
                    start = int(time.time()) - int(
                        float(input_items.get("history", 7)) * 86400
                    )

                if start >= end:
                    ew.log(EventWriter.INFO, f"Skipping {website['domain']} ")
                    continue

                ew.log(
                    EventWriter.INFO,
                    f"Will grab events for {website['domain']} from {start} to {end}",
                )

                r2 = s.get(
                    f"{url}/{website['id']}/graphs/performance/data",
                    params={"start": start, "end": end},
                    headers=headers,
                )

                if not r2.ok:
                    ew.log(
                        EventWriter.ERROR,
                        f"Failed to get website {website['name']} {website['domain']}, status={r2.status_code}",
                    )
                    continue

                data = r2.json()

                if not data or "timestamps" not in data:
                    ew.log(EventWriter.WARN, r2.text())
                    continue

                for index, timestamp in enumerate(data["timestamps"]):
                    for line in data["lines"]:
                        ew.write_event(
                            Event(
                                time=timestamp / 1000,
                                host=website["domain"],
                                source=line["legend"].replace("Response Time - ", ""),
                                data=str(line["data"][index]),
                            )
                        )

                with open(websitecheckpointfile, "w", encoding="utf8") as f:
                    json.dump(int(data["timestamps"][-1] / 1000), f)


if __name__ == "__main__":
    exitcode = Input().run(sys.argv)
    sys.exit(exitcode)
