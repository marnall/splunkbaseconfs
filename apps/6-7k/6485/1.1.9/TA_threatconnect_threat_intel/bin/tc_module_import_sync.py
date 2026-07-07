"""Download ThreatConnect Owner Information Command"""

# standard library
import os
import sys

# must be imported before packages in bin/lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib_1_1_9"))

# standard library
import json

# third-party
import splunklib.results as results
from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import dispatch


class ModuleImportSync(BaseGeneratingCommand):
    """Command to download owner data from ThreatConnect API.

    Usage:
    | tccleanup
    """

    _stored_module_imports = None
    _retrieved_module_imports = None

    def update_module_import(self, name, values):
        self.log(
            "info", "module-import-sync", f"updating name: {name}, values: {values}"
        )
        self.results.append({"message": f"updating {values}"})
        disable = values.pop("disabled", False)
        item = self.service.inputs.__getitem__((name, self.kind))
        item.update(**values).refresh()
        if disable:
            item.disable()
        else:
            item.enable()

    def remove_module_import(self, name):
        self.log("info", "module-import-sync", f"removing name: {name}")
        self.results.append({"message": f"removing {name}"})
        self.service.inputs.delete(kind=self.kind, name=name)

    def create_module_import(self, name, values):
        self.log("info", "module-import-sync", f"adding name: {name}, values: {values}")
        self.results.append({"message": f"adding {name}"})
        disable = values.pop("disabled", False)
        item = self.service.inputs.create(kind=self.kind, name=name, **values)
        if disable:
            item.disable()
        else:
            item.enable()

    @property
    def kind(self):
        return "tc_download_iocs"

    @property
    def service_path(self):
        service_id = self.settings.get("serviceId")
        path = f"""{self.settings.get("servicePath").rstrip("/")}/sync"""
        if service_id:
            path += f"""?splunk_id={service_id}"""
        return path

    def generate(self):
        """Implement generate command for downloading owners."""
        if self.settings.get("valid", False) is False or not self.settings.get(
            "servicePath"
        ):
            log_msg = (
                "Not syncing module imports due to settings being invalid or servicePath not being "
                "provided."
            )
            self.log("info", "module-import-sync", log_msg)
            return

        self.configure_session()

        for key, value in self.retrieved_module_imports.items():
            if self.stored_module_imports.get(key) is not None:
                continue
            # module has been added
            self.create_module_import(key, value)

        for key, value in self.stored_module_imports.items():
            retrieved_value = self.retrieved_module_imports.get(key)
            # module import has been removed. Not a single if to account for comparing the name.
            if retrieved_value is None:
                if value.get("from").lower() != "internal":
                    self.remove_module_import(key)
            else:
                self.log(
                    "debug",
                    "module-import-sync",
                    f"current_value: {value}, retrieved_value: {retrieved_value}",
                )
                if not self.dicts_are_equal(value, retrieved_value):
                    self.update_module_import(key, retrieved_value)

        for r in self.results:
            yield r

    def dicts_are_equal(self, dict_one, dict_two):
        if len(dict_one) != len(dict_two):
            return False

        for k, v in dict_one.items():
            if v != dict_two.get(k):
                self.log(
                    "info",
                    "module-import-sync",
                    f"k: {k}, v: {v}, dict_two.get(k): {dict_two.get(k)}",
                )
                return False
        return True

    @staticmethod
    def result_reader(search_results):
        """[summary]

        Args:
            search_results ([type]): [description]
        """
        for data in results.ResultsReader(search_results):
            yield data

    @property
    def retrieved_module_imports(self):
        if self._retrieved_module_imports is not None:
            return self._retrieved_module_imports
        self._retrieved_module_imports = {}
        for module_import in self.modules(self.service_path):
            module_name = module_import.get("name")
            self._retrieved_module_imports[module_name] = self.transform_module_import(
                module_import
            )
        self.log(
            "debug",
            "module-import-sync",
            f"retrieved_module_imports: {self._retrieved_module_imports}",
        )
        return self._retrieved_module_imports

    def modules(self, url):
        """Iterate over the modules returned by the API."""
        result_start = 0
        params = {"resultStart": result_start, "resultLimit": 100}
        while True:
            response = self.session.get(url, params=params)
            if not response.ok:
                raise RuntimeError(response.text or response.reason)
            response = response.json()
            yield from response
            if len(response) < params["resultLimit"]:
                break
            result_start += params["resultLimit"]

    @property
    def stored_module_imports(self):
        if self._stored_module_imports:
            return self._stored_module_imports
        stored_module_imports = (
            self.service.get(
                "data/inputs/tc_download_iocs/", output_mode="json", count=0
            )
            .body.read()
            .decode("utf8")
        )
        # commented out due to [APP-4074]
        # stored_module_imports = stored_module_imports.decode('utf8').replace("'", '"')
        stored_module_imports = json.loads(stored_module_imports).get("entry", [])
        self._stored_module_imports = {}
        for module_import in stored_module_imports:
            module_name = module_import.get("name")
            self._stored_module_imports[module_name] = self.transform_module_import(
                module_import
            )

        self.log(
            "debug",
            "module-import-sync",
            f"stored_module_imports: {self._stored_module_imports}",
        )

        return self._stored_module_imports

    @staticmethod
    def transform_module_import(module_import):
        """Transform module import"""
        module_import = module_import.get("content") or module_import
        transformed_module_import = {
            "owners": module_import.get("owners"),
            "interval": module_import.get("interval"),
            "fields": module_import.get("fields"),
            "from": module_import.get("from", module_import.get("_key", "None")),
            "tql": module_import.get("tql"),
            "version": module_import.get("version"),
            "resultLimit": int(module_import.get("resultLimit", 10_000)),
        }
        if "enabled" in module_import:
            transformed_module_import["disabled"] = not module_import.get("enabled")
        else:
            transformed_module_import["disabled"] = module_import.get("disabled")
        return transformed_module_import


if __name__ == "__main__":
    try:
        dispatch(ModuleImportSync, sys.argv, sys.stdin, sys.stdout, __name__)
    except:
        # standard library
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
