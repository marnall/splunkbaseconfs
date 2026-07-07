import logging, urllib2, sys, json, time, re
'''
Class WunderAPI
Author: Kyle Smith
Email: kylesmith@kyleasmith.info
Copyright 2012
This Class takes a json configuration and does simple operations to correctly identify the API calls to make to Wunderground.
$$TODO$$
Allow for more Dynamic calling, ie. getCity, setCity etc.

'''
def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        excpetions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            try_one_last_time = True
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                    try_one_last_time = False
                    break
                except ExceptionToCheck, e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print msg
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            if try_one_last_time:
                msg = "%s, Final Try with %d seconds..." % (str(e), mdelay)
                if logger:
                    logger.warning(msg)
                else:
                    print msg
                return f(*args, **kwargs)
            return
        return f_retry  # true decorator
    return deco_retry

class WunderAPI:
    BASE_URL = "http://api.wunderground.com/api/%(apikey)s/%(feature)s"
    BASE_GEOLOOKUP = "http://api.wunderground.com/api/%(apikey)s/geolookup"
    ACC = "/q/%(country)s/%(city)s.json"
    DATE_BASE = BASE_URL + "_%(date)s" + ACC
    VBASE = BASE_URL + ACC
    
    API_URLS = {  "conditions" : VBASE,
                  "alerts": VBASE,
                  "almanac": VBASE,
                  "astronomy":VBASE,
                  "currenthurricane": BASE_URL + "/view.json",
                  "forecast": VBASE,
                  "forecast10day":VBASE,
                  "geolookup_airport": BASE_GEOLOOKUP + "/q/%(airport)s.json",
                  "geolookup_latlng": BASE_GEOLOOKUP + "/q/%(lat)s,%(lng)s.json",
                  "geolookup_postal": BASE_GEOLOOKUP + "/q/%(postalcode)s.json",
                  "geolookup_pws": BASE_GEOLOOKUP + "/q/pws:%(pws)s.json",
                  "geolookup_auto": BASE_GEOLOOKUP + "/q/autoip.json",
                  "geolookup": BASE_GEOLOOKUP + ACC,              
                  "history": DATE_BASE, #Date is YYYYMMDD
                  "hourly": VBASE,
                  "hourly10day":VBASE,
                  "planner":DATE_BASE, #Date is MMDDMMDD
                  "rawtide": VBASE,
                  "satellite":VBASE,
                  "tide": VBASE,
                  "webcams": VBASE,
                  "yesterday": VBASE,
                  "pws": "http://api.wunderground.com/api/%(apikey)s/conditions/pws:1/q/pws:%(pws)s.json"
                  }
    conf = {}
    
    
    def __init__(self, apikey):
        """Construct an instance of the WunderAPI."""
        logging.debug("Setting API KEY")
        self.conf["apikey"] = apikey
        
    def RunAPI(self, config):
        logging.debug("Running API")
        return self.__doAPICall(self.__makeURL(config).replace(" ","%20"))
        
    def __makeError(self,s):
        logging.debug("Making an Error")
        raise Exception, "%s" % s
        
    def __makeURL(self, config):
        """ Make the URL """
        logging.debug("Making an URL")
        config["apikey"] = self.conf["apikey"]
        #TODO: Allow for a config index of "state" and map to "country"
        try:
            return self.API_URLS[config["feature"]] % (config)
        except KeyError:
            self.__makeError("Failed to find Index in API_URLS config:%s"%config)
     
    @retry(urllib2.URLError, tries=15, delay=2, backoff=2, logger=logging)
    def __urlopen_with_retry(self, url):
        return urllib2.urlopen(url)
       
    def __doAPICall(self, url):
        logging.debug("Making an API CALL")
        if url == None:
            self.__makeError("Unable to get valid URL")
        logging.info("class=WunderClass.py url=\"%s\""%(url))
        json_string = '{"not_assigned":"not_assigned"}'
        try: 
            f = self.__urlopen_with_retry(url)
            json_string = f.read()
            f.close()
        except Exception, e:
            json_string = "{\"permanent_url_error\":\"%s\"}"%(str(e));
        return json_string
