import os, sys
import json
import openai
from splunklib.client import Service, connect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators

@Configuration()
class ChatGptCommand(EventingCommand):
    """
    The chatgptcommand uses GPT-4 model's API to process data from the Splunk search results and answer a question.
    """

    field = Option(require=True)
    question = Option(require=True)

    def transform(self, records):
        data_list = [record[self.field] for record in records]

        # Prepare the data and question for the GPT-4 model's API
        data = "\n".join(data_list)
        
        # Get Api info from passwords conf
        session_key = self.service.token
        service = Service(token=session_key)
        for storage_password in service.storage_passwords:
            if storage_password.username == 'ChatGPTKEY' :
                api_key = storage_password.clear_password

        # Setup OpenAI API key
        openai.api_key = api_key

        # Create the prompt
        prompt = f"Data:\n{data}\nQuestion: {self.question}"

        # Make API call
        response = openai.Completion.create(engine="davinci", prompt=prompt, max_tokens=100)
        
        if response.choices:
            # The answer from the GPT-4 model's API
            answer = response.choices[0].text.strip()
            yield {"chatgpt_answer": answer}
        else:
            yield {"chatgpt_answer": "Error: GPT API response does not contain 'choices' field."}

dispatch(ChatGptCommand, sys.argv, sys.stdin, sys.stdout, __name__)
