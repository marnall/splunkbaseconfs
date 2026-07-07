#!/usr/bin/env python
import os, sys, time
from datetime import datetime
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

APPDIR = 'TA-croniter'

# make sure the directory storing the croniter library can be imported
LIBDIR = os.path.join(os.path.join(os.environ.get('SPLUNK_HOME')), 'etc', 'apps', APPDIR, 'bin', 'lib')
if not LIBDIR in sys.path:
    sys.path.append(LIBDIR)

# Import the library
try:
    from croniter import croniter
except ImportError:
    raise Exception('Unable to import required croniter library. Ensure path %s exists.' % LIBDIR)

@Configuration(local=True)
class CroniterCommand(StreamingCommand):
    """
    ##Syntax
     | croniter iterations=25 input=cron_schedule start_epoch=timestamp_field
     OR
     | croniter input=cron_schedule start_epoch=timestamp_field end_epoch=timestamp_field

    ##Description
      Implements the python croniter library to convert cron schedules to upcoming timestamps

    """

    try:
        iterations = Option(require=False, name='iterations', default=25)
    except:
        iterations = 25

    try:
        end_epoch = Option(require=False, name='end_epoch', default=None)
    except:
        end_epoch = None
    
    try:
        cron_field = Option(require=False, name='input', default='cron_schedule')
    except:
        cron_field = 'cron_schedule'

    try:
        start_epoch = Option(require=False, name='start_epoch', default=None)
    except:
        start_epoch = None


    def stream(self, events):

        # Setting this in case a start_epoch is not provided - it's not required to provide one
        current_time = time.time()

        # loop through all events
        for single_event in events:

            # only do stuff if the cron field exists
            if self.cron_field in single_event.keys():

                # Did start_epoch get set? If not or if any error occurs, default to the current_datetime set above
                if self.start_epoch is not None:
                    # If so, does the target field exist?
                    if self.start_epoch in single_event.keys():
                        # Try parsing it as an epoch for a start date
                        try:
                            start_date = int(float(single_event[self.start_epoch]))
                        except:
                            start_date = current_time
                    else:
                        start_date = current_time
                else:
                    start_date = current_time

                # Did an end_epoch get set?
                if self.end_epoch is not None:
                    if self.end_epoch in single_event.keys():
                        try:
                            end_time = int(float(single_event[self.end_epoch]))
                        except:
                            end_time = None
                    else:
                        end_time = None
                else:
                    end_time = None


                # create the iteration object
                iter_obj = croniter(str(single_event[self.cron_field]), start_date)

                single_event['croniter_return'] = []
                
                # The goal here is this:
                # If a user sets an end epoch, do not stop until we meet that
                # If a user sets an end epoch AND iterations value, stop when we meet the end epoch
                # If a user sets only iterations, stop after X iterations
                iter_counter = 1
                while True:
                    # Get the next calculated time
                    next_time = iter_obj.get_next()
                    try:
                        # Append it
                        single_event['croniter_return'].append(next_time)
                    except:
                        import traceback
                        single_event['croniter_return'].append('Error occurred while trying to generate future iterations. Stopping loop. Details: %s' % (traceback.format_exc()))
                        break

                    # Increment the internal counter
                    iter_counter += 1

                    # Check if end_time is set
                    if end_time is not None:
                        if next_time >= end_time:
                            break

                    # And if not, check the iterations counter
                    else:
                        if iter_counter > int(self.iterations):
                            break

                # yield
                yield single_event

            else:
                single_event['croniter_return'] = 'Field %s not found in event.' % str(cron_field)
                yield single_event

dispatch(CroniterCommand, sys.argv, sys.stdin, sys.stdout, __name__)