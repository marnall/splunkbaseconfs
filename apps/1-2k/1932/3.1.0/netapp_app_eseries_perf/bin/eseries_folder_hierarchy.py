"""Class - Folder hierarchy command."""
import sys
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration
import string


@Configuration()
class eseriesfolderhierarchyCommand(StreamingCommand):
    """This is custom command class."""

    def stream(self, events):
        """Stream method."""
        alphabet = list(string.ascii_lowercase)

        for event in events:
            path_count = int(event['0'])
            i = 0
            my_event = {}
            event_length = len(event.keys())
            column_count = path_count + event_length - 1

            for x in range(0, column_count):
                column_name = 'column_' + alphabet[x]
                my_event[column_name] = ''

            paths = event['1'].split('/')
            for path in paths:
                column_name = 'column_' + alphabet[i]
                my_event[column_name] = '1||' + path
                i = i + 1

            for x in range(2, event_length):
                if event[str(x)]:
                    column_name = 'column_' + alphabet[i]
                    my_event[column_name] = str(x) + '||' + str(event[str(x)])
                    i = i + 1

            yield my_event


dispatch(eseriesfolderhierarchyCommand, sys.argv, sys.stdin, sys.stdout, __name__)
