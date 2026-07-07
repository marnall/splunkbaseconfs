import re

regex_norm_key = re.compile('\W')
regex_norm_lowcase_key = re.compile('([a-z0-9])([A-Z]+)')
regex_kv = re.compile('(\w+)=(.*?)(?=\s\w+=|$)')

def normalize_key(key):
	nkey = regex_norm_key.sub('_', key)
	return regex_norm_lowcase_key.sub(r'\1_\2', nkey).lower()

def get_labels(extension):
	kv = {}
	is_key = False
	k = v = ''
	for i in range(len(extension) - 1, -1, -1):
		ch = extension[i]
		if ch == '=' and i > 0 and extension[i - 1] != '\\':
			is_key = True
		elif ch == ' ' and is_key:
			kv[k] = v
			k = v = ''
			is_key = False
		else:
			if is_key:
				k = ch + k
			else:
				v = ch + v

	if is_key and k != '':
		kv[k] = v

	return extract_labels(kv)

def get_labels_regex(extension):
	kv = {}
	for p in regex_kv.findall(extension):
		kv[p[0]] = p[1];

	return extract_labels(kv)

def get_log_extension(row):
	cols = row.split('|', 7)

	if (len(cols) != 8):
		return ''

	return cols[7]

def is_label_key(str):
	return str[-5:] == 'Label'

def extract_labels(kv):
	result = {}

	for k in kv.keys():
		if not is_label_key(k):
			continue

		k2 = k[0:len(k) - 5]

		if k2 in kv:
			label = normalize_key(kv[k])
			value = kv[k2]
			result[label] = value

	return result

def splunk_main():
	import splunk.Intersplunk

	try:
		results, unused1, unused2 = splunk.Intersplunk.getOrganizedResults()

		for result in results:
			kv = get_labels_regex(get_log_extension(result['_raw']))
			result.update(kv)
	except:
		import traceback
		tb = traceback.format_exc()
		results = splunk.Intersplunk.generateErrorResults('Error: Traceback: ' + str(tb))

	splunk.Intersplunk.outputResults(results)

splunk_main()