import csv
import sys
import os
import pathlib
import itertools
from os import walk
from sigma.parser.collection import SigmaCollectionParser
from sigma.config.collection import SigmaConfigurationManager
from sigma.backends.splunk import SplunkBackend
from sigma.configuration import SigmaConfigurationChain
from sigma.parser.exceptions import SigmaCollectionParseError, SigmaParseError
from sigma.backends.exceptions import BackendError, NotSupportedError, PartialMatchError, FullMatchError

def sigma_convertor(file_name):

    
    def get_inputs(path):
        if os.path.isfile(path):
            return [path]
        else:
            return next(walk(path), (None, None, []))[2]

    
    sigmaconfigs = SigmaConfigurationChain()
    rows = []
    sigmaconfig = SigmaConfigurationManager().get('splunk-windows')
    #order = sigmaconfig.order
    sigmaconfigs.append(sigmaconfig)

    backend = SplunkBackend(sigmaconfigs, {'rulecomment': False})
    print("File name"+","+"Splunk Query")
    sigmafiles = get_inputs(file_name)
    for sigmafile in sigmafiles:
        try:
            '''print("* Processing Sigma input %s" % (len(sigmafiles)))'''
            if len(sigmafiles) == 1:
              f = open(sigmafile, "r")
            else:
              f = open(file_name+sigmafile, "r")
            parser = SigmaCollectionParser(f, sigmaconfigs, None)
            results = parser.generate(backend)
            for result in results:
              print(str(sigmafile)+","+str(result))
            
        except OSError as e:
            print("Failed to open Sigma file %s: %s" % (sigmafile, str(e)))
        except (SigmaParseError, SigmaCollectionParseError) as e:
            print("Sigma parse error in %s: %s" % (sigmafile, str(e)))
        except NotSupportedError as e:
            print("The Sigma rule requires a feature that is not supported by the target system: " + str(e))
        except BackendError as e:
            print("Backend error in %s: %s" % (sigmafile, str(e)))
        except (NotImplementedError, TypeError) as e:
            print("An unsupported feature is required for this Sigma rule (%s): " % (sigmafile) + str(e))
        except PartialMatchError as e:
            print("Partial field match error: %s" % str(e))
        except FullMatchError as e:
            print("Full field match error")
        except:
            print("error")
        finally:
            try:
                f.close()
            except:
                pass


argument = sys.argv[1]
sigma_convertor(argument)