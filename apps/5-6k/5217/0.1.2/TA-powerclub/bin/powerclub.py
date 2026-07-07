import os
import sys
import json
import requests
from datetime import date, timedelta, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *


class Input(Script):
    MASK = "<encrypted>"
    APP = __file__.split(os.sep)[-3]

    def get_scheme(self):

        scheme = Scheme("Powerclub Usage Data")
        scheme.description = "Pull your daily Powerclub power usage data"
        scheme.use_external_validation = False
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            Argument(
                name="email",
                title="Email address",
                data_type=Argument.data_type_string,
                required_on_create=True,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                name="password",
                title="Password",
                data_type=Argument.data_type_string,
                required_on_create=True,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                name="days",
                title="Days",
                description="Days in the past to pull on first run",
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
        basecheckpointfile = os.path.join(
            self._input_definition.metadata["checkpoint_dir"], name
        )

        # Password Encryption / Decryption
        updates = {}
        for item in ["password"]:
            stored_password = [x for x in self.service.storage_passwords if x.username == item and x.realm == name]
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

        auth = {
            "email": input_items["email"],
            "password": input_items["password"],
        }
        headers = {"Accept": "application/json"}

        login = requests.post(
            "https://dest-pc-signup-sandbox.herokuapp.com/user/login",
            headers=headers,
            data=auth,
        )
        if login.ok:
            user = login.json()["data"]
            headers.update({"Authorization": user["auth_token"]})

            for a in user["address"]:
                checkpointfile = f"{basecheckpointfile}_{a['address_id']}"
                try:
                    day = datetime.strptime(
                        open(checkpointfile, "r").read(), "%Y-%m-%d"
                    ).date()
                except:
                    day = date.today() - timedelta(days=int(input_items["days"]))

                while day < date.today():
                    ew.log(EventWriter.INFO, f"Pulling {day} at {a['street']}")
                    resp = requests.get(
                        f"https://dest-pc-signup-sandbox.herokuapp.com/usage/half-hourly/{a['address_id']}?start_date={day.strftime('%Y-%m-%d')}",
                        headers=headers,
                    )
                    if resp.ok:
                        data = resp.json()["data"]
                    else:
                        data = {}

                    if data.get("usage_data") and len(data["usage_data"]) == 48:
                        ew.log(
                            EventWriter.INFO,
                            f"Writing metrics of {day.strftime('%Y-%m-%d')} at {a['street']}",
                        )
                        for z in zip(data["usage_data"], data["spot_price_data"]):
                            if z[0]["date"] == z[1]["date"]:
                                # Safe to merge them all
                                ew.write_event(
                                    Event(
                                        time=int(
                                            datetime.strptime(
                                                z[0]["date"], "%Y-%m-%dT%H:%M:%S"
                                            ).timestamp()
                                        ),
                                        source=a["street"],
                                        data=json.dumps(
                                            {
                                                "metric_name:power": z[0]["amount"],
                                                "metric_name:solar": z[0]["solar"],
                                                "metric_name:spotprice": z[1]["amount"],
                                                "metric_name:fixedprice": data["fixed_rate"],
                                            },
                                            separators=(",", ":"),
                                        ),
                                    )
                                )
                            else:
                                # Timestamp mismatch, seperate the events
                                ew.write_event(
                                    Event(
                                        time=int(
                                            datetime.strptime(
                                                z[0]["date"], "%Y-%m-%dT%H:%M:%S"
                                            ).timestamp()
                                        ),
                                        source=a["street"],
                                        data=json.dumps(
                                            {
                                                "metric_name:power": z[0]["amount"],
                                                "metric_name:solar": z[0]["solar"],
                                            },
                                            separators=(",", ":"),
                                        ),
                                    )
                                )

                                ew.write_event(
                                    Event(
                                        time=int(
                                            datetime.strptime(
                                                z[1]["date"], "%Y-%m-%dT%H:%M:%S"
                                            ).timestamp()
                                        ),
                                        source=a["street"],
                                        data=json.dumps(
                                            {
                                                "metric_name:spotprice": z[1]["amount"],
                                                "metric_name:fixedprice": data["fixed_rate"],
                                            },
                                            separators=(",", ":"),
                                        ),
                                    )
                                )
                        day = day + timedelta(days=1)
                        continue
                    else:
                        ew.log(EventWriter.INFO,f"Incomplete data for {day.strftime('%Y-%m-%d')} at {a['street']}")
                        break
                open(checkpointfile, "w").write(day.strftime("%Y-%m-%d"))
            ew.close()
            requests.delete(
                "https://dest-pc-signup-sandbox.herokuapp.com/user/logout",
                headers=headers,
            )

if __name__ == "__main__":
    exitcode = Input().run(sys.argv)
    sys.exit(exitcode)
