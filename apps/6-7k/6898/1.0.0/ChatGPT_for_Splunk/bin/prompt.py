# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#                                                                                                                     //
#   Author: Juan Alejandro Perez Chandia                                                                              //
#   Date: May 01st, 2023                                                                                              //
#   Personal brand: JPEngineer                                                                                        //
#                                                                                                                     //
#   ChatGPT for Splunk                                                                                                //
#                                                                                                                     //
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

import logging
import openai
import sys
import splunk.Intersplunk
import traceback
import configparser

config = configparser.ConfigParser()
config.read('../default/api_key.conf')


def get_response(prompt):
    g_response = openai.Completion.create(engine="text-davinci-003", prompt=prompt, max_tokens=2048, n=1, stop=None)
    return g_response.choices[0].text.strip()


try:
    logging.basicConfig(filename='ChatGPT_for_Splunk.log', level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s')

    openai.api_key = config.get('OPENAI_API_KEY', 'KEY')

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
