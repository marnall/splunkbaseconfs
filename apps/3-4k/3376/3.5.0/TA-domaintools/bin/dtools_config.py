import splunk.admin as admin
import splunk.entity as en
import splunk.rest
# from urlparse import urlparse
import json
from Utils.app_env import AppEnv

'''
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values
      corresponds to handleractions = edit in restmap.conf

'''


class DToolsConfig(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['api_key', 'username', 'min_tp_risk', 'min_prox_risk', 'populatingsearch_enabled',
                        'workflow_enabled', 'score_type', 'disabled',
                        'data_cache_length', 'search', 'use_ssl', 'summary_index', 'per_minute_limit',
                        'populating_search_run_interval', 'summary_search_run_interval', 'summary_search_run_cron',
                        'proxy_url', 'domains_observed_data', 'critical_domains_observed', 'total_critical_events',
                        'phisheye_domains_observed', 'total_phisheye_events', 'monitoring_timecharts_data',
                        'monitoring_timechart_events']:
                self.supportedArgs.addOptArg(arg)

    '''
    Read the initial values of the parameters from the custom file
        myappsetup.conf, and write them to the setup page.

    If the app has never been set up,
        uses ./static/app_name/default/myappsetup.conf.

    If app has been set up, looks at
        .../local/myappsetup.conf first, then looks at
    .../default/myappsetup.conf only if there is no value for a field in
        .../local/myappsetup.conf

    For boolean fields, may need to switch the true/false setting.

    For text fields, if the conf file says None, set to the empty string.
    '''

    def getCredentials(self):
        """Get the api_key from the Splunk password store.
        """
        sessionKey = self.getSessionKey()
        headers, payloadstr = splunk.rest.simpleRequest('/services/domaintools_credentials', method='POST',
                                                        sessionKey=sessionKey,
                                                        postargs={})
        payload = json.loads(payloadstr)
        if 'username' in payload:
            return payload['username'], payload['password']
        return '', ''

    def handleList(self, confInfo):
        s = self.getSessionKey()
        app_env = AppEnv()
        confDict = self.readConfCtx("domaintools")

        confInfo["config"]["username"], confInfo["config"]["api_key"] = self.getCredentials()
        if confDict is not None:
            for key, val in confDict['domaintools'].items():
                # if key == 'proxy_url':
                #     try:
                #         url = urlparse(val)
                #         confInfo['config'].append(key, '{0}://{1}'.format(url.scheme, url.netloc))
                #     except Exception as ex:
                #         pass
                # else:
                confInfo['config'].append(key, val)
            try:
                splunk.entity.getEntity('/apps/local', 'SplunkEnterpriseSecuritySuite',
                                        namespace=app_env.package_id, sessionKey=s, owner='nobody')
            except splunk.ResourceNotFound:
                confInfo["config"]["es_installed"] = 0
        else:
            confInfo["config"]["es_installed"] = 1

        confInfo["config"]["search"] = en.getEntity(
            '/configs/conf-macros', 'dt_base_search', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']
        confInfo["config"]["domains_observed_data"] = en.getEntity(
            '/configs/conf-macros', 'domains_observed_data', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']
        confInfo["config"]["critical_domains_observed"] = en.getEntity(
            '/configs/conf-macros', 'critical_domains_observed', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']
        confInfo["config"]["total_critical_events"] = en.getEntity(
            '/configs/conf-macros', 'total_critical_events', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']
        confInfo["config"]["phisheye_domains_observed"] = en.getEntity(
            '/configs/conf-macros', 'phisheye_domains_observed', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']
        confInfo["config"]["total_phisheye_events"] = en.getEntity(
            '/configs/conf-macros', 'total_phisheye_events', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']
        confInfo["config"]["monitoring_timecharts_data"] = en.getEntity(
            '/configs/conf-macros', 'monitoring_timecharts_data', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']
        confInfo["config"]["monitoring_timechart_events"] = en.getEntity(
            '/configs/conf-macros', 'monitoring_timechart_events', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']
        confInfo["config"]["summary_index"] = en.getEntity(
            '/configs/conf-macros', 'summary_index', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']

        confInfo["config"]["min_tp_risk"] = splunk.entity.getEntity(
            '/configs/conf-macros', 'min_tp_risk', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']
        confInfo["config"]["min_prox_risk"] = splunk.entity.getEntity(
            '/configs/conf-macros', 'min_prox_risk', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']
        confInfo["config"]["data_cache_length"] = int(splunk.entity.getEntity(
            '/configs/conf-macros', 'data_cache_length', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition'])/86400
        whois_populatingsearch_disabled = splunk.entity.getEntity(
            '/saved/searches', 'DomainTools Enterprise - API Enrichment First Pass KV Store', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['disabled']
        iris_populatingsearch_disabled = splunk.entity.getEntity(
            '/saved/searches', 'DomainTools Iris - API Enrichment First Pass KV Store', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['disabled']
        confInfo["config"]["populating_search_run_interval"] = splunk.entity.getEntity(
            '/configs/conf-macros', 'populating_search_run_interval', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']
        confInfo["config"]["summary_search_run_interval"] = splunk.entity.getEntity(
            '/configs/conf-macros', 'summary_search_run_interval', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']

        if whois_populatingsearch_disabled in ["0", "false", "False"]:
            whois_populatingsearch_disabled = True
        else:
            whois_populatingsearch_disabled = False
        if iris_populatingsearch_disabled in ["0", "false", "False"]:
            iris_populatingsearch_disabled = True
        else:
            iris_populatingsearch_disabled = False
        if whois_populatingsearch_disabled and iris_populatingsearch_disabled:
            confInfo["config"]["populatingsearch_enabled"] = "0"
        else:
            confInfo["config"]["populatingsearch_enabled"] = "1"

        workflow_disabled = splunk.entity.getEntity(
            '/configs/conf-workflow_actions', 'dts_es_whois_domainprofile_dashboard', namespace=app_env.package_id,
            sessionKey=s, owner='nobody')['disabled']
        if workflow_disabled in ["0", "false", "False"]:
            workflow_enabled = "1"
        else:
            workflow_enabled = "0"
        confInfo["config"]["workflow_enabled"] = workflow_enabled
        dt_api_enrich_cmd = splunk.entity.getEntity(
            '/configs/conf-macros', 'dt_api_enrich_cmd', namespace=app_env.package_id, sessionKey=s,
            owner='nobody')['definition']
        if dt_api_enrich_cmd == "noop":
            confInfo["config"]["score_type"] = ""
        elif dt_api_enrich_cmd == "domaintools domain mode=whois_parsed silent=t":
            confInfo["config"]["score_type"] = ""
        elif dt_api_enrich_cmd == "domaintools domain mode=reputation silent=t":
            confInfo["config"]["score_type"] = "reputation"
        elif dt_api_enrich_cmd == "domaintools domain mode=whois_reputation silent=t":
            confInfo["config"]["score_type"] = "reputation"
        elif dt_api_enrich_cmd == "domaintools domain mode=whois_risk silent=t":
            confInfo["config"]["score_type"] = "risk"
        elif dt_api_enrich_cmd == "domaintools domain mode=iris_enrich field=domain silent=t":
            confInfo["config"]["score_type"] = "iris_enrich"

    '''
    After user clicks Save on setup page, take updated parameters,
    normalize them, and save them somewhere
    '''

    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs
        app_env = AppEnv()

        '''
        Since we are using a conf file to store parameters, write them to the [setupentity] stanza
        in app_name/local/myappsetup.conf
        '''
        if 'summary_index' in args and args['summary_index'][0] is None:
            args['summary_index'][0] = 'summary'
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/summary_index'.format(
                app_env.package_id), postargs={
                'definition': args['summary_index'][0]}, method='POST', sessionKey=self.getSessionKey())
        if 'min_tp_risk' in args:
            if args['min_tp_risk'][0] is None:
                min_tp_risk = 90
            else:
                min_tp_risk = args['min_tp_risk'][0]
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/min_tp_risk'.format(
                app_env.package_id), postargs={
                'definition': min_tp_risk}, method='POST', sessionKey=self.getSessionKey())
        if 'min_prox_risk' in args:
            if args['min_prox_risk'][0] is None:
                min_prox_risk = 70
            else:
                min_prox_risk = args['min_prox_risk'][0]
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/min_prox_risk'.format(
                app_env.package_id), postargs={
                'definition': min_prox_risk}, method='POST', sessionKey=self.getSessionKey())
        if 'data_cache_length' in args:
            if args['data_cache_length'][0] is not None:
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/data_cache_length'.format(
                    app_env.package_id), postargs={
                    'definition': int(args['data_cache_length'][0])*86400}, method='POST', sessionKey=self.getSessionKey())
            else:
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/data_cache_length'.format(
                    app_env.package_id), postargs={
                    'definition': 30*86400}, method='POST', sessionKey=self.getSessionKey())

        domaintoolsConfig = {}

        if 'score_type' in args:
            score_type = args['score_type'][0]
            domaintoolsConfig['score_type'] = score_type

        if 'use_ssl' in args:
            use_ssl = args['use_ssl'][0]
            domaintoolsConfig['use_ssl'] = use_ssl

        if 'populatingsearch_enabled' in args:
            populatingsearch_enabled = args['populatingsearch_enabled'][0]
            domaintoolsConfig['whois'] = populatingsearch_enabled

        # if 'proxy_url' in args:
        #     try:
        #         proxy_url = urlparse(args['proxy_url'][0])
        #         domaintoolsConfig['proxy_url'] = '{0}://{1}'.format(url.scheme, url.netloc)
        #     except Exception as ex:
        #         pass

        if 'summary_search_run_interval' in args:
            summary_search_run_interval = args['summary_search_run_interval'][0]
        else:
            summary_search_run_interval = 15
        splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/summary_search_run_interval'.format(
            app_env.package_id), postargs={
            'definition': summary_search_run_interval}, method='POST', sessionKey=self.getSessionKey())

        dispatch_earliest_time = '-{0}m@m'.format(summary_search_run_interval)
        if 'summary_search_run_cron' in args:
            summary_search_run_cron = args['summary_search_run_cron'][0]
        else:
            summary_search_run_cron = '*/15 * * * *'
        domaintoolsConfig['summary_search_run_cron'] = summary_search_run_cron

        splunk.rest.simpleRequest('/servicesNS/nobody/{0}/configs/conf-domaintools/domaintools'.format(
            app_env.package_id), postargs=domaintoolsConfig, method='POST', sessionKey=self.getSessionKey())
        # KLUDGE: Repeated api calls here can be consolidated to one function.
        if 'search' in args:
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/dt_base_search'.format(
                app_env.package_id), postargs={
                'definition': args['search'][0]}, method='POST', sessionKey=self.getSessionKey())

        if 'domains_observed_data' in args:
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/domains_observed_data'.format(
                app_env.package_id), postargs={
                'definition': args['domains_observed_data'][0]}, method='POST', sessionKey=self.getSessionKey())

        if 'critical_domains_observed' in args:
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/critical_domains_observed'.format(
                app_env.package_id), postargs={
                'definition': args['critical_domains_observed'][0]}, method='POST', sessionKey=self.getSessionKey())

        if 'total_critical_events' in args:
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/total_critical_events'.format(
                app_env.package_id), postargs={
                'definition': args['total_critical_events'][0]}, method='POST', sessionKey=self.getSessionKey())

        if 'phisheye_domains_observed' in args:
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/phisheye_domains_observed'.format(
                app_env.package_id), postargs={
                'definition': args['phisheye_domains_observed'][0]}, method='POST', sessionKey=self.getSessionKey())

        if 'total_phisheye_events' in args:
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/total_phisheye_events'.format(
                app_env.package_id), postargs={
                'definition': args['total_phisheye_events'][0]}, method='POST', sessionKey=self.getSessionKey())

        if 'monitoring_timecharts_data' in args:
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/monitoring_timecharts_data'.format(
                app_env.package_id), postargs={
                'definition': args['monitoring_timecharts_data'][0]}, method='POST', sessionKey=self.getSessionKey())

        if 'monitoring_timechart_events' in args:
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/monitoring_timechart_events'.format(
                app_env.package_id), postargs={
                'definition': args['monitoring_timechart_events'][0]}, method='POST', sessionKey=self.getSessionKey())

        if 'summary_index' in args:
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/summary_index'.format(
                app_env.package_id), postargs={
                'definition': args['summary_index'][0]}, method='POST', sessionKey=self.getSessionKey())

        if 'workflow_enabled' in args:
            if args['workflow_enabled'][0] == '1':
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/data/ui/workflow-actions/dts_es_whois_domainprofile_dashboard'.format(
                    app_env.package_id), postargs={'disabled': 0}, method='POST', sessionKey=self.getSessionKey())
            elif args['workflow_enabled'][0] == '0':
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/data/ui/workflow-actions/dts_es_whois_domainprofile_dashboard'.format(
                    app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())

        if 'per_minute_limit' in args:
            per_minute_limit = args['per_minute_limit'][0]
        else:
            per_minute_limit = 60
        splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/per_minute_limit'.format(
            app_env.package_id), postargs={
            'definition': args['per_minute_limit'][0]}, method='POST', sessionKey=self.getSessionKey())

        if 'populating_search_run_interval' in args:
            populating_search_run_interval = args['populating_search_run_interval'][0]
        else:
            populating_search_run_interval = 5
        splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/populating_search_run_interval'.format(
            app_env.package_id), postargs={
            'definition': args['populating_search_run_interval'][0]}, method='POST', sessionKey=self.getSessionKey())

        splunk.rest.simpleRequest(
            '/servicesNS/nobody/{0}/saved/searches/DomainTools%20Threat%20Hunting%20-%20Total%20Domain%20Event%20Count%20Summary%20Index'.format(
                app_env.package_id),
            postargs={
                'cron_schedule': summary_search_run_cron,
                'dispatch.earliest_time': dispatch_earliest_time
            },
            method='POST',
            sessionKey=self.getSessionKey())
        splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Threat%20Hunting%20-%20Newly%20Observed%20Domains%20Summary%20Index'.format(
            app_env.package_id),
            postargs={
            'cron_schedule': summary_search_run_cron,
            'dispatch.earliest_time': dispatch_earliest_time
        },
            method='POST',
            sessionKey=self.getSessionKey())
        splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Threat%20Hunting%20-%20Registrant%20Country%20Codes%20from%20High%20Risk%20Domains'.format(
            app_env.package_id),
            postargs={
            'cron_schedule': summary_search_run_cron,
            'dispatch.earliest_time': dispatch_earliest_time
        },
            method='POST',
            sessionKey=self.getSessionKey())
        splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Threat%20Hunting%20-%20Risk%20Level%20Summary%20Index'.format(
            app_env.package_id),
            postargs={
            'cron_schedule': summary_search_run_cron,
            'dispatch.earliest_time': dispatch_earliest_time
        },
            method='POST',
            sessionKey=self.getSessionKey())
        splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Threat%20Hunting%20-%20Risky%20Registrant%20Emails%20Summary%20Index'.format(
            app_env.package_id),
            postargs={
            'cron_schedule': summary_search_run_cron,
            'dispatch.earliest_time': dispatch_earliest_time
        },
            method='POST',
            sessionKey=self.getSessionKey())
        splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Threat%20Hunting%20-%20Risky%20Registrants%20Summary%20Index'.format(
            app_env.package_id),
            postargs={
            'cron_schedule': summary_search_run_cron,
            'dispatch.earliest_time': dispatch_earliest_time
        },
            method='POST',
            sessionKey=self.getSessionKey())
        splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Threat%20Hunting%20-%20Risky%20Registrars%20Summary%20Index'.format(
            app_env.package_id),
            postargs={
            'cron_schedule': summary_search_run_cron,
            'dispatch.earliest_time': dispatch_earliest_time
        },
            method='POST',
            sessionKey=self.getSessionKey())
        splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Threat%20Hunting%20-%20Diagnostics%20-%20API%20Usage%20Count%20Summary%20Index'.format(
            app_env.package_id),
            postargs={
            'cron_schedule': summary_search_run_cron,
            'dispatch.earliest_time': dispatch_earliest_time
        },
            method='POST',
            sessionKey=self.getSessionKey())
        splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Threat%20Hunting%20-%20Diagnostics%20-%20API%20Overage%20Analysis%20Summary%20Index'.format(
            app_env.package_id),
            postargs={
            'cron_schedule': summary_search_run_cron,
            'dispatch.earliest_time': dispatch_earliest_time
        },
            method='POST',
            sessionKey=self.getSessionKey())

        # switch macros for whois/iris_enrich
        if score_type == 'iris_enrich':
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/dt_lookup_queue'.format(
                app_env.package_id), postargs={
                'definition': 'iris_lookup_queue'}, method='POST', sessionKey=self.getSessionKey())
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/dt_lookup_history'.format(
                app_env.package_id), postargs={
                'definition': 'iris_lookup_history'}, method='POST', sessionKey=self.getSessionKey())
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/dt_api_enrich_cmd'.format(
                app_env.package_id), postargs={
                'definition': 'domaintools domain mode=iris_enrich field=domain silent=t'},
                method='POST', sessionKey=self.getSessionKey())

            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Iris%20-%20Domain%20Name%20Queue%20Builder%20KV%20Store'.format(
                app_env.package_id), postargs={'disabled': 0}, method='POST', sessionKey=self.getSessionKey())

            if int(populatingsearch_enabled) == 1:
                # self.writeConf('savedsearches', 'Iris Queue Builder', {'disabled': '0'})
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Iris%20-%20Domain%20Name%20Queue%20Builder%20KV%20Store'.format(
                    app_env.package_id), postargs={'disabled': 0}, method='POST', sessionKey=self.getSessionKey())
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Iris%20-%20API%20Enrichment%20First%20Pass%20KV%20Store'.format(
                    app_env.package_id), postargs={'disabled': 0}, method='POST', sessionKey=self.getSessionKey())
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Iris%20-%20API%20Enrichment%20Second%20Pass%20KV%20Store'.format(
                    app_env.package_id), postargs={'disabled': 0}, method='POST', sessionKey=self.getSessionKey())

            else:
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Iris%20-%20Domain%20Name%20Queue%20Builder%20KV%20Store'.format(
                    app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Iris%20-%20API%20Enrichment%20First%20Pass%20KV%20Store'.format(
                    app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Iris%20-%20API%20Enrichment%20Second%20Pass%20KV%20Store'.format(
                    app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Iris%20-%20Whois%20Index%20Populator'.format(
                    app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())

            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Enterprise%20-%20Domain%20Name%20Queue%20Builder%20KV%20Store'.format(
                app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Enterprise%20-%20API%20Enrichment%20First%20Pass%20KV%20Store'.format(
                app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Enterprise%20-%20API%20Enrichment%20Second%20Pass%20KV%20Store'.format(
                app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Enterprise%20-%20Whois%20Index%20Populator'.format(
                app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())

            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/cron_limit'.format(
                app_env.package_id), postargs={
                'definition': int(
                    int(populating_search_run_interval)*int(per_minute_limit)*100*.9)},
                method='POST', sessionKey=self.getSessionKey())

        else:
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/dt_lookup_queue'.format(
                app_env.package_id), postargs={
                'definition': 'whois_lookup_queue'}, method='POST', sessionKey=self.getSessionKey())
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/dt_lookup_history'.format(
                app_env.package_id), postargs={
                'definition': 'whois_lookup_history'}, method='POST', sessionKey=self.getSessionKey())

            if score_type == 'risk':
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/dt_api_enrich_cmd'.format(
                    app_env.package_id), postargs={
                    'definition': 'domaintools domain mode=whois_risk silent=t'},
                    method='POST', sessionKey=self.getSessionKey())
            elif score_type == 'reputation':
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/dt_api_enrich_cmd'.format(
                    app_env.package_id), postargs={
                    'definition': 'domaintools domain mode=whois_reputation silent=t'},
                    method='POST', sessionKey=self.getSessionKey())

            if int(populatingsearch_enabled) == 1:
                # self.writeConf('savedsearches', 'Domain Analysis Queue Builder', {'disabled': '0'})
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Enterprise%20-%20Domain%20Name%20Queue%20Builder%20KV%20Store'.format(
                    app_env.package_id), postargs={'disabled': 0}, method='POST', sessionKey=self.getSessionKey())
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Enterprise%20-%20API%20Enrichment%20First%20Pass%20KV%20Store'.format(
                    app_env.package_id), postargs={'disabled': 0}, method='POST', sessionKey=self.getSessionKey())
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Enterprise%20-%20API%20Enrichment%20Second%20Pass%20KV%20Store'.format(
                    app_env.package_id), postargs={'disabled': 0}, method='POST', sessionKey=self.getSessionKey())

            else:
                # self.writeConf('savedsearches', 'Domain Analysis Queue Builder', {'disabled': '1'})
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Enterprise%20-%20Domain%20Name%20Queue%20Builder%20KV%20Store'.format(
                    app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Enterprise%20-%20API%20Enrichment%20First%20Pass%20KV%20Store'.format(
                    app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Enterprise%20-%20Whois%20Index%20Populator'.format(
                    app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())
                splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Enterprise%20-%20API%20Enrichment%20Second%20Pass%20KV%20Store'.format(
                    app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())

            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Iris%20-%20Domain%20Name%20Queue%20Builder%20KV%20Store'.format(
                app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Iris%20-%20API%20Enrichment%20First%20Pass%20KV%20Store'.format(
                app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Iris%20-%20API%20Enrichment%20Second%20Pass%20KV%20Store'.format(
                app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())
            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/DomainTools%20Iris%20-%20Whois%20Index%20Populator'.format(
                app_env.package_id), postargs={'disabled': 1}, method='POST', sessionKey=self.getSessionKey())

            splunk.rest.simpleRequest('/servicesNS/nobody/{0}/admin/macros/cron_limit'.format(
                app_env.package_id), postargs={
                'definition': int(
                    int(populating_search_run_interval)*int(per_minute_limit)*.9)},
                method='POST', sessionKey=self.getSessionKey())


# initialize the handler
admin.init(DToolsConfig, admin.CONTEXT_NONE)
