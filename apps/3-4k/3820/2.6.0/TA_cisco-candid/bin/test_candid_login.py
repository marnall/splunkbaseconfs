from __future__ import print_function
from candidpyclient import RestClient
import pprint
import time
import candid_logger_manager as log

_LOGGER = log.setup_logging("candid_data_collection")
from fabric import Fabric
from Epochs import Epoch
from events import Event


nae_ip = "<provide NAE hostname or ip address>"
protocol_scheme = "<http or https>"
port = "<provide port if there else set to None>"
username = "<provide username>"
password = "<provide password>"
domain_name = "<provide domain name if there else set to None>"
verify_ssl = True
last_n_epochs = "<Collect Epochs from last n hours (provide integer value)>"
TIMEOUT = 120

url = protocol_scheme + "://" + nae_ip

if port:
    url = url + ":" + port


def login():
    """Log in to NAE."""
    print("Trying a Candid Login...")
    try:
        return RestClient(url, username, password, verify_ssl, domain_name, TIMEOUT)
    except Exception as e:
        print("NAE Error: Could not login to host: {0}".format(nae_ip))
        print("Exception: {0}".format(str(e)))


def fetch_epochs():
    """Log in and fetch epochs."""
    rc = login()

    if rc:
        fab = Fabric(rc)
        ids = fab.get_fabric_ids()

        # # Fetch epoch for single fabric component with parameters specified in epoch_param_dict
        # # Note: You can modify page and size parameters as per requirement

        # ep = Epoch(rc, ids[0])
        # epoch_param_dict = {'$page': 2, '$size': 5}
        # print("****** EPOCHs FOR FABRIC: {0} and CUSTOM PARAMETERS: {1} *******".format(ids[0], epoch_param_dict))
        # resp = ep.get_last_n_epochs(param_dict=epoch_param_dict)
        # resp = ep.get_latest_epoch()
        # pp = pprint.PrettyPrinter(indent=4)
        # pp.pprint(resp)

        # To fetch latest epoch. It may not cover all epochs in user specified time-zone/all time.
        # print("************** LATEST EPOCH ************")
        # resp = ep.get_latest_epoch()
        # pp = pprint.PrettyPrinter(indent=4)
        # pp.pprint(resp)

        # get all epochs for all fabrics in user specified time-zone
        if isinstance(last_n_epochs, int):
            now_time = int(round(time.time()) * 1000)
            startTime = now_time - last_n_epochs * 60 * 60 * 1000

            for fab_id in ids:
                try:
                    ep = Epoch(rc, fab_id)
                    event_object = Event(rc, fab_id)
                    resp = ep.get_epochs_by_time(start_time=startTime, end_time=now_time)
                except Exception as e:
                    print("NAE Error: Failed to fetch epochs for fabric: {0} host {1}".format(fab_id, nae_ip))
                    print("Exception: {0}".format(str(e)))
                    continue

                if resp:
                    print("************** EPOCHs FOR FABRIC: {0} ************".format(fab_id))
                    # for each in resp:
                    #     print(str(each["epoch_id"]))
                    pp = pprint.PrettyPrinter(indent=4)
                    pp.pprint(resp)

                    # To Get Smart Events for fabric, set event_param_dict accordingly (see example from line 101)
                    try:
                        event_param_dict = {}
                        resp = event_object.get_events(event_param_dict)
                    except Exception:
                        pass

                else:
                    print("************** NO EPOCHs FOR FABRIC: {0} ************".format(fab_id))
        else:
            print("Epoch value should be an integer greater than zero.")

        # fab_id = "8dc26787-3f9d-46ab-943a-014e89e3d1f6"
        # epoch_id = "dd6cb7ea-111d-3a99-a395-040cc91cfa92"
        # category = "POLICY_ANALYSIS"
        # mnemonic_name = "CONTRACT_HAS_NO_PROVIDERS"
        # sub_category = "TENANT_SECURITY"

        # event_param_dict = {}
        # event_param_dict['$epoch_id'] = epoch_id
        # event_param_dict['severity'] = "EVENT_SEVERITY_MINOR"
        # event_param_dict['category'] = category
        # event_param_dict['sub_category'] = sub_category
        # event_param_dict['mnemonic'] = mnemonic_name
        # event_object = Event(rc, fab_id)
        # resp = event_object.get_events(event_param_dict)
        # pp = pprint.PrettyPrinter(indent=4)
        # pp.pprint(resp)
    else:
        print("Login Failed. Try Again.")


if __name__ == "__main__":
    if isinstance(last_n_epochs, int) and last_n_epochs > 0:
        fetch_epochs()
    else:
        print("Number of Epochs should be positive integer, greater than zero.")
