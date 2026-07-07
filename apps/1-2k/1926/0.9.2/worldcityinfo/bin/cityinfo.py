import os
import csv
from operator import itemgetter
from itertools import groupby
from splunk import Intersplunk

if __name__ == '__main__':
    keywords, options = Intersplunk.getKeywordsAndOptions()

    try:
        if len(keywords) == 0:
            results = Intersplunk.generateErrorResults('City field must be specified')
            Intersplunk.outputResults(results)
            exit(1)

        city = keywords[0]
        country = options.get('country', None)
        region = options.get('region', None)

        results = Intersplunk.readResults()
        with open('world.csv', 'rb') as f:
            reader = csv.reader(f)
            cityinfo = dict([k.decode('utf8'), list(g)] for k, g in groupby(reader, itemgetter(1)))

        popgetter = itemgetter(4)
        for row in results:
            cityname = row.get(city, None)
            if cityname is None:
                continue
            info = cityinfo.get(cityname.lower(), None)
            if info:
                if country:
                    geo = filter(lambda x: x[0] == row[country].lower(), info)
                    if region:
                        geo = filter(lambda x: x[3] == row[region].upper(), geo)
                    geo = geo[0]
                else:
                    geo = max(info, key=lambda x: int(popgetter(x)))
                row['lon'] = float(geo[-1])
                row['lat'] = float(geo[-2])
    except:
        import traceback
        stack = traceback.format_exc()
        results = Intersplunk.generateErrorResults('Traceback: ' + str(stack))

    Intersplunk.outputResults(results)
