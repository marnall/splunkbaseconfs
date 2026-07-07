import logging
import openai
import sys
import os
import splunk.Intersplunk
import traceback


def get_response(prompt):
    g_response = openai.Completion.create(engine="text-davinci-003", prompt=prompt, max_tokens=2048, n=1, stop=None)
    return g_response.choices[0].text.strip()


try:
    logging.basicConfig(filename='ChatGPT_for_Splunk.log', level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s')

    openai.api_key = "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"
    os.environ["OPENAI_API_KEY_PATH"] = "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"

    results = splunk.Intersplunk.getOrganizedResults()
    args = sys.argv[1:]
    logging.info(f'Argumentos: {args}')
    ask = args[0].strip()
    response = get_response(ask)

    event = {'result': response}
    event_list = [event]
    logging.info(event_list)
    splunk.Intersplunk.outputResults(event_list)

except:
    stack = traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))
    logging.error(results)
