import csv, sys, argparse
from math import cos, asin, sqrt

# External txt files are sourced from: http://download.geonames.org/export/dump/
# cities1000_mod.txt is created by downloading the original (cities1000.txt) and
# running: cat cities1000.txt | cut -f3,5,6,9,11,18 > cities1000_mod.txt
# The "alternate names" field in the original file causes issues because it's too big.
CITIES = '../static/cities1000_mod.txt'
REGIONS = '../static/admin1CodesASCII.txt'
COUNTRIES = '../static/countryinfo_mod.txt'

# Implement a haversine to determine the great circle distance between two points on a sphere.
# Source: https://stackoverflow.com/questions/41336756/find-the-closest-latitude-and-longitude
def distance(lat1, lon1, lat2, lon2):
     p = 0.017453292519943295
     a = 0.5 - cos((lat2-lat1)*p)/2 + cos(lat1*p)*cos(lat2*p) * (1-cos((lon2-lon1)*p)) / 2
     return 12742 * asin(sqrt(a))

# Implement a shortcut to finding the minimum distance between the given lat/lon and the cities in our list.
# Source: https://stackoverflow.com/questions/41336756/find-the-closest-latitude-and-longitude
def closest(data, v):
    return min(data, key=lambda p: distance(v['lat'],v['lon'],p['latitude'],p['longitude']))

# This is utilized to take a Region, City, and Country and return a matching entry for lat/long
# City can be a partial match (utilizing starts with) but region and country need to be exact
def find_city(data, city, region, country):
    country = country.upper()
    region = region.upper()
    city = city.upper()

    partial_match = None

    for d in data:
        if str(d['country']).upper() == country and str(d['admin1']).upper() == region:
            if str(d['name']).upper() == city:
                return d

            if str(d['name']).upper().startswith(city):
                partial_match = d

    return partial_match 

# This could be prone to error... but it should allow you to find a city/country combination without region (state) information
def find_city_no_region(data, city, country):
    country = country.upper()
    city = city.upper()

    partial_match = None

    for d in data:
        if str(d['country']).upper() == country:
            if str(d['name']).upper() == city:
                return d

            if str(d['name']).upper().startswith(city):
                partial_match = d

    return partial_match 

# This creates dictionaries in memory from the external files to speed up the lookup process over larger datasets
def create_dictionary(type='city'):
    if type == 'city':
        data = []
        csv.field_size_limit(sys.maxsize)
        with open(CITIES, 'r') as f:
            reader = csv.reader(f,delimiter = '\t')

            for x in reader:
                data.append( 
                   { 
                   'name': x[0], 
                   'latitude': float(x[1]), 
                   'longitude': float(x[2]), 
                   'country': x[3], 
                   'admin1': x[4], 
                   'timezone': x[5]
                   })


    elif type == 'region':
        data = {}
        with open(REGIONS, 'r') as f:
            reader = csv.reader(f, delimiter = '\t')
            for x in reader:
                data[x[0]] = x[2]

    elif type == 'country':
        data = {}
        with open(COUNTRIES, 'r') as f:
            reader = csv.reader(f, delimiter = '\t')
            for x in reader:
                # Should result in entries like this
                # { "UNITED STATES": "US" }
                data[str(x[1]).upper()] = str(x[0]).upper()

    else:
        data = None
        pass

    return data

# Main function
def main():
    # Use argparse; add the required fields
    parser = argparse.ArgumentParser(description='Perform a conversion from lat/lon to closest city.')
    parser.add_argument('lat', default='lat')
    parser.add_argument('lon', default='lon')
    parser.add_argument('city', default='city')
    parser.add_argument('region', default='region')
    parser.add_argument('timezone', default='timezone')
    parser.add_argument('country', default='country')
    parser.add_argument('geo_matched', default='geo_matched')

    args = parser.parse_args()

    # Read the csv data splunk gives us
    r = csv.DictReader(sys.stdin)

    # Pull the headers for the output
    hdr = r.fieldnames

    # Send csv output back to splunk
    w = csv.DictWriter(sys.stdout, fieldnames=hdr)
    w.writeheader()

    # create the dictionaries
    city_dict = create_dictionary(type='city')

    # Actually, this one is a list but you get the idea
    region_dict = create_dictionary(type='region')

    # For normalizing country inputs to the ISO code
    country_dict = create_dictionary(type='country')

    # Loop through the results splunk sends us
    for result in r:
        # If the lat/long fields are populated, assume we need to find the nearest known city
        if result[args.lat] and result[args.lon]:
            try:
                closest_city = closest(city_dict, {'lat': float(result[args.lat]), 'lon': float(result[args.lon])})
                result[args.geo_matched] = closest_city
                result[args.city] = closest_city['name']
                result[args.timezone] = closest_city['timezone']
                result[args.country] = closest_city['country']
                try:
                    result[args.region] = region_dict[closest_city['country']+'.'+closest_city['admin1']]
                except:
                    # We try to expand the region code to a full name; if it's not found we default back to the short region.
                    result[args.region] = closest_city['admin1']

            except:
                # Very generic error handling just to make sure the script doesn't die fully.
                result[args.geo_matched] = 'Error'
                result[args.city] =  'Error'
                result[args.timezone] = 'Error'
                result[args.country] = 'Error'
                result[args.region] = 'Error'

        # On the other hand, if a city/region/country is provided - try to find a matching lat/long
        elif result[args.city] and result[args.country]:
            ## normalize the country provided...
            checked_country = ''
            if args.country in result:
                if str(result[args.country]).upper() in country_dict:
                    checked_country = country_dict[str(result[args.country]).upper()]
                else:
                    checked_country = result[args.country]
            else:
                checked_country = 'not provided'
            region = ''
            if args.region in result:
                try:
                    # Step 1 is to normalize the region. Texas should be TX; Colorado should be CO.
                    # If a match is not found, we default to whatever was provided by the user.
                    matched_key = None
                                        
                    for key,value in region_dict.items():
                        if str(key).upper().startswith(checked_country) and str(value).title() == result[args.region].title():
                            matched_key = key
                            break
                    
                    # Again, this requires a proper country code to be provided.
                    if matched_key is not None:
                        region = matched_key[len(checked_country)+1::]
                    else:
                        region = result[args.region]
                except:
                    region = result[args.region]


            if region == '' or region == 'none' or region is None:
                region = 'not_here'
            
            try:
                # Step 2 is to find the matching city based on an exact or partial match.
                # Results are added to the row and sent back to splunk.
                if region == 'not_here':
                    match = find_city_no_region(city_dict, result[args.city], checked_country)
                else:
                    match = find_city(city_dict, result[args.city], region, checked_country)

                if match is not None:
                    result[args.geo_matched] = match
                    result[args.lat] = match['latitude']
                    result[args.lon] = match['longitude']
                    result[args.timezone] = match['timezone']

                else:
                    result[args.geo_matched] = 'Not Found'
                    result[args.lat] = 'Not Found'
                    result[args.lon] = 'Not Found'
                    result[args.timezone] = 'Not Found'
            except:
                # Very generic error handling just to make sure the script doesn't die fully.
                result[args.geo_matched] = 'Error'
                result[args.lat] = 'Error'
                result[args.lon] = 'Error'
                result[args.timezone] = 'Error'

        else:
            pass

        w.writerow(result)


main()
