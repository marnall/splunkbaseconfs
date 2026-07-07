#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import remedy_incident_update_base as riub
import remedy_ticket as rt


class RemedyIncidentUpdateManual(riub.RemedyIncidentUpdateBase):
    """
    Update Remedy incident manually by running the script and passing
    in the correct parameters
    """

    def __init__(self):
        super(RemedyIncidentUpdateManual, self).__init__()

    def _get_events(self):
        args_set = self.args_set
        if args_set is None:
            raise Exception("Cannot get fields for update command.")
        required_set = self.required_set
        if required_set is None:
            raise Exception("Cannot get required fields for update command.")
        create_parser = rt.ArgumentParser()
        args_lst = self.args_lst
        # create create_parser
        for arg in args_lst:
            if arg not in required_set:
                continue
            create_parser.add_argument(
                "--" + arg, dest=arg, type=str, action="store", required=True, help=arg
            )
        for arg in args_lst:
            if arg in required_set:
                continue
            create_parser.add_argument(
                "--" + arg, dest=arg, type=str, action="store", help=arg
            )
        opts = create_parser.parse_args()

        rec = {}
        for arg in args_set:
            if hasattr(opts, arg):
                rec[arg] = getattr(opts, arg)
        return (rec,)


def main():
    handler = RemedyIncidentUpdateManual()
    handler.handle()


if __name__ == "__main__":
    main()
