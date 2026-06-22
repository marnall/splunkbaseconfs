import sys
import import_declare_test

from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators
from llm_search_command import stream

@Configuration()
class LlmCommand(StreamingCommand):
    """

    ##Syntax
    llm prompt="<text or template>" [connection=<name>] [model=<name>]

    ##Description
    Send a prompt template to a configured LLM connection.

    """

    prompt = Option(name='prompt', require=True)
    connection = Option(name='connection', require=False)
    model = Option(name='model', require=False)

    def stream(self, events):
        return stream(self, events)

dispatch(LlmCommand, sys.argv, sys.stdin, sys.stdout, __name__)