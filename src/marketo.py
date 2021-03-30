
import sys
import logging
import requests
import time

# Disabling list of libraries you want to output in the logger
disable_libraries = [
    'urllib3',
    'requests'
]
for library in disable_libraries:
    logging.getLogger(library).disabled = True


class Marketo():

    def __init__(self, munchkin_id, client_id, client_secret):

        self.BASE_URL = f'https://{munchkin_id}.mktorest.com'
        self.access_token = self.authenticate(client_id, client_secret)

    def get_request(self, url, params=None):

        try:
            response = requests.get(url, params=params)
        except Exception as err:
            logging.error(f'Error occured: {err}')
            sys.exit(1)

        return response

    def post_request(self, url, params=None, body=None):

        try:
            response = requests.post(url, params=params, json=body)
        except Exception as err:
            logging.error(f'Error occured: {err}')
            sys.exit(1)

        return response

    def authenticate(self, client_id, client_secret):

        auth_url = f'{self.BASE_URL}/identity/oauth/token'
        params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }

        response = requests.get(url=auth_url, params=params)
        self.check_response(response, 'Fetching access token')

        return response.json()['access_token']

    def check_response(self, response, stage):
        if response.status_code != 200:
            logging.error(f'[{response.status_code}] - {stage} failed.')
            sys.exit(1)
        else:
            logging.info(stage)

    def fetch_endpoint(self, endpoint, date_obj, desired_activities, fields_str):
        '''
        Endpoint: Activities
        '''

        # Request parameters
        request_url = f'{self.BASE_URL}/bulk/v1/{endpoint}/export'
        request_param = {
            'access_token': self.access_token
        }
        request_body = {
            'format': 'CSV'
        }

        # setting up request parameters depending on endpoint
        if endpoint == 'activities':
            # Create date parameters
            if not date_obj['created_date_bool']:
                logging.error(
                    'The Activities endpoint requires Created Date interval.')
                sys.exit(1)
            else:
                request_body['filter'] = {}
                created_at = {
                    'startAt': date_obj['start_created_date'],
                    'endAt': date_obj['end_created_date']
                }
                request_body['filter']['createdAt'] = created_at

            # Update date parameters
            if date_obj['updated_date_bool']:
                updated_at = {
                    'startAt': date_obj['start_updated_date'],
                    'endAt': date_obj['end_updated_date']
                }
                request_body['filter']['updatedAt'] = updated_at

            # activities specificiations
            if len(desired_activities) > 0:
                request_body['filter']['activityTypeIds'] = desired_activities

        elif endpoint == 'leads':
            request_body['fields'] = fields_str

            # Filter parameters
            if not date_obj['updated_date_bool'] and not date_obj['created_date_bool']:
                logging.error(
                    'The Leads endpoint requries either Created or Updated parameter.')
                sys.exit(1)

            else:
                request_body['filter'] = {}

            # Update paramaters
            if date_obj['updated_date_bool']:
                updated_at = {
                    'startAt': date_obj['start_updated_date'],
                    'endAt': date_obj['end_updated_date']
                }
                request_body['filter']['updatedAt'] = updated_at

            # Create parameters
            if date_obj['created_date_bool']:
                created_at = {
                    'startAt': date_obj['start_created_date'],
                    'endAt': date_obj['end_created_date']
                }
                request_body['filter']['createdAt'] = created_at

        # 1 - Create exports
        export_id = self.create_export(
            request_url, request_param, request_body)

        # 2 - Enqueue export
        self.enqueue_export(request_url, request_param, export_id)

        # 3 - loop while waiting for the report to be ready
        ready_bool = False
        while not ready_bool:
            ready_bool = self.check_export_status(
                request_url, request_param, export_id)

        # 4 - Outputing the file
        data_out = self.output_export(
            request_url, request_param, export_id, endpoint)

        return data_out

    def create_export(self, request_url, request_param, request_body):

        export_url = f'{request_url}/create.json'
        create_export = self.post_request(
            export_url, request_param, request_body)
        self.check_response(create_export, 'Creating export')

        if not create_export.json()['success']:
            logging.error(
                f'Creating export was not successful; Errors: {create_export.json()["errors"]}')
            sys.exit(1)

        export_id = create_export.json()['result'][0]['exportId']
        logging.info(f'Export ID: [{export_id}]')

        return export_id

    def enqueue_export(self, request_url, request_param, export_id):

        enqueue_url = f'{request_url}/{export_id}/enqueue.json'
        enqueue_export = self.post_request(
            enqueue_url, request_param, body=None)
        self.check_response(enqueue_export, 'Enqueuing export')

    def check_export_status(self, request_url, request_param, export_id):

        time.sleep(60)

        ready_bool = False
        status_url = f'{request_url}/{export_id}/status.json'
        status_export = self.get_request(status_url, params=request_param)
        self.check_response(status_export, 'Standing by for export status')

        try:
            if status_export.json()['result'][0]['status'] == 'Completed':
                ready_bool = True
        except KeyError:
            logging.error("There was a problem when obtaining the status of the export.\
            Please try rerunning the configuration as the API sometimes behaves unpredictably.")
            logging.error(f'Response: {status_export.json()}')
            sys.exit(1)
        except Exception as e:
            logging.error(e)
            sys.exit(1)

        return ready_bool

    def output_export(self, request_url, request_param, export_id, endpoint):
        '''
        # Output file destination
        output_file_name = endpoint.capitalize() + '_bulk.csv'
        output_file_destination = self.tables_out_path + output_file_name
        '''

        # Output file request parameter
        output_url = f'{request_url}/{export_id}/file.json'

        response = self.get_request(output_url, request_param)

        return response.content
