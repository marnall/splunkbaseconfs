import re
import logging
import sys
import csv
import urllib
#import splunk.Intersplunk

stop_words = ['a', 'able', 'about', 'across', 'after', 'all', 'almost', 'also', 'am', 'among', 'an', 'and', 'any', 'are', 'as', 'at', 'be', 'because', 'been', 'but', 'by', 'can', 'cannot', 'could', 'dear', 'did', 'do', 'does', 'either', 'else', 'ever', 'every', 'for', 'from', 'get', 'got', 'had', 'has', 'have', 'he', 'her', 'hers', 'him', 'his', 'how', 'however', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'just', 'least', 'let', 'like', 'likely', 'may', 'me', 'might', 'most', 'must', 'my', 'neither', 'no', 'nor', 'not', 'of', 'off', 'often', 'on', 'only', 'or', 'other', 'our', 'own', 'rather', 'said', 'say', 'says', 'she', 'should', 'since', 'so', 'some', 'than', 'that', 'the', 'their', 'them', 'then', 'there', 'these', 'they', 'this', 'tis', 'to', 'too', 'twas', 'us', 'wants', 'was', 'we', 'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'would', 'yet', 'you', 'your']

# splunk logging requirements
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)
#filehandler = logging.FileHandler("C:/Program Files/Splunk/var/log/splunk/wc.log", mode="a")
#filehandler.setFormatter(formatter)
#logging.root.addHandler(filehandler)


def count_words_from_string(s, use_stops=True):
    running_total = dict()
    for token in re.sub(r"\s+|\b", '\f', s).split('\f'):
        clean_token = re.sub(r"[^a-zA-Z1-9'-]", "", token).lower()
        if clean_token and ((clean_token not in stop_words) or not use_stops):
            if clean_token in running_total:
                running_total[clean_token] += 1
            else:
                running_total[clean_token] = 1
    return running_total


# Tees input as it is being read, also logging it to a file
class Reader:
    def __init__(self, buf, filename=None):
        self.buf = buf
        if filename is not None:
            self.log = open(filename, 'w')
        else:
            self.log = None

    def __iter__(self):
        return self

    def next(self):
        return self.readline()

    def readline(self):
        line = self.buf.readline()

        if not line:
            raise StopIteration

        # Log to a file if one is present
        if self.log is not None:
            self.log.write(line)
            self.log.flush()

        # Return to the caller
        return line


def encode_mv(vals):
    """For multivalues, values are wrapped in '$' and separated using ';'
    Literal '$' values are represented with '$$'"""
    s = ""
    for val in vals:
        val = val.replace('$', '$$')
        if len(s) > 0:
            s += ';'
        s += '$' + val + '$'

    return s

# stolen from https://github.com/splunk/splunk-sdk-python/blob/master/examples/twitted/twitted/bin/tophashtags.py
def read_input(buf, has_header = True):
    """Read the input from the given buffer (or stdin if no buffer)
    is supplied. An optional header may be present as well"""

    # Use stdin if there is no supplied buffer
    if buf is None:
        buf = sys.stdin

    # Attempt to read a header if necessary
    header = {}
    if has_header:
        # Until we get a blank line, read "attr:val" lines,
        # setting the values in 'header'
        last_attr = None
        while True:
            line = buf.readline()

            # remove lastcharacter (which is a newline)
            line = line[:-1]

            # When we encounter a newline, we are done with the header
            if len(line) == 0:
                break

            colon = line.find(':')

            # If we can't find a colon, then it might be that we are
            # on a new line, and it belongs to the previous attribute
            if colon < 0:
                if last_attr:
                    header[last_attr] = header[last_attr] + '\n' + urllib.unquote(line)
                else:
                    continue

            # extract it and set value in settings
            last_attr = attr = line[:colon]
            val = urllib.unquote(line[colon+1:])
            header[attr] = val

    return buf, header


def output_results(results, mvdelim = '\n', output = sys.stdout):
    """Given a list of dictionaries, each representing
    a single result, and an optional list of fields,
    output those results to stdout for consumption by the
    Splunk pipeline"""

    # We collect all the unique field names, as well as
    # convert all multivalue keys to the right form
    fields = set()
    for result in results:
        for key in result.keys():
            if(isinstance(result[key], list)):
                result['__mv_' + key] = encode_mv(result[key])
                result[key] = mvdelim.join(result[key])
        fields.update(result.keys())

    # convert the fields into a list and create a CSV writer
    # to output to stdout
    fields = sorted(list(fields))

    writer = csv.DictWriter(output, fields)

    # Write out the fields, and then the actual results
    writer.writerow(dict(zip(fields, fields)))
    writer.writerows(results)


def main(argv):
    stdin_wrapper = Reader(sys.stdin)
    csv.field_size_limit(sys.maxint)
    buf, settings = read_input(stdin_wrapper, has_header=True)
    events = csv.DictReader(buf)

    logging.debug("settings: %s" % str(settings))
    logging.debug("argv: %s" % argv)

    parse_field = "_raw"
    usestops = True

    for i in range(1, len(argv)):
        arg = argv[i]  
        if arg.lower().startswith('usestopwords'):
            bits = arg.split('=')
            if bits[1].strip().lower().startswith('f'):
                usestops = False
        else:
            parse_field = arg

    logging.debug("parse_field = %s" % parse_field)

    results = []
    for event in events:
        logging.debug("event: %s" % event)
        word_counts = count_words_from_string(event[parse_field], usestops)
        #event["__mv_counts"] = word_counts
        logging.debug("counts: %s" % word_counts)
        for word, cnt in word_counts.iteritems():
            row = dict()
            row["_time"] = event["_time"]
            row["word"] = word
            row["count"] = cnt
            results.append(row)

    output_results(results)
    #splunk.Intersplunk.outputResults(results, fields=["word", "count"])


if __name__ == "__main__":
    try:
        main(sys.argv)
    except Exception:
        import traceback
        traceback.print_exc(file=sys.stdout)
