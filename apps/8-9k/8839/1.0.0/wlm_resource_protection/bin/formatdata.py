import sys
import json
from splunk.rest import simpleRequest
from splunklib.searchcommands import dispatch, EventingCommand, Configuration
import splunk.mining.dcutils as dcu

logger = dcu.getLogger()


@Configuration()
class FormatData(EventingCommand):
    mib_to_gib = 1.0 / 1024.0
    default_collection_period = 10.0
    remote_sid_prefix = "remote_"
    parallel_sid_prefix = "prd.ph"

    def getCollectionPeriodInSecs(self):
        collection_period = self.default_collection_period
        try:
            path = (
                "/servicesNS/-/introspection_generator_addon/configs/conf-server/"
                "introspection:generator:resource_usage?output_mode=json"
            )
            response, content = simpleRequest(
                path,
                sessionKey=self.service.token,
                method='GET'
            )

            if response.status == 200:
                if isinstance(content, bytes):
                    content = content.decode('utf-8')

                payload = json.loads(content)
                if "entry" in payload and len(payload["entry"]) > 0:
                    content_dict = payload["entry"][0].get("content", {})
                    collection_period = content_dict.get(
                        "collectionPeriodInSecs",
                        self.default_collection_period
                    )
            else:
                logger.error(
                    "Failed to get collectionPeriodInSecs. Status: {0}".format(
                        response.status
                    )
                )

        except Exception as e:
            logger.error(
                "Error retrieving collectionPeriodInSecs: {0}, using default value".format(
                    str(e)
                )
            )

        logger.debug("collectionPeriodInSecs={0}".format(collection_period))
        return float(collection_period)

    def normalize_sid(self, sid):
        is_sh = True

        if not sid.startswith(self.remote_sid_prefix):
            return sid, is_sh

        is_sh = False
        normalized_sid = sid[len(self.remote_sid_prefix):]
        sh_name = self.service.info["serverName"]
        sh_prefix = sh_name + "_"

        if normalized_sid.startswith(sh_prefix):
            normalized_sid = normalized_sid[len(sh_prefix):]

        sid_parts = normalized_sid.split("_", 1)
        if (
            len(sid_parts) == 2 and
            sid_parts[0].startswith(self.parallel_sid_prefix)
        ):
            normalized_sid = sid_parts[1]

        return normalized_sid, is_sh

    def transform(self, records):
        collection_period = self.getCollectionPeriodInSecs()

        output_records = {}
        search_details = {}
        for record in records:
            sid = record.get('sid')
            sid, is_sh = self.normalize_sid(sid)
            single_vcpu_sec = float(record.get('pct_cpu', 0)) / 100 * collection_period
            single_mem_usage = float(record.get('mem_used', 0)) * self.mib_to_gib
            single_mem_gib_sec = single_mem_usage * collection_period

            if sid not in output_records:
                output_records[sid] = {
                    'total_vcpu_sec': 0,
                    'total_mem_gib_sec': 0,
                    'shs_vcpu_sec': 0,
                    'shs_mem_gib_sec': 0,
                    'idxs_vcpu_sec': 0,
                    'idxs_mem_gib_sec': 0,
                    'max_shs_vcpu_sec': 0,
                    'max_idxs_vcpu_sec': 0,
                    'max_shs_mem_usage': 0,
                    'max_idxs_mem_usage': 0
                }

            if sid not in search_details:
                search_details[sid] = {
                    'user': ""
                }

            user = record.get('user', "")
            if user:
                search_details[sid]['user'] = user

            output_records[sid]['total_vcpu_sec'] += single_vcpu_sec
            output_records[sid]['total_mem_gib_sec'] += single_mem_gib_sec

            shs_vcpu_sec = 0
            shs_mem_gib_sec = 0
            idxs_vcpu_sec = 0
            idxs_mem_gib_sec = 0

            if is_sh:
                shs_vcpu_sec = single_vcpu_sec
                shs_mem_gib_sec = single_mem_gib_sec
                if single_mem_usage > output_records[sid]['max_shs_mem_usage']:
                    output_records[sid]['max_shs_mem_usage'] = single_mem_usage
                if single_vcpu_sec > output_records[sid]['max_shs_vcpu_sec']:
                    output_records[sid]['max_shs_vcpu_sec'] = single_vcpu_sec
            else:
                idxs_vcpu_sec = single_vcpu_sec
                idxs_mem_gib_sec = single_mem_gib_sec
                if single_mem_usage > output_records[sid]['max_idxs_mem_usage']:
                    output_records[sid]['max_idxs_mem_usage'] = single_mem_usage
                if single_vcpu_sec > output_records[sid]['max_idxs_vcpu_sec']:
                    output_records[sid]['max_idxs_vcpu_sec'] = single_vcpu_sec

            output_records[sid]['shs_vcpu_sec'] += shs_vcpu_sec
            output_records[sid]['shs_mem_gib_sec'] += shs_mem_gib_sec
            output_records[sid]['idxs_vcpu_sec'] += idxs_vcpu_sec
            output_records[sid]['idxs_mem_gib_sec'] += idxs_mem_gib_sec

        for sid, stats in output_records.items():
            yield {
                'sid': sid,
                'user': search_details[sid]['user'],
                'total_vcpu_sec': stats['total_vcpu_sec'],
                'total_mem_gib_sec': stats['total_mem_gib_sec'],
                'shs_vcpu_sec': stats['shs_vcpu_sec'],
                'shs_mem_gib_sec': stats['shs_mem_gib_sec'],
                'idxs_vcpu_sec': stats['idxs_vcpu_sec'],
                'idxs_mem_gib_sec': stats['idxs_mem_gib_sec'],
                'max_shs_vcpu_sec': stats['max_shs_vcpu_sec'],
                'max_idxs_vcpu_sec': stats['max_idxs_vcpu_sec'],
                'max_shs_mem_usage': stats['max_shs_mem_usage'],
                'max_idxs_mem_usage': stats['max_idxs_mem_usage']
            }


if __name__ == "__main__":
    dispatch(FormatData, sys.argv, sys.stdin, sys.stdout, __name__)
