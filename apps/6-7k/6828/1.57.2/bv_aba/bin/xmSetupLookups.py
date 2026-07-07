# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import fnmatch
import os
import re
import csv
import sys
import time
import platform
import saUtils
import shutil
import splunk.Intersplunk as si
from xml.dom.minidom import parseString
import splunk.rest
import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':
    try:
        print ('Response')

        splunkHome=os.environ.get('SPLUNK_HOME')

        defaultResourceMappingFile=splunkHome + "/etc/apps/bv_aba/config/resource-mapping-default.json"
        resourceMappingFile=splunkHome + "/etc/apps/bv_aba/config/resource-mapping.json"
        # in case of upgrade - don't overwrite existing resource-mapping file
        if not os.path.exists(resourceMappingFile):
            shutil.copyfile(defaultResourceMappingFile,resourceMappingFile)
            logger.info("xmSetupLookup - Seeded " + resourceMappingFile)

        defaultCategoriesFile=splunkHome + "/etc/apps/bv_aba/lookups/categories-default.csv"
        categoriesFile=splunkHome + "/etc/apps/bv_aba/lookups/categories.csv"
        # in case of upgrade - don't overwrite existing categories file
        if not os.path.exists(categoriesFile):
            shutil.copyfile(defaultCategoriesFile,categoriesFile)
            logger.info("xmSetupLookup - Seeded " + categoriesFile)

        initAssetsFile=splunkHome + "/etc/apps/bv_aba/lookups/bv_assets-default.csv"
        assetsFile=splunkHome + "/etc/apps/bv_aba/lookups/bv_assets.csv"
        # in case of upgrade - don't overwrite existing assets file
        if not os.path.exists(assetsFile):
            shutil.copyfile(initAssetsFile,assetsFile)
            logger.info("xmSetupLookup - Seeded " + assetsFile)

        initActorsFile=splunkHome + "/etc/apps/bv_aba/lookups/bv_actors-default.csv"
        actorsFile=splunkHome + "/etc/apps/bv_aba/lookups/bv_actors.csv"
        # in case of upgrade - don't overwrite existing actors file
        if not os.path.exists(actorsFile):
            shutil.copyfile(initActorsFile,actorsFile)
            logger.info("xmSetupLookup - Seeded " + actorsFile)

        #defaultDataDictionaryFile=splunkHome + "/etc/apps/bv_aba/config/data-dictionary-default.json"
        #dataDictionaryFile=splunkHome + "/etc/apps/bv_aba/config/data-dictionary.json"
        # in case of upgrade - don't overwrite existing data dictionaries file
        #if not os.path.exists(dataDictionaryFile):
        #    shutil.copyfile(defaultDataDictionaryFile,dataDictionaryFile)
        #    logger.info("xmSetupLookup - Seeded " + dataDictionaryFile)

        defaultPropertiesFile=splunkHome + "/etc/apps/bv_aba/config/scm-framework-default.properties"
        propertiesFile=splunkHome + "/etc/apps/bv_aba/config/scm-framework.properties"
        # in case of upgrade - don't overwrite existing scm-framework.properties file
        if not os.path.exists(propertiesFile):
            shutil.copyfile(defaultPropertiesFile,propertiesFile)
            logger.info("xmSetupLookup - Seeded " + propertiesFile)

        defaultSavedSearchesFile=splunkHome + "/etc/apps/bv_aba/default/savedsearches.default"
        savedSearchesFile=splunkHome + "/etc/apps/bv_aba/default/savedsearches.conf"
        # in case of upgrade - don't overwrite existing savedsearches.conf file
        if not os.path.exists(savedSearchesFile):
            shutil.copyfile(defaultSavedSearchesFile,savedSearchesFile)
            logger.info("xmSetupLookup - Seeded " + savedSearchesFile)

        logger.info("xmSetupLookup - Success Initializing Lookups")
        print ("SUCCESS")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

