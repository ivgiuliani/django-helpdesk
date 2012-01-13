from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse

from helpdesk.views import api


class APITest(TestCase):
    urls = "helpdesk.urls"
    fixtures = ["test_fixtures.json"]

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
