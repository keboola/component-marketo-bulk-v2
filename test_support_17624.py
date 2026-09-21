"""Regression guard for SUPPORT-17624.

Marketo stopped accepting the OAuth token as an ``access_token`` query
parameter on 2026-08-31. Every Bulk Extract request must carry it in an
``Authorization: Bearer`` header instead.

All Bulk Extract calls go through Marketo.get_request, post_request and
get_stream_request, so these tests cover every call site.
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from marketo import Marketo  # noqa: E402


class FakeResponse(object):
    status_code = 200

    def json(self):
        return {'success': True}

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=None):
        return iter([b'a,b\n1,2\n'])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def build_client():
    """A Marketo client with a known token, without calling the auth endpoint."""
    with mock.patch.object(Marketo, 'authenticate', return_value='TOKEN'):
        return Marketo('munchkin', 'id', 'secret', '/tmp')


class TestTokenTransport(unittest.TestCase):
    """The token must travel in the header, never in the query string."""

    def assert_bearer(self, request):
        kwargs = request.call_args[1]
        self.assertEqual('Bearer TOKEN', kwargs['headers'].get('Authorization'))
        self.assertNotIn('access_token', kwargs.get('params') or {})

    def test_get_request_uses_authorization_header(self):
        client = build_client()
        with mock.patch('marketo.requests.get', return_value=FakeResponse()) as request:
            client.get_request('https://x.mktorest.com/bulk/v1/leads/export.json', params={})
        self.assert_bearer(request)

    def test_post_request_uses_authorization_header(self):
        client = build_client()
        with mock.patch('marketo.requests.post', return_value=FakeResponse()) as request:
            client.post_request('https://x.mktorest.com/bulk/v1/leads/export/create.json',
                                params={}, body={'format': 'CSV'})
        self.assert_bearer(request)

    def test_get_stream_request_uses_authorization_header(self):
        client = build_client()
        destination = os.path.join('/tmp', 'support_17624_stream.csv')
        with mock.patch('marketo.requests.get', return_value=FakeResponse()) as request:
            client.get_stream_request(destination,
                                      'https://x.mktorest.com/bulk/v1/leads/export/1/file.json',
                                      params={})
        self.assert_bearer(request)
        os.remove(destination)


class TestExportParamsCarryNoToken(unittest.TestCase):
    """The query params built for an export must not contain the token."""

    def test_fetch_endpoint_params_have_no_access_token(self):
        client = build_client()
        calls = []

        def record(url, request_param, *args, **kwargs):
            calls.append(request_param)
            raise StopIteration('stop after the first call')

        with mock.patch.object(Marketo, 'create_export', side_effect=record):
            date_obj = {
                'updated_date_bool': True,
                'start_updated_date': '2026-09-01',
                'end_updated_date': '2026-09-02',
                'created_date_bool': False,
            }
            try:
                client.fetch_endpoint('leads', date_obj, [], 'id,email')
            except StopIteration:
                pass

        self.assertEqual(1, len(calls))
        self.assertNotIn('access_token', calls[0])


if __name__ == '__main__':
    unittest.main()
