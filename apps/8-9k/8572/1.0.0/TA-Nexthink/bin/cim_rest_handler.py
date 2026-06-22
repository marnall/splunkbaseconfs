# encoding = utf-8
"""
CIM REST Handler for TA-Nexthink

Supports full CRUD operations for CIM mappings:
- GET (list): List all CIM mappings or get specific one
- POST (create): Create new CIM mapping
- POST with existing (edit): Update existing CIM mapping  
- DELETE (remove): Delete CIM mapping and clean up conf files
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import splunk.admin as admin


APP_NAME = "TA-Nexthink"
SOURCETYPE_PREFIX = "nexthink:"
VALID_SUFFIX_PATTERN = re.compile(r'^[a-z0-9_:]+$')


class CIMMapperHandler(admin.MConfigHandler):
    """REST Handler for CIM field mapping management."""
    
    def setup(self):
        """Define supported arguments for all actions."""
        self.supportedArgs.addOptArg("sourcetype_suffix")
        self.supportedArgs.addOptArg("cim_mappings")
        self.supportedArgs.addOptArg("enable_cim")
    
    def handleList(self, confInfo):
        """GET: List all CIM mappings or get specific one."""
        # Check if requesting specific mapping
        if self.callerArgs.id:
            # Return specific mapping
            sourcetype_suffix = self.callerArgs.id
            if not VALID_SUFFIX_PATTERN.match(sourcetype_suffix):
                raise admin.ArgValidationException(
                    "sourcetype_suffix must contain only lowercase letters, numbers, underscores, or colons"
                )
            full_sourcetype = SOURCETYPE_PREFIX + sourcetype_suffix
            mappings = self._get_mappings_for_sourcetype(full_sourcetype)
            tags = self._get_tags_for_sourcetype(sourcetype_suffix)
            
            confInfo[sourcetype_suffix]["sourcetype"] = full_sourcetype
            confInfo[sourcetype_suffix]["mappings"] = json.dumps(mappings)
            confInfo[sourcetype_suffix]["tags"] = json.dumps(tags)
            confInfo[sourcetype_suffix]["exists"] = "true" if mappings else "false"
        else:
            # Return all CIM mappings
            all_mappings = self._get_all_cim_mappings()
            for item in all_mappings:
                suffix = item["sourcetype_suffix"]
                confInfo[suffix]["sourcetype"] = item["sourcetype"]
                confInfo[suffix]["mappings"] = json.dumps(item["mappings"])
                confInfo[suffix]["tags"] = json.dumps(item["tags"])
                confInfo[suffix]["field_count"] = str(len(item["mappings"]))
    
    def handleCreate(self, confInfo):
        """POST: Create or update CIM mappings for a sourcetype."""
        try:
            # Get name from URL path or from data
            sourcetype_suffix = self.callerArgs.id
            if not sourcetype_suffix:
                sourcetype_suffix = self._get_arg("sourcetype_suffix")
            
            cim_mappings_json = self._get_arg("cim_mappings", "[]")
            enable_cim = self._get_arg("enable_cim", "true")
            
            if not sourcetype_suffix:
                raise admin.ArgValidationException("sourcetype_suffix is required")
            
            if not VALID_SUFFIX_PATTERN.match(sourcetype_suffix):
                raise admin.ArgValidationException(
                    "sourcetype_suffix must contain only lowercase letters, numbers, underscores, or colons"
                )
            
            full_sourcetype = SOURCETYPE_PREFIX + sourcetype_suffix
            
            try:
                mappings = json.loads(cim_mappings_json) if cim_mappings_json else []
            except (json.JSONDecodeError, ValueError) as e:
                raise admin.ArgValidationException("Invalid JSON: " + str(e))
            
            if enable_cim.lower() == "true" and mappings:
                self._write_props_conf(full_sourcetype, mappings)
                self._write_eventtypes_conf(full_sourcetype, sourcetype_suffix)
                self._write_tags_conf(full_sourcetype, sourcetype_suffix, mappings)
                
                confInfo["result"]["status"] = "success"
                confInfo["result"]["message"] = "CIM mappings saved for " + full_sourcetype
                confInfo["result"]["field_count"] = str(len(mappings))
            else:
                self._remove_cim_config(full_sourcetype, sourcetype_suffix)
                confInfo["result"]["status"] = "success"
                confInfo["result"]["message"] = "CIM mappings cleared for " + full_sourcetype
                
        except admin.ArgValidationException:
            raise
        except Exception as e:
            confInfo["result"]["status"] = "error"
            confInfo["result"]["message"] = str(e)
    
    def handleEdit(self, confInfo):
        """Handle edit same as create."""
        self.handleCreate(confInfo)
    
    def handleRemove(self, confInfo):
        """DELETE: Remove CIM mappings for a sourcetype."""
        try:
            sourcetype_suffix = self.callerArgs.id
            if not sourcetype_suffix:
                raise admin.ArgValidationException("sourcetype_suffix is required in URL")
            
            if not VALID_SUFFIX_PATTERN.match(sourcetype_suffix):
                raise admin.ArgValidationException(
                    "sourcetype_suffix must contain only lowercase letters, numbers, underscores, or colons"
                )
            
            full_sourcetype = SOURCETYPE_PREFIX + sourcetype_suffix
            self._remove_cim_config(full_sourcetype, sourcetype_suffix)
            
            confInfo["result"]["status"] = "success"
            confInfo["result"]["message"] = "CIM mappings deleted for " + full_sourcetype
            
        except Exception as e:
            confInfo["result"]["status"] = "error"
            confInfo["result"]["message"] = str(e)
    
    def _get_arg(self, name, default=None):
        """Safely get argument value."""
        value = self.callerArgs.data.get(name)
        if value is None:
            return default
        if isinstance(value, list):
            return value[0] if value else default
        return value
    
    def _get_local_conf_path(self, conf_name):
        """Get path to local conf file, creating directory if needed."""
        splunk_home = os.environ.get("SPLUNK_HOME", "/opt/splunk")
        app_path = os.path.join(splunk_home, "etc", "apps", APP_NAME, "local")
        if not os.path.exists(app_path):
            os.makedirs(app_path)
        return os.path.join(app_path, conf_name + ".conf")
    
    def _read_conf_file(self, conf_path):
        """Read a .conf file and return as dict of stanzas."""
        stanzas = {}
        current_stanza = None
        if not os.path.exists(conf_path):
            return stanzas
        with open(conf_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    current_stanza = line[1:-1]
                    stanzas[current_stanza] = {}
                elif '=' in line and current_stanza:
                    key, value = line.split('=', 1)
                    stanzas[current_stanza][key.strip()] = value.strip()
        return stanzas
    
    def _write_conf_file(self, conf_path, stanzas):
        """Write stanzas dict to a .conf file."""
        with open(conf_path, 'w') as f:
            f.write("# Auto-generated by " + APP_NAME + " CIM Mapper\n")
            f.write("# DO NOT EDIT MANUALLY\n\n")
            for stanza_name, settings in stanzas.items():
                f.write("[" + stanza_name + "]\n")
                for key, value in settings.items():
                    f.write(key + " = " + value + "\n")
                f.write("\n")
    
    def _write_props_conf(self, sourcetype, mappings):
        """Write FIELDALIAS definitions to props.conf."""
        conf_path = self._get_local_conf_path("props")
        stanzas = self._read_conf_file(conf_path)
        
        if sourcetype in stanzas:
            stanzas[sourcetype] = dict((k, v) for k, v in stanzas[sourcetype].items() 
                                       if not k.startswith("FIELDALIAS-cim_"))
        else:
            stanzas[sourcetype] = {}
        
        stanzas[sourcetype]["KV_MODE"] = "json"
        stanzas[sourcetype]["SHOULD_LINEMERGE"] = "false"
        
        for mapping in mappings:
            source_field = mapping.get("source", "")
            target_field = mapping.get("target", "")
            if source_field and target_field and source_field != target_field:
                alias_key = "FIELDALIAS-cim_" + target_field.replace('.', '_')
                if '.' in source_field:
                    stanzas[sourcetype][alias_key] = '"' + source_field + '" AS ' + target_field
                else:
                    stanzas[sourcetype][alias_key] = source_field + " AS " + target_field
        
        self._write_conf_file(conf_path, stanzas)
    
    def _write_eventtypes_conf(self, sourcetype, sourcetype_suffix):
        """Write eventtype definition to eventtypes.conf."""
        conf_path = self._get_local_conf_path("eventtypes")
        stanzas = self._read_conf_file(conf_path)
        eventtype_name = "nexthink_" + sourcetype_suffix.replace(':', '_')
        stanzas[eventtype_name] = {"search": 'sourcetype="' + sourcetype + '"'}
        self._write_conf_file(conf_path, stanzas)
    
    def _write_tags_conf(self, sourcetype, sourcetype_suffix, mappings):
        """Write CIM tags to tags.conf."""
        conf_path = self._get_local_conf_path("tags")
        stanzas = self._read_conf_file(conf_path)
        eventtype_name = "nexthink_" + sourcetype_suffix.replace(':', '_')
        stanza_key = "eventtype=" + eventtype_name
        
        all_tags = set()
        for mapping in mappings:
            tags = mapping.get("tags", [])
            if isinstance(tags, list):
                all_tags.update(tags)
            elif isinstance(tags, str) and tags:
                all_tags.add(tags)
        
        if all_tags:
            stanzas[stanza_key] = dict((tag, "enabled") for tag in all_tags)
        elif stanza_key in stanzas:
            del stanzas[stanza_key]
        
        self._write_conf_file(conf_path, stanzas)
    
    def _remove_cim_config(self, sourcetype, sourcetype_suffix):
        """Remove all CIM configuration for a sourcetype."""
        # Remove from props.conf
        props_path = self._get_local_conf_path("props")
        props_stanzas = self._read_conf_file(props_path)
        if sourcetype in props_stanzas:
            del props_stanzas[sourcetype]
        if props_stanzas:
            self._write_conf_file(props_path, props_stanzas)
        elif os.path.exists(props_path):
            # Write empty file with header
            with open(props_path, 'w') as f:
                f.write("# Auto-generated by " + APP_NAME + " CIM Mapper\n")
        
        # Remove from eventtypes.conf
        eventtypes_path = self._get_local_conf_path("eventtypes")
        eventtype_name = "nexthink_" + sourcetype_suffix.replace(':', '_')
        eventtypes_stanzas = self._read_conf_file(eventtypes_path)
        if eventtype_name in eventtypes_stanzas:
            del eventtypes_stanzas[eventtype_name]
        if eventtypes_stanzas:
            self._write_conf_file(eventtypes_path, eventtypes_stanzas)
        elif os.path.exists(eventtypes_path):
            with open(eventtypes_path, 'w') as f:
                f.write("# Auto-generated by " + APP_NAME + " CIM Mapper\n")
        
        # Remove from tags.conf
        tags_path = self._get_local_conf_path("tags")
        stanza_key = "eventtype=" + eventtype_name
        tags_stanzas = self._read_conf_file(tags_path)
        if stanza_key in tags_stanzas:
            del tags_stanzas[stanza_key]
        if tags_stanzas:
            self._write_conf_file(tags_path, tags_stanzas)
        elif os.path.exists(tags_path):
            with open(tags_path, 'w') as f:
                f.write("# Auto-generated by " + APP_NAME + " CIM Mapper\n")
    
    def _get_all_cim_mappings(self):
        """Get all CIM mappings from props.conf."""
        conf_path = self._get_local_conf_path("props")
        stanzas = self._read_conf_file(conf_path)
        
        results = []
        for stanza_name, settings in stanzas.items():
            if stanza_name.startswith(SOURCETYPE_PREFIX):
                mappings = []
                for key, value in settings.items():
                    if key.startswith("FIELDALIAS-cim_"):
                        # Parse: "source_field" AS target_field or source_field AS target_field
                        match = re.match(r'"?([^"]+)"?\s+AS\s+(\w+)', value)
                        if match:
                            mappings.append({
                                "source": match.group(1),
                                "target": match.group(2)
                            })
                
                if mappings:
                    suffix = stanza_name[len(SOURCETYPE_PREFIX):]
                    tags = self._get_tags_for_sourcetype(suffix)
                    results.append({
                        "sourcetype_suffix": suffix,
                        "sourcetype": stanza_name,
                        "mappings": mappings,
                        "tags": tags
                    })
        
        return results
    
    def _get_mappings_for_sourcetype(self, sourcetype):
        """Get CIM mappings for a specific sourcetype."""
        conf_path = self._get_local_conf_path("props")
        stanzas = self._read_conf_file(conf_path)
        
        mappings = []
        if sourcetype in stanzas:
            for key, value in stanzas[sourcetype].items():
                if key.startswith("FIELDALIAS-cim_"):
                    match = re.match(r'"?([^"]+)"?\s+AS\s+(\w+)', value)
                    if match:
                        mappings.append({
                            "source": match.group(1),
                            "target": match.group(2)
                        })
        
        return mappings
    
    def _get_tags_for_sourcetype(self, sourcetype_suffix):
        """Get CIM tags for a specific sourcetype."""
        conf_path = self._get_local_conf_path("tags")
        stanzas = self._read_conf_file(conf_path)
        
        eventtype_name = "nexthink_" + sourcetype_suffix.replace(':', '_')
        stanza_key = "eventtype=" + eventtype_name
        
        tags = []
        if stanza_key in stanzas:
            tags = list(stanzas[stanza_key].keys())
        
        return tags


admin.init(CIMMapperHandler, admin.CONTEXT_APP_AND_USER)
