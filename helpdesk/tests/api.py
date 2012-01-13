from django.utils import unittest
from django.contrib.auth.models import User
from django.test.client import Client
from django.core.urlresolvers import reverse

from helpdesk.models import Ticket, Queue


class APITest(unittest.TestCase):
    urls = "helpdesk.urls"

    def setUp(self):
        "Creates some test data that can be used later on in tests"
        self.admin_user = User.objects.create_user("admin",
                                                   "admin@admin.com",
                                                   "adminpwd")
        self.admin_user.is_superuser = True
        self.admin_user.is_staff = True
        self.admin_user.save()

        self.normal_user = User.objects.create_user("normal",
                                                    "normal@normal.com",
                                                    "normalpwd")
        self.normal_user.save()

        self.queue = Queue(
            title="Queue title",
            slug="queue",
        )
        self.queue.save()

        self.ticket = Ticket(
            title="Ticket title",
            description="Ticket description",
            queue=self.queue,
            submitter_email="test@example.com",
            priority=3,
        )
        self.ticket.save()

    def testOnlyPostRequestsGetAccepted(self):
        "GET requests to API must be ignored"
        client = Client()

        response = client.get(reverse("helpdesk_api", args=("list_queues",)))
        self.assertEqual(response.status_code, 405)

        response = client.post(reverse("helpdesk_api", args=("list_queues",)), {
            "user": "admin",
            "password": "adminpwd",
        })
        self.assertEqual(response.status_code, 200)
