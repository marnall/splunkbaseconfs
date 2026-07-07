import sys,re
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration
import base64
import json
import time
from distutils.version import LooseVersion

def is_string(s):
    if isinstance(s, basestring):
        return True
    return False

def field_compare(r, r_field, c, c_field):
    if r_field in r and c_field in c:
        a = r[r_field]
        b = c[c_field]
        if a == "" or b == "":
            return 0.0
        a_is_string = is_string(a)
        b_is_string = is_string(b)
        if a_is_string and b_is_string:
            return val_compare(a.lower(), b.lower())
        if not b_is_string:
            b_is_string, a_is_string = b_is_string, a_is_string
            b, a = a, b
        if b_is_string:
            return max(val_compare(x.lower(), b.lower()) for x in a)
        scores = []
        for y in b:
            scores.append(max(val_compare(y.lower(), x.lower()) for x in a))
        if len(scores) == 0:
            raise Exception("BestCPE: " + repr(a) + repr(type(a)) + " | " + repr(b) + repr(type(b)))
        return max(scores)
    return 0.0


def val_compare(a_val, c_val):
    score = 0.0
    if a_val in c_val:
        score += len(a_val)
    else:
        a_split = re.split('[\s:\-_\W]', a_val)
        c_split = re.split('[\s:\-_\W]', c_val)
        percentage = max(len(a_split), len(c_split))
        for a in a_split:
            for c in c_split:
                if a == c:
                    score += 1.0 / percentage
                elif a in c:
                    score += (0.5*len(a)) / percentage
                elif c in a:
                    score += (0.5*len(c)) / percentage
    return score

def levenshtein(s, t):
    memo = {}
    if s == "":
        return len(t)
    if t == "":
        return len(s)
    cost = 0 if s[-1] == t[-1] else 1

    i1 = (s[:-1], t)
    if not i1 in memo:
        memo[i1] = levenshtein(*i1)
    i2 = (s, t[:-1])
    if not i2 in memo:
        memo[i2] = levenshtein(*i2)
    i3 = (s[:-1], t[:-1])
    if not i3 in memo:
        memo[i3] = levenshtein(*i3)
    res = min([memo[i1]+1, memo[i2]+1, memo[i3]+cost])
    return res

@Configuration(local=True, distributed=False)
class BestCPE(StreamingCommand):

    def prepare(self):
        startTime = time.time()
        self.cpe_kvstore = self.service.kvstore["bah_cpe_correlations"]
        self.cpe_data = self.cpe_kvstore.data.query(query='{\
            "$or": [\
                { "part": "h" }, { "part": "o" }\
                ]\
            }')
        count = 0
        for cpe in self.cpe_data:
            count += 1
            if cpe["vendor"] == "microsft":
                self.logger.error("BestCPE: " + repr(cpe))
        self.logger.error("BestCPE: Time to convert KVStore: " + repr(time.time() - startTime))
        self.logger.error("BestCPE: CPEs received from KVStore: " + repr(count))

    def get_uri(self, cpe):
        return cpe["cpe_uri"]

    cpe_compare_fields = [
            "cpe_uri",
            ]
    asset_compare_fields = [
            "host_name",
            "device_name",
            "firmware_version",
            "device_type",
            "manufacturer",
            "model",
            "operating_system",
            ]

    def best_cpe(self, record):
        best_score = 0
        best_cpe = None
        best_scores = {}
        for cpe in self.cpe_data:
            score = 0
            scores = {}
            scores["firmware_version|version"] = field_compare(record, "firmware_version", cpe, "version")
            scores["manufacturer|vendor"] = 2 * field_compare(record, "manufacturer", cpe, "vendor")
            scores["model|product"] = 2 * field_compare(record, "model", cpe, "product")
            scores["operating_system|product"] = 10 * field_compare(record, "operating_system", cpe, "product")
            scores["operating_system|vendor"] = 10 * field_compare(record, "operating_system", cpe, "vendor")
            scores["operating_system|version"] = 5 * field_compare(record, "operating_system", cpe, "version")
            scores["device_name|vendor"] = 10 * field_compare(record, "device_name", cpe, "vendor")
            scores["device_name|product"] = 10 * field_compare(record, "device_name", cpe, "product")
            scores["device_name|version"] = 10 * field_compare(record, "device_name", cpe, "version")
            for key, value in scores.iteritems():
                score += value
            if score > best_score:
                best_score = score
                best_cpe = cpe["cpe_uri"]
                best_scores = scores
                self.logger.error("BestCPE Scores: " + repr(scores) + ", " + best_cpe)
        return (best_cpe, best_scores)

    def stream(self, records):
        for record in records:
            record["best_cpe"], record["best_scores"] = self.best_cpe(record)
            yield record
        return

if __name__ == "__main__":
   dispatch(BestCPE, sys.argv, sys.stdin, sys.stdout, __name__)
