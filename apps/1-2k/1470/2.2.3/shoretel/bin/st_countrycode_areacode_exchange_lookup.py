# Copyright (C) 2013-2018 Sideview LLC.  All Rights Reserved.

import csv,sys, traceback
from phonenumbers import phonenumberutil, is_possible_number, is_valid_number, length_of_geographical_area_code
from phonenumbers.geocoder import area_description_for_number, country_name_for_number
from sv_sh_lookups import UK_DIALLING_CODES, COUNTRY_CODES

inputFields= ["CallerID", "DialedNumber"]
outputFieldSuffixes = ["Type", "CountryCode", "AreaCode", "Exchange", "AreaDescription", "CountryName", "Lat", "Long"]
currentCountry = "US"




def main():
    r = csv.reader(sys.stdin)
    w = None
    header = []
    first = True

    errors = []

    for line in r:
        if first:
            first = False
            header = line

            for field in inputFields:
                for suffix in outputFieldSuffixes:
                    header.append(field + suffix)

            csv.writer(sys.stdout).writerow(header)
            w = csv.DictWriter(sys.stdout, header)

            #continue

        result = {}
        try:
            # Read the result

            i = 0
            headerLen = len(header)
            lineLen = len(line)
            while i < headerLen:
                if i < lineLen:
                    result[header[i]] = line[i]
                else:
                    result[header[i]] = ''
                i += 1



            for field in inputFields:
                try:
                    n = result[field]
                    if len(n) > 1  and n[0] == "9":
                        n = n[1:]
                    if len(n) > 6:
                        number = phonenumberutil.parse(n, currentCountry)
                        isValid = is_valid_number(number)
                        if (isValid == None):
                            isValid = "False"

                        result[field + "IsValid"] = str(isValid)

                        if is_possible_number(number) and isValid:

                            countryList = COUNTRY_CODES.get(number.country_code, False)

                            result[field + "CountryCode"] = str(number.country_code)

                            areaCodeLength = length_of_geographical_area_code(number)
                            result[field + "AreaCode"] = str(number.national_number)[:areaCodeLength]

                            result[field + "AreaDescription"] = str(area_description_for_number(number, "en"))

                            result[field + "CountryName"] = str(country_name_for_number(number, "en"))


                            if number.country_code == 1:
                                nat = str(number.national_number)
                                result[field + "Exchange"] = nat[len(nat) - 7:len(nat) - 4]


                            if number.country_code == 44 and areaCodeLength > 0:
                                UK_list = UK_DIALLING_CODES.get(int(str(number.national_number)[:areaCodeLength]), False)
                                result[field + "Lat"] = str(UK_list)
                                if UK_list:
                                    result[field + "Lat"] = UK_list[2]
                                    result[field + "Long"] = UK_list[3]

                            elif countryList:
                                result[field + "Lat"] = countryList[1]
                                result[field + "Long"] = countryList[2]

                            numberType = phonenumberutil.number_type(number)

                            if numberType == phonenumberutil.PhoneNumberType.FIXED_LINE:
                                result[field + "Type"] = "Fixed Line"

                            elif numberType == phonenumberutil.PhoneNumberType.MOBILE:
                                result[field + "Type"] = "Mobile"

                            elif numberType == phonenumberutil.PhoneNumberType.FIXED_LINE_OR_MOBILE:
                                result[field + "Type"] = "Fixed Line Or Mobile"



                except phonenumberutil.NumberParseException as e:
                    result["DynamicLookupError"] = field + " is invalid!"
                    result[field + "IsValid"] = "False"

                except Exception as e2:
                    result["DynamicLookupError"] = str( e2.__class__.__name__ ) + ": " + str(e2)+ "\n\n" + traceback.format_exc()


        except Exception as e:
            result["DynamicLookupError"] = str( e.__class__.__name__ ) + ":" + str(e)

        w.writerow(result)
main()
