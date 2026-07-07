#!/usr/bin/env python3

from tenable_asm import TenableASM
import arrow
import json

class TASM_Event_Proccessor(object):

    def __init__(self, api_key, hostname='bitdiscovery.com'):
        self.hostname = hostname
        self.api_key = api_key
        self.tasm =  TenableASM(self.api_key,hostname=hostname)

    def create_events(self, helper, ew):
        helper.log_debug("Getting T.asm smart folders for mapping into events")
        self._build_smartfolder_lookup()
        helper.log_debug("Starting T.asm inventory collection and event creation")
        for asset in self.tasm.inventory.list(size=5000):
            asset['bd.smartfolders'] = self._update_smartfolders(asset.pop('bd.smartfolders'))
            if asset.get('bd.addedtoportfolio', False):
                asset['bd.addedtoportfolio'] = self._convert_epoch_to_timestamp(asset.get('bd.addedtoportfolio'))
            clean_asset = json.dumps(self._strip_prefix_from_keys(asset))
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=clean_asset)
            ew.write_event(event)
        helper.log_debug("Completed T.asm inventory collection and event creation")

    def _convert_epoch_to_timestamp(self, epoch_time):
        time = arrow.get(epoch_time)
        return time.isoformat()

    def _strip_prefix_from_keys(self, asset):
        ret = {}
        for old_key in asset:
            if old_key.startswith('bd.'):
                key = old_key.lstrip('bd.')
            elif old_key.startswith('ports.'):
                key = old_key[6:]
            else:
                key = old_key
            ret[key] = asset[old_key]
        return ret

    def _update_smartfolders(self, smartfolders):
        ret = []
        if smartfolders == '':
            return ret
        else:
            tmp_ids = smartfolders.split(',')
            for s in tmp_ids:
                id = int(s[:len(s)-6])
                data = {
                    'id': id,
                    'name': self.smartfolders[id]
                }
                ret.append(data)
            return ret

    def _build_smartfolder_lookup(self):
        self.smartfolders = {}
        for sf in self.tasm.smartfolders.list():
            self.smartfolders[int(sf['id'])] = sf['name']
