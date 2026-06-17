# Copyright (C) 2010-2025 Sideview LLC.  All Rights Reserved.
import splunk.Intersplunk
import phonenumbers


# This is an alternate to the "parse_phone_numbers" scripted lookup that also
# ships in this app.
# HOWEVER cleaner though this in many ways looks and feels, the scripted lookup
# is about 30% faster.  So we are only shipping it in case it becomes useful
# in the field.  For one thing, it can possibly pushed out to the indexers more
# reliably than the scripted lookup but this is just a guess.


POSSIBLE_OFFNET_PREFIXES = ["99", "9"]
POSSIBLE_IDD_PREFIXES = ["011", "001", "0011", "00", "010"]
currentCountry = "US"



def writeFields(result, number, field):
    result[field + "CountryCode"] = str(number.country_code)
    areaCodeLength = phonenumbers.length_of_geographical_area_code(number)
    if areaCodeLength > 0:
        result[field + "AreaCode"] = str(number.national_number)[:areaCodeLength]
    if number.country_code == 1:
        nat = str(number.national_number)
        result[field + "Exchange"] = nat[len(nat)-7:len(nat)-4]

def is_valid_number(number):
    return phonenumbers.is_possible_number(number) and phonenumbers.is_valid_number(number)

def stripPrefixes(n):
    for prefix in POSSIBLE_OFFNET_PREFIXES:
        if n.startswith(prefix):
            n = n[len(prefix):]
            break

    for iddPrefix in POSSIBLE_IDD_PREFIXES:
        if n.startswith(iddPrefix):
            n = "+" + n[len(iddPrefix):]
            break
    return n



def main():
    inputFields = ["callingParty", "finalCalledParty"]
    #outputFieldSuffixes = ["CountryCode", "Exchange", "AreaCode"]

    # get the previous search results
    results, _unused1, _unused2 = splunk.Intersplunk.getOrganizedResults()

    for result in results:
        for field in inputFields:
            try:
                n = result.get(field + "Number", "").rstrip("#")

                if len(n) < 7 or len(n) > 16 or n.startswith("b"):
                    continue

                number = phonenumbers.phonenumberutil.parse(n, currentCountry)
                if is_valid_number(number):
                    writeFields(result, number, field)
                else:
                    stripped = stripPrefixes(n)
                    if stripped != n:
                        try:
                            number = phonenumbers.phonenumberutil.parse(stripped, currentCountry)
                            if is_valid_number(number):
                                writeFields(result, number, field)
                        except:
                            pass

            except phonenumbers.phonenumberutil.NumberParseException as e:
                pass
            except Exception as e:
                result[field + "CountryCode"] = result[field + "AreaCode"] = str(e)
    splunk.Intersplunk.outputResults(results)

main()
