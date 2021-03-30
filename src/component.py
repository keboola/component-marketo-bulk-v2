'''
Keboola Marketo Bulk Extractor

'''
import sys
import logging
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

from keboola.component import CommonInterface
from marketo import Marketo


sys.tracebacklimit = 0

# Disabling list of libraries you want to output in the logger
disable_libraries = [
    'urllib3',
    'requests'
]
for library in disable_libraries:
    logging.getLogger(library).disabled = True


# configuration variables
KEY_MUNCHKINID = 'munchkinid'
KEY_CLIENT_ID = 'client_id'
KEY_CLIENT_SECRET = '#client_secret'
KEY_QUERY = 'query'


# #### Keep for debug
KEY_DEBUG = 'debug'

# list of mandatory parameters => if some is missing,
# component will fail with readable message on initialization.
REQUIRED_PARAMETERS = [
    KEY_MUNCHKINID,
    KEY_CLIENT_ID,
    KEY_CLIENT_SECRET,
    KEY_QUERY
]
REQUIRED_IMAGE_PARS = []

APP_VERSION = '0.0.1'


def get_local_data_path():
    return Path(__file__).resolve().parent.parent.joinpath('data').as_posix()


def get_data_folder_path():
    data_folder_path = None
    if not os.environ.get('KBC_DATADIR'):
        data_folder_path = get_local_data_path()
    return data_folder_path


class Component(CommonInterface):
    def __init__(self, debug=False):
        # for easier local project setup
        data_folder_path = get_data_folder_path()
        super().__init__(data_folder_path=data_folder_path)

        # override debug from config
        if self.configuration.parameters[KEY_DEBUG]:
            debug = True
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.info('Running version %s', APP_VERSION)
            logging.info('Loading configuration...')

        try:
            # validation of required parameters. Produces ValueError
            self.validate_configuration(REQUIRED_PARAMETERS)
            self.validate_image_parameters(REQUIRED_IMAGE_PARS)
        except ValueError as e:
            logging.exception(e)
            exit(1)

    def run(self):
        '''
        Main execution code
        '''
        params = self.configuration.parameters

        # Validating User input configurations
        self.validate_user_parameters(params)

        # Read the parameters
        # Credentials parameters
        munchkin_id = params.get(KEY_MUNCHKINID)
        client_id = params.get(KEY_CLIENT_ID)
        client_secret = params.get(KEY_CLIENT_SECRET)

        # Endpoint parameters
        query = params.get(KEY_QUERY)
        endpoint = query.get('endpoint')
        created_param = query.get('created_at')[0]
        month_year_created = created_param['value'] if created_param['type'] == 'month/year' else ''
        dayspan_created = created_param['value'] if created_param['type'] == 'dayspan' else ''

        # Leads Endpoint optional parmaeters
        updated_param = query.get('updated_at')[0]
        month_year_updated = updated_param['value'] if updated_param['type'] == 'month/year' else ''
        dayspan_updated = updated_param['value'] if updated_param['type'] == 'dayspan' else ''
        fields_str_tmp = query.get('desired_fields')
        fields_str = [i.strip() for i in fields_str_tmp.split(',')]

        # Activities Endpoint optinal parameters
        desired_activities_tmp = params.get('desired_activities')
        desired_activities = [i.strip()
                              for i in desired_activities_tmp.split(",")]

        # Outputing log if parameters are configured
        logging.info("Endpoint: %s" % endpoint)
        logging.info("Dayspan updated: %s" %
                     dayspan_updated) if dayspan_updated else ''
        logging.info("Dayspan created: %s" %
                     dayspan_created) if dayspan_created else ''
        logging.info("Desired activities: %s" %
                     str(desired_activities)) if desired_activities_tmp else ''
        logging.info("Month/Year updated: %s" %
                     month_year_updated) if month_year_updated else ''
        logging.info("Month/Year created: %s" %
                     month_year_created) if month_year_created else ''
        logging.info("Desired fields: %s" %
                     str(fields_str)) if fields_str_tmp else ''

        # Request parameters based on user inputs
        CREATED_DATE, start_created, end_created = self.create_date_ranges(
            dayspan_created, month_year_created, 'Created')
        UPDATED_DATE, start_updated, end_updated = self.create_date_ranges(
            dayspan_updated, month_year_updated, 'Updated')

        date_obj = {
            'created_date_bool': CREATED_DATE,
            'start_created_date': start_created,
            'end_created_date': end_created,
            'updated_date_bool': UPDATED_DATE,
            'start_updated_date': start_updated,
            'end_updated_date': end_updated
        }

        # Marketo class
        marketo = Marketo(munchkin_id=munchkin_id,
                          client_id=client_id, client_secret=client_secret)

        # Endpoint Request
        data_out = marketo.fetch_endpoint(endpoint=endpoint.lower(
        ), date_obj=date_obj, desired_activities=desired_activities, fields_str=fields_str)

        # Output data
        self.output_file(endpoint=endpoint, data_in=data_out)

    def validate_user_parameters(self, params):
        # 1 - check if the configuration is empty
        if not params or params == {}:
            logging.error('Please configure your component.')
            sys.exit(1)

        # 2 - Check if all the credentials are entered
        if not params.get(KEY_CLIENT_ID) or not params.get(KEY_MUNCHKINID) or not params.get(KEY_CLIENT_SECRET):
            logging.error(
                "Credentials are missing: [Client ID], [Munchkin ID], [Client Secret]")
            sys.exit(1)

        # 3 - ensure row base configuration is configured
        if not params.get(KEY_QUERY):
            logging.error(
                'Configuration row is missing. Please configure your configuration row.')
            sys.exit(1)

        query = params.get(KEY_QUERY)
        # 4 - ensure the endpoints are supported
        endpoint = query.get('endpoint')
        if endpoint not in ('Activities', 'Leads'):
            logging.error('Specified endpoint is not supported.')
            sys.exit(1)

        # 5 - when endpoint leads is selected, desired fields cannot be empty
        fields_str_tmp = query.get('desired_fields')
        fields_str = [i.strip() for i in fields_str_tmp.split(",")
                      ] if fields_str_tmp else ''
        if endpoint == 'Leads' and len(fields_str) == 0:
            logging.error(
                "Please specify [Desired Fields] when endpoint [Leads] is selected.")
            sys.exit(1)

    def create_date_ranges(self, dayspan, month_year, date_type):
        '''
        Created Filter
        Determine whether we want to get data from apst X days or from a specific month/year
        '''
        # Return parameters
        CREATED_DATE = False
        start_date = ''
        end_date = ''

        if dayspan != '':
            # Using the dayspan value regardless if the created value is empty or not
            CREATED_DATE = True
            start_date = str(
                (datetime.utcnow() - timedelta(days=int(dayspan))).date())
            end_date = str(datetime.utcnow().date())

            # Disregarding Created value is not empty
            if month_year != '':
                logging.info(f'Disregarding the <Month/Year for      \'{date_type}\'> parameter, taking into consideration only \
                     the <How many days back you want to go with \'{date_type}\'?> parameter''Disregrading the <Month/\
                    Year ')

        # when dayspan variable is not specified
        else:
            if month_year != '':
                CREATED_DATE = True
                month = month_year[:3].lower()
                year = int(month_year[4:])
                if year % 4 == 0 and year % 400 != 0:
                    feb_length = '29'
                else:
                    feb_length = '28'
                year = str(year)
                months = {
                    'jan': [year + "-01-01T00:00:00Z", year + "-01-31T23:59:59Z"],
                    'feb': [year + "-02-01T00:00:00Z", year + "-02-" + feb_length + "T23:59:59Z"],
                    'mar': [year + "-03-01T00:00:00Z", year + "-03-31T23:59:59Z"],
                    'apr': [year + "-04-01T00:00:00Z", year + "-04-30T23:59:59Z"],
                    'may': [year + "-05-01T00:00:00Z", year + "-05-31T23:59:59Z"],
                    'jun': [year + "-06-01T00:00:00Z", year + "-06-30T23:59:59Z"],
                    'jul': [year + "-07-01T00:00:00Z", year + "-07-31T23:59:59Z"],
                    'aug': [year + "-08-01T00:00:00Z", year + "-08-31T23:59:59Z"],
                    'sep': [year + "-09-01T00:00:00Z", year + "-09-30T23:59:59Z"],
                    'oct': [year + "-10-01T00:00:00Z", year + "-10-31T23:59:59Z"],
                    'nov': [year + "-11-01T00:00:00Z", year + "-11-30T23:59:59Z"],
                    'dec': [year + "-12-01T00:00:00Z", year + "-12-31T23:59:59Z"]
                }
                start_date = months[month][0][:10]
                end_date = months[month][1][:10]

            else:
                CREATED_DATE = False
                logging.info(f'{date_type} date is not provided.')

        return CREATED_DATE, start_date, end_date

    def output_file(self, endpoint, data_in):

        # Output file destination
        output_file_name = endpoint + '_bulk.csv'
        output_file_destination = f'{self.tables_out_path}/{output_file_name}'

        # Outputting sequence
        if len(list(data_in)) == 0:
            logging.info(
                'The export from the API reached state Completed, but no data were transferred from the API.')
        else:
            # Output file
            csv_file = open(output_file_destination, 'wb')
            csv_file.write(data_in)
            csv_file.close()

            # Output Manifest
            pk = ['marketoGUID'] if endpoint == 'activities' else ['id']
            self.save_manifest(
                file_name=output_file_name, primary_keys=pk)

            logging.info(f'{endpoint} exported.')

    def save_manifest(self, file_name, primary_keys):
        """
        Dummy function for returning manifest
        """

        file = '/data/out/tables/' + file_name + ".manifest"

        logging.info("Manifest output: {0}".format(file))

        manifest = {
            'destination': '',
            'incremental': True,
            'primary_key': primary_keys
        }

        try:
            with open(file, 'w') as file_out:
                json.dump(manifest, file_out)
                logging.info(
                    "Output manifest file ({0}) produced.".format(file))
        except Exception as e:
            logging.error("Could not produce output file manifest.")
            logging.error(e)


"""
        Main entrypoint
"""
if __name__ == "__main__":
    try:
        comp = Component()
        comp.run()
    except Exception as exc:
        logging.exception(exc)
        exit(2)
