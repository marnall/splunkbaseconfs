# Copyright 2018 Sideview, LLC. all rights reserved
import csv,traceback,json

"""
A simple utility that uses our field_gallery.csv file to generate the json 
field list that ships at the bottom of application.js
"""
def to_json(o, level=0):
    ret = ""
    if isinstance(o, dict):
        ret += "{"
        comma = ""

        #lambda function is to do a case-insensitive sort. 
        for k,v in sorted(o.iteritems(),key=lambda x: x[0].lower()):
            ret += comma
            if (level==0) :
                comma = ",\n    "
            else :
                comma = ", "
            ret += '"' + str(k) + '": '
            ret += to_json(v, level + 1)

        ret += "}"
    elif isinstance(o, basestring):
        ret += '"' + o + '"'
    elif isinstance(o, int):
        ret += str(o)
    else:
        raise TypeError("Unknown type '%s' for json serialization" % str(type(o)))
    return ret


def execute():
    try:
        field_json = {}
        path = "../lookups/";
        with open(path + "field_gallery.csv", 'rb') as field_gallery:
            csvReader = csv.reader(field_gallery, delimiter=',')
            for row in csvReader:
                attrs = {"categorical":0,"numeric":0,"time":0};
                attrs[row[1]] = 1
                field_json[row[0]] = attrs
        
        field_json_str = to_json(field_json)
        print field_json_str
        
    except Exception as e:
        print e
        print traceback.print_exc(e)
        return e

if __name__ == '__main__':
    execute()

