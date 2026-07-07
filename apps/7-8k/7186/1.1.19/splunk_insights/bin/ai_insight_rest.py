import os
import json
import tempfile
import requests
import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication


OPENAI_API_KEY = '';

#os.environ.get("OPENAI_API_KEY")  # Store in env or use Splunk secrets

class AiInsightHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super().__init__()

    def convert_to_dict(self, query):
        """
        Create a dictionary containing the parameters.
        """
        parameters = {}

        for key, val in query:

            # If the key is already in the list, but the existing entry isn't a list then make the
            # existing entry a list and add thi one
            if key in parameters and not isinstance(parameters[key], list):
                parameters[key] = [parameters[key], val]

            # If the entry is already included as a list, then just add the entry
            elif key in parameters:
                parameters[key].append(val)

            # Otherwise, just add the entry
            else:
                parameters[key] = val

        return parameters

    def parse_in_string(self, in_string):
        """
        Parse the in_string
        """

        
        params = json.loads(in_string)

        params['method'] = params['method'].lower()

        params['form_parameters'] = self.convert_to_dict(params.get('form', []))
        params['query_parameters'] = self.convert_to_dict(params.get('query', []))


        return params
    
    def handle(self, args):
        try:
            
            """if args['method'] != 'POST':
                return self._error("Only POST supported", 405)
            """
            body = self.parse_in_string(args.decode('utf-8'))["form_parameters"]
            
            with open("/tmp/my_ai_log.txt", "a") as f:
                f.write(json.dumps(body))
            
            #body = json.loads(args['payload'].decode("utf-8"))
            # Extract parameters
            spl_query = body.get("spl")
            description = body.get("description")
            related_infos = body.get("relatedInfos")
            severities_text = body.get("severitiesText")

            csv_content = body.get("csv")  # CSV passed as a string
            if not all([spl_query, description, csv_content]):
                return self._error("Missing required fields", 400)
            
            # Step 2: Prepare and send prompt
            prompt = f"""
You are a senior business data analyst and Splunk admin with deep expertise in interpreting operational and strategic data.

You will receive the following inputs:
- A Splunk SPL query
- A description of the query's intent
- Business context or related information, including links if available
- A table of historical search results (CSV or tabular format)

Your objectives are to:
- Interpret the data **from a business value and operational impact perspective**
- Identify key **patterns, anomalies, risks, trends, or performance shifts**
- Derive **strategic insights** and **actionable recommendations**
- Raise **high-impact questions** to guide business or technical stakeholders
- Present your findings in a **polished HTML business report** with the following clearly structured sections:

**Formatting Requirements:**
- Organize findings in sections.
- It should be as much detailed as possible and business oriented.
- Output a clean, semantic HTML5 document.
- Use **inline CSS** only (no external styles).
- use basic black color for text
- Visually differentiate alerts (e.g. critical findings) using **red-tinted boxes**.
- Use **green-tinted boxes** to highlight successful trends or positive performance.
- Use **orange-tinted boxes** to highlight warnings.
- Ensure visual clarity, professional formatting, and business-appropriate language.
- Output **only HTML**, no markdown or commentary.
- At the end add those sections to the other sections that you will generate :
    - **Behavioral Trends** help to understand user or system behavior over time.
    - **Automated Decision-Making** include real-time possible decisions driven by historical learning.
    - **Personalized Recommendations** deliver tailored suggestions based on past patterns.
    - **Anomaly Detection** identify unusual activity or system failures .
    - **Root Cause Analysis** trace back issues to their origin with precision.
    - **Predictive Analytics** forecast future events, behaviors, or system states.
    - **Summary** section that summarize findings 
    - and Finally a **Related Resources** section that Includes helpful links to Splunk documentation, dashboards, or general business intelligence resources.

**Good to know:**
if the data contains a severity level field (an integer between 0 and 5), below is the meaning of that field :
- 0 => info severity (id: severity_info_text)
- 1 => normal severity (id: severity_normal_text)
- 2 => low severity (id: severity_low_text)
- 3 => medium severity (id: severity_medium_text)
- 4 => high severity (id: severity_high_text)
- 5 => critical severity (id: severity_critical_text)

For each severity level, you may find in the inputs its description and explanation in a JSON formatted string with the severity id as a key and its description as the value... please use it to understand the context and the next steps and generate global insights and findings


INPUTS:
SPL Query:
{spl_query}

Search Description:
{description}

Related Information:
{related_infos}

Severities Description:
{severities_text}

Historical Results:
{csv_content}
"""


            chat_payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
            }

            chat_res = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                data=json.dumps(chat_payload)
            )

            if chat_res.status_code != 200:
                return self._error(f"Chat failed: {chat_res.text}", 500)

            chat_json = chat_res.json()
            html_output = chat_json["choices"][0]["message"]["content"]
    
            return {
                "status": 200,
                "payload": json.dumps({"html": html_output}),
                "headers": {'Content-Type': 'application/json'}
            }
        
            

        except Exception as e:
            with open("/tmp/my_ai_log.txt", "a") as f:
                f.write(str(e))
            return self._error(f"Unexpected error: {str(e)}", 500)

    def _error(self, message, code):
        return {
            "status": code,
            "payload": json.dumps({"error": message}),
            "headers": {'Content-Type': 'application/json'}
        }

    def extract_html(content):
        if content.startswith("```html") and content.endswith("```"):
            return content[7:-3].strip()  # remove ```html\n and ending ```
        return content.strip()


"""
it should include those sections , but also other sections that you may generate according to your findings and business context:
1. **Search Context** — Summarize what the search does, its business relevance, and how it supports strategic or operational goals.
2. **Key Insights** — Highlight the most significant observations from the data. Prioritize trends, shifts, unusual drops/spikes, or consistent patterns.
3. **Suggested Actions** — Provide business-relevant recommendations and operational steps based on your analysis.
4. **Questions for Leadership or Operations** — Pose strategic or tactical questions the business should explore.
5. **Related Resources** — Include helpful links to Splunk documentation, dashboards, or general business intelligence resources.
"""