import sys
import time
import json
from os import environ
from os.path import join as join_path
from pathlib import Path
import pendulum
import logging
from helpers.logger import setup_logger
from splunklib.searchcommands import (
    dispatch, 
    GeneratingCommand, 
    Configuration, 
    Option
)


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_get_control_info_command'
)


@Configuration()
class GenerateCommand(GeneratingCommand):
    domain = Option(
        require=False, 
        name='domain'
    )

    control = Option(
        require=False,
        name='control'
    )

    app_name = Path(__file__).absolute().parts[-3]

    app_dir = join_path(
        environ['SPLUNK_HOME'],
        'etc',
        'apps',
        app_name
    )

    domains_file_path = join_path(
        app_dir,
        'appserver',
        'static',
        'utils',
        'json',
        'domains.json'
    )

    def generate(self):
        self.log_start_message()
        _time = time.time()
        sourcetype = 'cmmc:control_info'

        status = None
        message = None


        with open(self.domains_file_path, 'r') as domains_file:
            try:
                control_object = json.load(domains_file)

            except Exception as e:
                logger.error(f'status="ERROR", message="Error loading domains.json: {str(e)}"')

                yield {
                    '_time': _time,
                    'status': 'ERROR',
                    'message': f'Error loading domains.json: {str(e)}',
                    'control_info': None,
                    'sourcetype': sourcetype,
                    '_raw': {
                        'time': _time,
                        'status': 'ERROR',
                        'message': f'Error loading domains.json: {str(e)}',
                        'control_info': None
                    }
                }

            else:
                logger.info(f'status="success", message="Successfully loaded domains.json."')


        if self.control:
            logger.info(f'message="Retrieving control info for control {self.control}."')

            control_domain = self.control[:2]

            try:
                control_object = {
                    self.control.upper(): control_object['domains'][control_domain.upper()][self.control.upper()]
                }

            except KeyError:
                status = 'Failure'
                message = f'No matching control name found for {self.control}'
                control_object = None
                logger.error(f'status="ERROR", message="No matching control name found for {self.control}"')


            else:
                status = 'Success'
                message = f'Successful request for control {self.control}.'
                logger.info(f'status="success", message="Successfully retrieved control info for control {self.control}."')


        elif self.domain:
            logger.info(f'message="Retrieving control info for domain {self.domain}."')

            try:
                control_object = {
                    self.domain.upper(): control_object['domains'][self.domain.upper()]
                }

                try:
                    del control_object[self.domain.upper()]['domain']
                    del control_object[self.domain.upper()]['cmmc_levels']

                except:
                    pass

            except KeyError:
                status = 'Failure'
                message = f'No matching domain found for {self.domain}'
                control_object = None
                logger.error(f'status="ERROR", message="No matching domain found for {self.domain}."')

            else:
                status = 'Success'
                message = f'Successful request for domain {self.domain}.'
                logger.info(f'status="success", message="Successfully retrieved control info for domain {self.domain}."')


        else:
            status = 'Success'
            message = 'Successful request for all domains.'
            logger.info(f'status="success", message="Successful request for all domains."')


        self.log_stop_message()


        if not control_object:
            yield {
                '_raw': {
                    'status': status,
                    'message': message
                }
            }


        elif self.control:
            for practice, practice_data in control_object.items():
                practice_name = practice

            practice_data['control_name'] = practice_name

            yield {
                'control_name': practice,
                'practice_description': practice_data['practice_description'],
                'cmmc_clarification': practice_data['cmmc_clarification'],
                'mappings': practice_data['mappings'],
                'assessment_objectives': practice_data['assessment_objectives'],
                'potential_assessment_methods': practice_data['potential_assessment_methods'],
                'further_discussion': practice_data['further_discussion'],
                'potential_assessment_considerations': practice_data['potential_assessment_considerations'],
                'process_automation': practice_data['process_automation'],
                'possible_technology_considerations': practice_data['possible_technology_considerations'],
                'cmmc_source_discussion': practice_data['cmmc_source_discussion'],
                'suggested_technologies': practice_data['suggested_technologies'],
                'suggested_implementation': practice_data['suggested_implementation'],
                'sourcetype': sourcetype,
                '_time': _time,
                '_raw': {
                    '_time': _time,
                    'control': practice_data,
                    'sourcetype': sourcetype,
                    'control_name': practice_name
                }
            }


        elif self.domain:
            for practice_name, practice_data in control_object[self.domain.upper()].items():

                practice_data['control_name'] = practice_name

                yield {
                    'control_name': practice_name,
                    'practice_description': practice_data['practice_description'],
                    'cmmc_clarification': practice_data['cmmc_clarification'],
                    'mappings': practice_data['mappings'],
                    'assessment_objectives': practice_data['assessment_objectives'],
                    'potential_assessment_methods': practice_data['potential_assessment_methods'],
                    'further_discussion': practice_data['further_discussion'],
                    'potential_assessment_considerations': practice_data['potential_assessment_considerations'],
                    'process_automation': practice_data['process_automation'],
                    'possible_technology_considerations': practice_data['possible_technology_considerations'],
                    'cmmc_source_discussion': practice_data['cmmc_source_discussion'],
                    'suggested_technologies': practice_data['suggested_technologies'],
                    'suggested_implementation': practice_data['suggested_implementation'],
                    'sourcetype': sourcetype,
                    '_time': _time,
                    '_raw': {
                        '_time': _time,
                        'control': practice_data,
                        'sourcetype': sourcetype,
                        'control_name': practice_name
                    }
                }


        else:
            for domain, practices_data in control_object['domains'].items():
                try:
                    del practices_data['domain']
                    del practices_data['cmmc_levels']

                except:
                    pass

                for practice_name, practice_data in practices_data.items():

                    practice_data['control_name'] = practice_name

                    yield {
                        'control_name': practice_name,
                        'practice_description': practice_data['practice_description'],
                        'cmmc_clarification': practice_data['cmmc_clarification'],
                        'mappings': practice_data['mappings'],
                        'assessment_objectives': practice_data['assessment_objectives'],
                        'potential_assessment_methods': practice_data['potential_assessment_methods'],
                        'further_discussion': practice_data['further_discussion'],
                        'potential_assessment_considerations': practice_data['potential_assessment_considerations'],
                        'process_automation': practice_data['process_automation'],
                        'possible_technology_considerations': practice_data['possible_technology_considerations'],
                        'cmmc_source_discussion': practice_data['cmmc_source_discussion'],
                        'suggested_technologies': practice_data['suggested_technologies'],
                        'suggested_implementation': practice_data['suggested_implementation'],
                        'sourcetype': sourcetype,
                        '_time': _time,
                        '_raw': {
                            '_time': _time,
                            'control': practice_data,
                            'sourcetype': sourcetype,
                            'control_name': practice_name
                        }
                    }


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Get Control Info command execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Get Control Info command started at {timestamp}."')
        return


if __name__ == '__main__':
    dispatch(
        GenerateCommand,
        sys.argv,
        sys.stdin,
        sys.stdout,
        __name__
    )
