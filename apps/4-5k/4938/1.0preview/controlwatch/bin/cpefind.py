import sys,re
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration
import base64
import json
import time
from distutils.version import LooseVersion

def cpes_equal(version):
    def match_cpe(cpe):
        version_match = cpe["version"] == version
        return version_match
    return match_cpe

def cpes_lte(version):
    parsed_version = LooseVersion(version)
    def match_cpe(cpe):
        version_match = LooseVersion(cpe["version"]) <= parsed_version
        return version_match
    return match_cpe

@Configuration(local=True, distributed=False)
class CPEFind(StreamingCommand):

    def prepare(self):
        startTime = time.time()
        self.cpe_kvstore = self.service.kvstore["bah_cpe_correlations"]
        cpe_data = self.cpe_kvstore.data.query()
        self.cpes = {}
        for cpe in cpe_data:
            vendor = cpe["vendor"]
            if vendor not in self.cpes:
                self.cpes[vendor] = {}
            product = cpe["product"]
            if product not in self.cpes[vendor]:
                self.cpes[vendor][product] = []
            self.cpes[vendor][product].append(cpe)
        self.logger.error("CPEFIND: Time to convert KVStore: " + repr(time.time() - startTime))

    def get_uri(self, cpe):
        return cpe["cpe_uri"]


    def get_cpes(self, vendor, product, version, match_fn):
        result = []
        # Vendor not in database
        if vendor in self.cpes:
            vendor_cpes = self.cpes[vendor]
            if product == "*":
                for product, product_cpes in vendor_cpes:
                    result += map(self.get_uri, product_cpes)
            elif product in vendor_cpes:
                product_cpes = vendor_cpes[product]
                if version == "*":
                    result = product_cpes
                else:
                    result = filter(match_fn(version), product_cpes)

        if len(result) > 0:
            result = map(self.get_uri, result)

        return result

    def match_cpes(self, affects):
        matches = []

        # Sample Affects Object
        # { "vendor" : {
        #     "vendor_data" : [ {
        #         "vendor_name" : "google",
        #         "product" : {
        #             "product_data" : [ {
        #                 "product_name" : "android",
        #                 "version" : {
        #                     "version_data" : [ {
        #                         "version_value" : "-",
        #                         "version_affected" : "=" } ]
        #                     }
        #                 } ]
        #             }
        #         } ]
        #     }
        # }

        try:
            affectsDict = json.loads(affects)
        except ValueError:
            return (None, None, None)


        vendors = affectsDict["vendor"]["vendor_data"]
        num_vendor = len(vendors)
        num_products = []
        for vendor_data in vendors:
            vendor = vendor_data["vendor_name"]
            products = vendor_data["product"]["product_data"]
            num_products.append(repr(len(products)))
            for product_data in products:
                product = product_data["product_name"]
                versions = product_data["version"]["version_data"]
                for version in versions:
                    comparator = version["version_affected"]
                    value = version["version_value"]
                    if comparator == "=":
                        matches += self.get_cpes(vendor, product, value, cpes_equal)
                    elif comparator == "<=":
                        matches += self.get_cpes(vendor, product, value, cpes_lte)
                    else:
                        self.logger.error("CPEFIND: Unknown comparator - " + repr(comparator))

        return (num_vendor, ", ".join(num_products), matches)

    def stream(self, records):
        for record in records:
            record['num_vendors'], record['num_products'], record["affected_cpes"] = self.match_cpes(record['affects'])
            yield record
        return

if __name__ == "__main__":
   dispatch(CPEFind, sys.argv, sys.stdin, sys.stdout, __name__)
