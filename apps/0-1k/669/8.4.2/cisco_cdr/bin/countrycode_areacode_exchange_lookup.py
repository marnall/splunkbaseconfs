# Copyright (C) 2013-2025 Sideview LLC.  All Rights Reserved.
"""
implemented as a scripted lookup (aka external lookup) in splunk.
This uses a python port of google's libphonenumbers library to parse the party numbers
and extract various new fields, notably country code, area code and exchange.
"""
import csv
import sys
import phonenumbers


###############################
# NOTES ON MAKING MODIFICATIONS TO OFFNET_PREFIXES
# If the number parses without any prefix changes, great.
# Otherwise we try each prefix separately, stripping the given prefix from the start.
# as soon as we get a number that libphonenumbers says is valid, we stop.
OFFNET_PREFIXES = ["9", "0", "8", "99"]

def get_number_types():
    """ only used to populate a constant mapping the type integers to the actual labels like
    "fixed_line",  "mobile" or the always popular "fixed_line_or_mobile" """
    raw_vars = vars(phonenumbers.phonenumberutil.PhoneNumberType)
    out = {}
    for key in raw_vars:
        # Weird the library doesn't give you a way to get these. Here we grab the raw vars but then
        # throw away any that aren't entirely uppercase.  ie "FIXED_LINE_OR_MOBILE"
        if key.upper() == key:
            # but after filtering we lowercase them all.
            out[raw_vars[key]] = key.lower()
    return out

NUMBER_TYPES = get_number_types()

def populate_fields(result, valid_number, field):
    """
    Given a valid number, files away the actual output fields into the given result dict.
    Things we could be getting from the number object and we aren't.
    1)Domestic carrier code.  something that might be in there sometimes?
        number.preferred_domestic_carrier_code
    2) country mobile token.
        phonenumbers.country_mobile_token(number.country_code)
    3) information about the region's "short numbers" like "text 3543 to
        123-555-1212 and you'll donate $50 to Bob"
        see "shortnumberinfo.py" etc.
    """

    result[field + "CountryCode"] = str(valid_number.country_code)

    area_code_length = phonenumbers.length_of_geographical_area_code(valid_number)
    nat = str(valid_number.national_number)
    if area_code_length > 0:
        result[field + "AreaCode"] = nat[:area_code_length]
        if valid_number.country_code == 1:
            result[field + "Exchange"] = nat[area_code_length:area_code_length+3]

    elif area_code_length == 0:
        # I dont care what you smell get back in there.
        if valid_number.country_code == 1 and len(nat) == 10:
            result[field + "AreaCode"] = nat[:3]
            result[field + "Exchange"] = nat[3:6]

    result[field + "NumberType"] = get_number_type(valid_number)

def get_number_type(number):
    """ convenience method to get the number type label in one shot """
    number_type = phonenumbers.phonenumberutil.number_type(number)
    return NUMBER_TYPES.get(number_type, None)

def is_valid_number(number):
    """ we always check both of these, so this got pulled up. """
    return phonenumbers.is_possible_number(number) and phonenumbers.is_valid_number(number)


def get_country(result):
    country = result.get("clusterLocale", "")
    if not country or country == "UNSET":
        country = "US"
    return country

def worth_trying(result, field):
    #General optimization
    party_number = result.get(field + "Number", "")
    country = get_country(result)

    if not party_number:
        return False
    #US optimization
    if country == "US" and len(party_number) < 10:
        return False
    if len(party_number) < 7 or party_number.startswith("b"):
        return False

    return True

def process_party_number_field(result, field):
    """ process either callingParty*  or finalCalledParty* on the given result """
    party_number = result.get(field + "Number", "")
    country = get_country(result)

    party_number = party_number.rstrip("#")

    number = phonenumbers.phonenumberutil.parse(party_number, country)

    prefix_index = 0
    while not is_valid_number(number) and prefix_index < len(OFFNET_PREFIXES):
        prefix = OFFNET_PREFIXES[prefix_index]
        if party_number.startswith(prefix):
            candidate = party_number[len(prefix):]
            number = phonenumbers.phonenumberutil.parse(candidate, country)
        prefix_index += 1
    if is_valid_number(number):
        populate_fields(result, number, field)


def main():
    """ outer function called and passed the incoming results on stdin.  returns modified result
        rows to stdout """
    reader = csv.reader(sys.stdin)
    writer = None
    first = True

    for line in reader:
        if first:
            header = line

            csv.writer(sys.stdout).writerow(header)
            writer = csv.DictWriter(sys.stdout, header)
            first = False
            continue

        # Read the result
        result = {}


        for i, value in enumerate(line):
            if value:
                result[header[i]] = value

        for field in ["callingParty", "finalCalledParty"]:
            if worth_trying(result, field):
                try:
                    process_party_number_field(result, field)
                except phonenumbers.phonenumberutil.NumberParseException:
                    pass
                except Exception as unexpected_exc:
                    result[field + "CountryCode"] = result[field + "AreaCode"] = str(unexpected_exc)
        writer.writerow(result)


# this allows us to import from unit tests file and exercise individual functions, without mucking
# with our stdin/stdout
if len(sys.argv) > 0 and sys.argv[0].endswith("unit_tests.py"):
    pass
else:
    main()
