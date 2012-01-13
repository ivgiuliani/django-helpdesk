from django.test import TestCase
from django.test.client import Client
from django.utils import simplejson
from django.core.urlresolvers import reverse

from helpdesk.views import api


class APITest(TestCase):
    urls = "helpdesk.urls"
    fixtures = ["test_fixtures.json"]

    def api_call(self, method, data):
        "Convenience method for easier API calling"
        client = Client()
        post_data = {
            "user": "admin",
            "password": "admin",
        }
        post_data.update(data)
        return client.post(reverse("helpdesk_api", args=(method, )), post_data)

    def testOnlyPostRequestsGetAccepted(self):
        "GET requests to API must be ignored"
        client = Client()

        response = client.get(reverse("helpdesk_api", args=("list_queues",)))
        self.assertEqual(response.status_code, 405)

        response = client.post(reverse("helpdesk_api", args=("list_queues",)), {
            "user": "admin",
            "password": "admin",
        })
        self.assertEqual(response.status_code, 200)

    def testGetTicket(self):
        "Test get_ticket API method"
        non_existent_ticket = self.api_call("get_ticket", { "ticket": 25 })
        self.assertEqual(non_existent_ticket.status_code,
                         api.STATUS_ERROR_NOT_FOUND,
                         "API call didn't fail on inexisting ticket")

        existing_ticket = self.api_call("get_ticket", { "ticket": 1 })
        self.assertEqual(existing_ticket.status_code, api.STATUS_OK,
                        "Existing ticket hasn't been returned")

        ticket = simplejson.loads(existing_ticket.content)
        self.assertIsNotNone(ticket)

        self.assertEquals(ticket["description"], "ticket description")
        self.assertEquals(ticket["queue"], 1)
        self.assertEquals(ticket["submitter_email"], "customer@customer.com")
