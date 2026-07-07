
import os
import random


DISPLAY_NAME_KEY = "displayName"
class Namifier(object):
    """ simple object to hold the silly job of assigning secret names to people. """

    def __init__(self):
        self.name_mapping = {}
        self.names = []
        self.first_names = []
        self.last_names = []
        current_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(current_path, "random_names.txt"), 'r+') as name_file:
            for line in name_file:
                first_last=line.strip().split(" ")
                if first_last[0] not in self.first_names:
                    self.first_names.append(first_last[0])
                if first_last[1] not in self.last_names:
                    self.last_names.append(first_last[1])

            for last_name in self.last_names:
                for first_name in self.first_names:
                    self.names.append(first_name + " " + last_name)

            #print(self.names)
            #print(len(self.names))



        assert len(self.names)>499000, "we assume there are more than half a names in our list"

    def get_secret_name(self, raw_name):
        """ get the name we're mapping this raw_name to, and remember the mapping for later also. """
        #return "Agnes Leatherbottom"
        if raw_name not in self.name_mapping:
            random_index = random.randrange(len(self.names))
            # pop it off and assign it at the same time
            self.name_mapping[raw_name] =self.names.pop(random_index)
        return self.name_mapping[raw_name]

    def fix_single_display_name(self, item):
        if item and DISPLAY_NAME_KEY in item and item[DISPLAY_NAME_KEY]:
            raw_name = item[DISPLAY_NAME_KEY]
            secret_name = self.get_secret_name(raw_name)
            #print(raw_name + " changing to " + secret_name)
            if not isinstance(raw_name, str):
                return False
            item[DISPLAY_NAME_KEY] =secret_name
            return True

