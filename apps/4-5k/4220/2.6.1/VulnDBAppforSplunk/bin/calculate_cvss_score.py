import os
import sys
import re

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'VulnDBAppforSplunk', 'lib'))

from splunklib.searchcommands import dispatch, EventingCommand, Configuration


@Configuration()
class CvssScoreCommand(EventingCommand):
    """Custom command class to calculate the CVSS Score."""

    def transform(self, records):
        """Method to calculate the CVSS Score."""
        for record in records:
            try:
                combined_field = record["combined_field"]
            except Exception:
                yield record

            else:
                is_RBS = False
                score_string = ""

                if (isinstance(combined_field, list)):
                    combined_field.sort(reverse=True)
                    for item in combined_field:
                        if ("RBS" in item):
                            is_RBS = True
                            score_string = item
                            break
                    if not is_RBS:
                        score_string = combined_field[0]
                else:
                    score_string = combined_field
                if (score_string):
                    m = re.search(r'\|(\d{1,2}.\d)\|', score_string)
                    score = m.group(1)
                    record["score"] = score
                yield record


dispatch(CvssScoreCommand, sys.argv, sys.stdin, sys.stdout, __name__)
