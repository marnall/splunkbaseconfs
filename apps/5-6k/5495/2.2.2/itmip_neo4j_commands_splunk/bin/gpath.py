import itmip_neo4j_commands_splunk_declare
#import logging
#import os
import sys
#import time
import re
import json

from splunklib.searchcommands import dispatch, Configuration, Option, GeneratingCommand
from itmip_neo4j_commands_splunk_common import neo4jenvironment  
import splunklib.results as results
import splunklib.client

@Configuration(type='reporting',distributed=False)
class gpath(GeneratingCommand):
    query = None
    debug = False
    output = None
    entities = None
    serviceentities = None
    labelfield = None
    _account = None
    servicedescriptionfield = None
    servicetagfields = None
    servicetemplate = None
    entityaliasses = None
    entitydescription = None
    entityinfos = None
    entitytype = None

    ############
    ## query contains the MATCH path query or multiple path queries in the match and return.
    query = Option(require=True)

    @Option
    def account(self):
        return self._account

    @account.setter
    def account(self, value):
        self._account = value

    @Option
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value):
        self._debug = value

    ############
    ## output can be <cmdb|services|entities|itsi|delta>
    output = Option(require=False)

    ############
    ## entities is a comma seperated list of labels in a string who should be marked as entities
    entities = Option(require=False)

    ############
    ## serviceentities is a comma seperated list of labels in a string who should be marked as both services as entities
    serviceentities = Option(require=False)

    ############
    ## servicedescriptionfield point to the field within the CMDM. If not specified no description output is given
    servicedescriptionfield = Option(require=False)

    ############
    ## servicetagfields should contain a comma seperated string with fields that should be outputted as Service Tags.
    servicetagfields = Option(require=False)

    ############
    ## servicetemplate should contain one valid ITSI ServiceTemplate name
    ## If servicetemplate is used it should also have entityalias and/or entityinfo fields defined together with entities
    servicetemplate = Option(require=False)

    ############
    ## entityaliasses should contain a comma seperated string of fields for the Entity Alias fields
    entityaliasses = Option(require=False)

    ############
    ## entitydescription should contain a field within the CMDM given de description of the Entity. If not specified no Entity Description output is given.
    entitydescription = Option(require=False)

    ############
    ## entityinfos should contain a comma seperated string of fields for the Entity Info fields
    entityinfos = Option(require=False)

    ############
    ## entitytype should contain a field within the CMDM given de type of the Entity. If not specified no EntityType output is given.
    entitytype = Option(require=False)

    ############
    ## If labelfield is not specified it fallsback to the default "name" field that should be common for all nodes
    labelfield = Option(require=False)

    def generate(self):
        #logger = None
        #self.logging_level = "INFO"
        self._debug = bool(self._debug)
        #if self._debug: logger = setup_logging("neo4jsearch")
        if self.account is None:
            account = "neo4j"
        else:
            account = self.account

        if self.labelfield is None:
            self.labelfield = "name"

        try:
            neo4jenv = neo4jenvironment(outerclass=self, account=account, scriptname="gpath", debug=self._debug, statsonly=False)
        except Exception as e:
            self.write_error("Not possible to setup neo4jenvironment: {0}".format(e))
            exit()

        if re.search('(CREATE|DELETE|MERGE)\s+', self.query, re.I):
            self.write_error("Query is not allowed to contain CREATE, DELETE OR MERGE!")
        list_of_output_choices = ['cmdb', 'services', 'entities', 'eduard' , 'itsi', 'delta']
        if not self.output is None and not self.output in list_of_output_choices:
            self.write_error("Field output can only contain the following: <cmdb | services | entities | itsi | delta> and is case sensitive.")
        if not self.output is None and (self.output == "services" or self.output == "entities" or self.output == "itsi" or self.output == "delta"):
            try:
                itsi_app_version = self.service.apps['itsi'].content['version']
            except:
                self.write_error("The requested 'output' cannot succeed as there is NO Splunk ITSI installed on this Splunk environment. Only option is to use output='cmdb'.")
                exit()
        if self.output is None:
            self.output = 'cmdb'
        
        ## check for if servicetemplate that there is either entityaliasses or entityinfos
        if self.servicetemplate and not (self.entityaliasses or self.entityinfos):
            self.write_error("If servicetemplate is specified there must be at least one entityalias or entityinfo specified.")

        #### Start of ITSI services query
        if not self.output is None and (self.output == "services"  or self.output == "delta"):
            params = {
                "fields": "title,_key,description,services_depends_on,services_depending_on_me,service_tags,base_service_template_id,entity_rules,object_type",
                #"filter": '{"title":{"$regex":"Servic.*"}}'
            }
            try:
                response = self.service.get("/servicesNS/nobody/SA-ITOA/itoa_interface/service/", **params)
            except Exception as e:
                self.write_error("Not possible to communicate with ITSI: {0}".format(e))
                exit()
            
            if response and response['status'] == 200:
                neo4jenv.logger2.info("Start reading services response.")
                self.itsi_services = json.loads(response['body'].read())
                neo4jenv.logger2.debug("Result is: {0}".format(self.itsi_services))
                
                for eachdoc in self.itsi_services:
                    neo4jenv.logger2.debug("each service doc is: {0}".format(eachdoc))
                    pass
            else:
                self.write_error("Not possible to communicate with ITSI. HTTP response code is: {0}".format(response['status']))
                exit()
        ###### end of services query

        #### Start of ITSI entities query
        if not self.output is None and (self.output == "entities" or self.output == "services"  or self.output == "delta"):
            params = {
                "fields": "title,_key,_itsi_informational_lookups,_itsi_identifier_lookups",
                #"filter": '{"title":{"$regex":"Servic.*"}}'
            }
            try:
                response = self.service.get("/servicesNS/nobody/SA-ITOA/itoa_interface/entity/", **params)
            except Exception as e:
                self.write_error("Not possible to communicate with ITSI: {0}".format(e))
                exit()
            
            if response and response['status'] == 200:
                neo4jenv.logger2.info("Start reading entities response.")
                self.itsi_entities = json.loads(response['body'].read())
                neo4jenv.logger2.debug("Result is: {0}".format(self.itsi_entities))            
                for eachdoc in self.itsi_entities:
                    neo4jenv.logger2.debug("each entity doc is: {0}".format(eachdoc))
                    pass
            else:
                self.write_error("Not possible to communicate with ITSI. HTTP response code is: {0}".format(response['status']))
                exit()           
        ###### end of entities query

        #### Start of ITSI service templates query
        if not self.output is None and (self.output == "entities" or self.output == "services"  or self.output == "delta"):
            params = {
                "fields": "title,_key",
                #"filter": '{"title":{"$regex":"Servic.*"}}'
            }
            try:
                response = self.service.get("/servicesNS/nobody/SA-ITOA/itoa_interface/base_service_template/", **params)
            except Exception as e:
                self.write_error("Not possible to communicate with ITSI: {0}".format(e))
                exit()
            
            if response and response['status'] == 200:
                neo4jenv.logger2.info("Start reading ITSI templates response.")
                self.itsi_service_templates = json.loads(response['body'].read())
                neo4jenv.logger2.debug("Result is: {0}".format(self.itsi_service_templates))            
                for eachdoc in self.itsi_service_templates:
                    neo4jenv.logger2.debug("each entity doc is: {0}".format(eachdoc))
                    pass
            else:
                self.write_error("Not possible to communicate with ITSI. HTTP response code is: {0}".format(response['status']))
                exit()           
        ###### end of ITSI service templates query
        
        ###### Process the service and entities to combine them so that the entity_ids are updated with titles in the self.itsi_services dict.
        # Also rename the service template id to a name.
        if not self.output is None and (self.output == "services"  or self.output == "delta"):
            for eachservice in self.itsi_services:
                if eachservice['object_type'] == 'service':
                    lservicesdepenindonme = []
                    lservicesdependson = []
                    if 'services_depending_on_me' in eachservice:
                        if eachservice['services_depending_on_me']:
                            for eachservicesdepenindonme in eachservice['services_depending_on_me']:
                                for findservice in self.itsi_services:
                                    if findservice['_key'] == eachservicesdepenindonme['serviceid']:
                                        try:
                                            lservicesdepenindonme.append(findservice['title'])
                                        except:
                                            pass
                                        break
                    else:
                        neo4jenv.logger2.info("Service: {0}, nokey: 'services_depending_on_me'".format(eachservice['title']))
                    eachservice['services_depending_on_me_title'] = lservicesdepenindonme
                    if 'services_depends_on' in eachservice:
                        if eachservice['services_depends_on']:
                            for eachservicesdepenindson in eachservice['services_depends_on']:
                                for findservice in self.itsi_services:
                                    if findservice['_key'] == eachservicesdepenindson['serviceid']:
                                        try:
                                            lservicesdependson.append(findservice['title'])
                                        except:
                                            pass
                                        break
                    else:
                        neo4jenv.logger2.info("Service: {0}, nokey: 'services_depends_on'".format(eachservice['title']))
                    eachservice['services_depends_on_title'] = lservicesdependson
                    relatedentities = []
                    if 'entity_rules' in eachservice:
                        if eachservice['entity_rules']:
                            for eachrule in eachservice['entity_rules']:
                                for entity in self.itsi_entities:
                                    neo4jenv.logger2.debug("value ind rule is: {0}".format(eachrule))
                                    entitymatch = 0
                                    numberdetailedrules = len(eachrule["rule_items"])
                                    for eachdetailedrule in eachrule["rule_items"]:
                                        item = eachdetailedrule
                                        rulevalue = item["value"].replace("*",".*")
                                        ruleterm = item["field"] + "=" + rulevalue
                                        if item["field_type"] == "title":
                                            if item["rule_type"] == "matches" and re.match(rulevalue, entity["title"]):
                                                entitymatch += 1
                                            if item["rule_type"] == "not" and not re.match(rulevalue, entity["title"]):
                                                entitymatch += 1
                                        elif item["field_type"] == "alias":
                                            if entity["_itsi_identifier_lookups"]:
                                                for eachalias in entity["_itsi_identifier_lookups"]:
                                                    if item["rule_type"] == "matches" and re.match(ruleterm, eachalias):
                                                        entitymatch += 1
                                                    if item["rule_type"] == "not" and not re.match(ruleterm, eachalias):
                                                        entitymatch += 1
                                        elif item["field_type"] == "info":
                                            if entity["_itsi_informational_lookups"]:
                                                for eachinfo in entity["_itsi_informational_lookups"]:
                                                    if item["rule_type"] == "matches" and re.match(ruleterm, eachinfo):
                                                        entitymatch += 1
                                                    if item["rule_type"] == "not" and not re.match(ruleterm, eachinfo):
                                                        entitymatch += 1
                                    if eachrule["rule_condition"] == "AND" and entitymatch == numberdetailedrules:
                                        relatedentities.append(entity["title"])
                                    elif eachrule["rule_condition"] == "OR" and entitymatch > 1:
                                        relatedentities.append(entity["title"])
                    else:
                        neo4jenv.logger2.info("Service: {0}, nokey: 'entity_rules'".format(eachservice['title']))
                    eachservice['relatedentities'] = relatedentities
                    # process the service template id.
                    eachservice["base_service_template_name"] = ""
                    if eachservice['base_service_template_id']:
                        for template in self.itsi_service_templates:
                            if eachservice['base_service_template_id'] == template['_key']:
                                eachservice["base_service_template_name"] = template['title']
                                break
                    else:
                        eachservice["base_service_template_name"] = ""
                    # end processing of service templates
        ###### end processing
        
        ###### Start reading the CMDB pathes
        self.cmdb_items = []
        self.entitylabels = []
        self.serviceentitylabels = []
        if not self.entities is None:
            lentities = self.entities.split(",")
            for eachentity in lentities:
                self.entitylabels.append(eachentity.strip())
        if not self.serviceentities is None:
            lserviceentities = self.serviceentities.split(",")
            for eachserviceentity in lserviceentities:
                self.serviceentitylabels.append(eachserviceentity.strip())
        if not self.output is None and (self.output == "cmdb" or self.output == "itsi" or self.output == "delta"):
            outcome = neo4jenv.execute_path_query(query=self.query, data='')
            if outcome:
                for rel in outcome:
                    #####
                    # Need to add servicetemplatefield. If template field then the entity needs Info and Alias fields
                    # So it needs multiple tags for services, multiple info and alias fields, service description
                    # Need to add the list of fields that should be retrieved for the entities
                    # 
                    #####
                    # The followin list of property name-value pairs. But you can check with key in node or node[key]
                    #if self._debug: logger.info(rel.start_node.items())
                    for relationship in rel['graph']['relationships']:
                        start_node = relationship['startNode']
                        for index, node in enumerate(rel['graph']['nodes']):
                        #for node in rel['nodes']:
                            if node['id'] == start_node:
                                startnl = node['labels']
                                startindex = index
                            else:
                                endnl = node['labels']
                                endindex = index
                        #logger.info(rel.start_node)  #printing everything about the node labels and properties.
                        # ouput = <Node id=7061 labels=set([u'k8sNode']) properties={u'name': u'lab'}>
                        itsistarttype, itsiendtype = "S", "S"
                        if [x for x in startnl if x in self.entitylabels]:
                            itsistarttype = "E"
                        elif [x for x in startnl if x in self.serviceentitylabels]:
                            itsistarttype = "B"
                        if [x for x in endnl if x in self.entitylabels]:
                            itsiendtype = "E"
                        elif [x for x in endnl if x in self.serviceentitylabels]:
                            itsiendtype = "B"
                        startnlstr = ""
                        if len(startnl) >1:
                            for labelstart in startnl:
                                startnlstr += labelstart + ","
                        else:
                            startnlstr = startnl
                        endnlstr = ""
                        if len(endnl) >1:
                            for labelend in endnl:
                                endnlstr += labelend + ","
                        else:
                            endnlstr = endnl

                        basedict = dict({"startnode":  rel['graph']['nodes'][startindex]['properties'][self.labelfield], "startlabel": startnlstr, "endnode": rel['graph']['nodes'][endindex]['properties'][self.labelfield], "endlabel": endnlstr, "reltype": relationship['type'], "starttypeitsi": itsistarttype, "endtypeitsi": itsiendtype})

                        if self.servicedescriptionfield:
                            ddescription = {}
                            ddescription["service_description"] =  rel['graph']['nodes'][startindex]['properties'].get(self.servicedescriptionfield, "")
                            basedict.update(ddescription)

                        if self.servicetagfields:
                            lservicetagfields = self.servicetagfields.split(",")
                            sertagnr = 0
                            dservicetags = {}
                            for tagfield in lservicetagfields:
                                sertagnr += 1
                                outputtag = "service_tag"+str(sertagnr)+"_"+tagfield
                                dservicetags[outputtag] =  rel['graph']['nodes'][startindex]['properties'].get(tagfield, "")
                            basedict.update(dservicetags)

                        if self.servicetemplate:
                            dservicetemplate = {}
                            dservicetemplate["service_template"] =  rel['graph']['nodes'][startindex]['properties'].get(self.servicetemplate, "")
                            basedict.update(dservicetemplate)
    
                        if self.entitydescription:
                            dentitydescription = {}
                            if itsiendtype == "E" or itsiendtype == "B":
                                dentitydescription["endentity_description"] = rel['graph']['nodes'][endindex]['properties'].get(self.entitydescription, "")
                            else:
                                dentitydescription["endentity_description"] = ""
                            basedict.update(dentitydescription)
    
                        if self.entityaliasses:
                            lentityaliasses = self.entityaliasses.split(",")
                            enaliasnr = 0
                            dentityaliass = {}
                            if itsiendtype == "E" or itsiendtype == "B":
                                for alias in lentityaliasses:
                                    enaliasnr += 1
                                    outputalias = "endentity_alias"+str(enaliasnr)+"_"+alias
                                    dentityaliass[outputalias] = rel['graph']['nodes'][endindex]['properties'].get(alias, "")
                            else:
                                for alias in lentityaliasses:
                                    enaliasnr += 1
                                    outputalias = "endentity_alias"+str(enaliasnr)+"_"+alias
                                    dentityaliass[outputalias] = ""
                            basedict.update(dentityaliass)
    
                        if self.entityinfos:
                            lentityinfos = self.entityinfos.split(",")
                            eninfonr = 0
                            dentityinfos = {}
                            if itsiendtype == "E" or itsiendtype == "B":
                                for info in lentityinfos:
                                    eninfonr += 1
                                    outputinfo = "endentity_info"+str(eninfonr)+"_"+info
                                    dentityinfos[outputinfo] = rel['graph']['nodes'][endindex]['properties'].get(info, "")
                            else:
                                for info in lentityinfos:
                                    eninfonr += 1
                                    outputinfo = "endentity_info"+str(eninfonr)+"_"+info
                                    dentityinfos[outputinfo] = ""
                            basedict.update(dentityinfos)
                        
                        if self.entitytype:
                            dentitytype = {}
                            if itsiendtype == "E" or itsiendtype == "B":
                                dentitytype["endentity_type"] = rel['graph']['nodes'][endindex]['properties'].get(self.entitytype, "")
                            else:
                                dentitytype["endentity_type"] = ""
                            basedict.update(dentitytype)
     
                        self.cmdb_items.append(basedict)
        ###### End reading the CMDB pathes

        ###### Start doing processing of the CMDB table to ITSI format
        if not self.output is None and (self.output == "itsi"):
            self.cmdbtoitsi = {}
            for ciis in self.cmdb_items:
                keyid = ciis['startnode'] + ciis['endnode']
                if not keyid in self.cmdbtoitsi:
                    if ciis['starttypeitsi'] == 'S':
                        service = ciis['startnode']
                    else:
                        self.write_error("Splunk ITSI is not supporting that a starting node is an Entity or Both, should alwasy be Service.")
                        exit()
                    if ciis['endtypeitsi'] == 'S':
                        dependingservice = ciis['endnode']
                        entitytitle = ""
                    elif ciis['endtypeitsi'] == 'E':
                        entitytitle = ciis['endnode']
                        dependingservice = ""
                    elif ciis['endtypeitsi'] == 'B':
                        entitytitle = ciis['endnode']
                        dependingservice = ciis['endnode']
                    doutput = {}
                    doutput["ServiceTitle"] = service
                    doutput["DependentService"] = dependingservice
                    doutput["EntityTitle"] = entitytitle
                    for key in ciis:
                        if key=="starttypeitsi" or key=="endtypeitsi" or key=="startnode" or key=="endnode" or key=="startlabel" or key=="endlabel" or key=="reltype":
                            continue
                        doutput[key] = ciis[key]
                    self.cmdbtoitsi[keyid] = doutput
                    ###self.cmdbtoitsi[keyid] = dict({"ServiceTitle": service , "DependentService": dependingservice, "EntityTitle": entitytitle})
                    #####
                    # What about ServiceDescription, ServiceTags123, ServiceTemplate
                    # What about EntityDescription, EntityAlias,EntityInformation,EntityType
        ###### End

        ###### Processing delta between CMDB and ITSI
        if not self.output is None and (self.output == "delta"):
            self.itsi_services_delta = {}
            for ciis in self.cmdb_items:
                uuid = ciis['startnode'] + ciis['endnode']
                if not uuid in self.itsi_services_delta:
                    startnodematch = 0
                    endentitymatch = 0
                    endnodematch = 0
                    #relatedservices = set()
                    for serviceid in self.itsi_services:
                        if ciis['startnode'] == serviceid['title']:
                            startnodematch = 1
                            #for servid in self.itsi_services[serviceid]['services_depends_on']:
                            #    relatedservices.add(servid)
                            #for servid in self.itsi_services[serviceid]['services_depending_on_me']:
                            #    relatedservices.add(servid)
                        if ciis['endtypeitsi'] == 'S':
                            if ciis['endnode'] == serviceid['title']:
                                endnodematch = 1
                        elif ciis['endtypeitsi'] == 'E':
                            if ciis['endnode'] in serviceid['relatedentities']:
                                endentitymatch = 1
                            if ciis['endnode'] == serviceid['title']:
                                endnodematch = 1
                            pass
                        elif ciis['endtypeitsi'] == 'B':
                            if ciis['endnode'] in serviceid['relatedentities']:
                                endentitymatch = 1
                            if ciis['endnode'] == serviceid['title']:
                                endnodematch = 1
                    if startnodematch or endnodematch:
                        pass
                    self.itsi_services_delta[uuid] = ciis
                    outcome = {'startnodematch': startnodematch, 'endentitymatch': endentitymatch, 'endnodematch': endnodematch}
                    self.itsi_services_delta[uuid].update(outcome)
        ###### End

        ###### Outputting section
        if not self.output is None and (self.output == "services"):
            for key in self.itsi_services:
                yield key
        if not self.output is None and (self.output == "itsi"):
            ####### Here we do the processing in a format that ITSI understands
            #self.cmdb_items
            for key in self.cmdbtoitsi:
                yield self.cmdbtoitsi[key]
                #if self.itsi_services[key]['type'] == 'service':
                #    yield self.itsi_services[key]
        if not self.output is None and self.output == "entities":
            for result in self.itsi_entities:
                yield result
        if not self.output is None and self.output == "cmdb":
            for result in self.cmdb_items:
                yield result
        if not self.output is None and self.output == "delta":
            for result in self.itsi_services_delta:
                yield self.itsi_services_delta[result]
        ###### End Outputting section

if __name__ == "__main__":
    dispatch(gpath, sys.argv, sys.stdin, sys.stdout, __name__)
