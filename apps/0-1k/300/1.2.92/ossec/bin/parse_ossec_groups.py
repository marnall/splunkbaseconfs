#!/opt/splunk/bin/python
############################################################
############################################################
#
# Scan the OSSEC rules XML files for rule<->group mappings
# and build the appropriate config files for Splunk.
#
############################################################
############################################################
#
# This may output two files:
#
#   1)  ossec_rule_groups.csv
#       ---------------------
#       Contains a list of all rule IDs and the OSSEC rule
#       groups to which they belong.
#
#  2)   eventtypes-ossec.conf
#       ---------------------
#       Creates a list of eventtypes based on rule IDs. This
#       can be merged into your normal eventtyes.conf. Note
#       that the preferred approach is to NOT use this file,
#       but instead create your own eventtypes. To do this,
#       use the fields added from the lookup table. This way,
#       only the CSV file must be updated:
#          search = eventtype=ossec ossec_group=attack
#
############################################################
import os
import re
import sys
import getopt


# Path to the OSSEC rules directory, e.g., /var/ossec/rules/
DEFAULT_RULES_DIR = "/var/ossec/rules/"


# Each of these should be a filename, or set to None to
# suppress generation of that file
OUTPUT_LOOKUP_TABLE = "ossec_rule_groups.csv"
OUTPUT_EVENTTYPES   = None




############################################################
# Changes should not be needed beyond this point.
############################################################

try:
    opts,args = getopt.getopt(sys.argv[1:], 'r:', ['rules'])
except getopt.GetoptError, err:
    print str(err)
    sys.exit(2)

rules_dir = DEFAULT_RULES_DIR
output_file = OUTPUT_LOOKUP_TABLE
for o,a in opts:
    if o in [ '-r', '--rules' ]:
        rules_dir = a


re_global_group = re.compile(  '<group name="(.*?)"'  )
re_local_group = re.compile(  '<group>(.*?)</group>'  )
re_rule  = re.compile(  '<rule.*id="(\d+)"'     )


# Two dictionaries for mapping back and forth
rule_to_groups = {}
group_to_rules = {}


# Loop through all rule files, populating the mappings from
# rule to group and vice versa
for filename in os.listdir(rules_dir):
	if filename[-4:].lower() != '.xml':
		continue

        f = open(os.path.join(rules_dir, filename))

	rule_id = None
	localGroups = []
	globalGroups = []
	
        for line in f:
                l = line.lower().strip()

		if l[:8] == '</group>':
			# End of a global group section
			globalGroups = ()

		elif l[:7] == '</rule>':
			# End of a rule section - fill the dictionaries
			rule_to_groups[rule_id] = globalGroups + localGroups

			for xgroup in (globalGroups + localGroups):
				group = xgroup.strip()
				if group in group_to_rules.keys():
					# Add to existing entry
					group_to_rules[group].append(rule_id)
				else:
					# Create new entry
					group_to_rules[group] = [rule_id]

			rule_id = None
			localGroups = []

		else:

			# Is this a rule id?
			m = re_rule.match(l)
			if m != None:
				rule_id = m.group(1)
				continue

			# Is this a global group setting?
			m = re_global_group.match(l)
			if m != None:
				globalGroups = m.group(1).strip(",").split(",")
				continue

			# Is this a local group setting?
			m = re_local_group.match(l)
			if m != None:
				localGroups = localGroups + m.group(1).strip(",").split(",")
				continue


# Now we have everything in memory. Output the lookup table.
if OUTPUT_LOOKUP_TABLE != None:
	sorted = rule_to_groups.keys()
	sorted.sort()
	f = open(OUTPUT_LOOKUP_TABLE, "w")
	print >>f, '"rule_number","ossec_group"'
	for rule_id in sorted:
		for group in rule_to_groups[rule_id]:
			print >>f, '"' + rule_id.strip() +'","' + group.strip() + '"'
		


# Output the eventtype list
if OUTPUT_EVENTTYPES != None:
	sorted = group_to_rules.keys()
	sorted.sort()
	f = open("eventtypes-ossec.conf", "w")
	print >>f, "############################################################"
	print >>f, "# OSSEC Eventtypes for Splunk"
	print >>f, "# Automatically generated -- modify at your own risk"
	print >>f, "############################################################"
	print >>f
	for group in sorted:
		eventtype = "[ossec_" + group.strip() + "]"
		search = " OR rule_number=".join(group_to_rules[group])
		search = "search=sourcetype=ossec (rule_number=" + search + ")"

		print >>f, eventtype
		print >>f, search
		print >>f

