from django.test import TestCase
from django.test.client import Client
from django.utils import simplejson
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from helpdesk.views import api
from helpdesk.models import Ticket, Queue, FollowUp

import datetime
import tempfile


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

        response = client.post(
                        reverse("helpdesk_api", args=("list_queues",)), {
                            "user": "admin",
                            "password": "admin",
                        })
        self.assertEqual(response.status_code, 200)

    def testGetTicket(self):
        "Test get_ticket API method"
        non_existent_ticket = self.api_call("get_ticket", {"ticket": 25})
        self.assertEqual(non_existent_ticket.status_code,
                         api.STATUS_ERROR_NOT_FOUND,
                         "API call didn't fail on inexisting ticket")

        existing_ticket = self.api_call("get_ticket", {"ticket": 1})
        self.assertEqual(existing_ticket.status_code, api.STATUS_OK,
                        "Existing ticket hasn't been returned")

        ticket = simplejson.loads(existing_ticket.content)
        self.assertIsNotNone(ticket)

        self.assertEquals(ticket["description"], "ticket description")
        self.assertEquals(ticket["queue"], 1)
        self.assertEquals(ticket["submitter_email"], "customer@customer.com")
        self.assertEquals(ticket["assigned_to"], 1)

        ticket_obj = Ticket.objects.get(id=1)
        ticket_obj.assigned_to = None
        ticket_obj.save()

        existing_ticket = self.api_call("get_ticket", {"ticket": 1})
        ticket = simplejson.loads(existing_ticket.content)
        self.assertIsNotNone(ticket)

        self.assertEquals(ticket["description"], "ticket description")
        self.assertEquals(ticket["queue"], 1)
        self.assertEquals(ticket["submitter_email"], "customer@customer.com")
        self.assertIsNone(ticket["assigned_to"])

    def testGetFollowupsForTicket(self):
        response = self.api_call("get_followups", {"ticket": 25})
        self.assertEquals(response.status_code,
                          api.STATUS_ERROR_NOT_FOUND)

        response = self.api_call("get_followups", {"ticket": 1})
        self.assertEquals(response.status_code,
                          api.STATUS_OK)

        followups = simplejson.loads(response.content)
        self.assertEquals(len(followups), 0)

        ticket = Ticket.objects.get(id=1)
        f = FollowUp(ticket=ticket,
                     date=datetime.datetime.now(),
                     comment="first comment",
                     user=User.objects.get(username="admin"),
                     public=True,
                     title="Comment added")
        f.save()
        response = self.api_call("get_followups", {"ticket": 1})
        followups = simplejson.loads(response.content)
        self.assertEquals(len(followups), 1)

        f = FollowUp(ticket=ticket,
                     date=datetime.datetime.now(),
                     comment="private comment",
                     user=User.objects.get(username="admin"),
                     public=False,
                     title="Comment added")
        f.save()

        response = self.api_call("get_followups", {
            "ticket": 1,
            "private": 'n',
        })
        followups = simplejson.loads(response.content)
        self.assertEquals(len(followups), 1)

        response = self.api_call("get_followups", {
            "ticket": 1,
            "private": 'y',
        })
        followups = simplejson.loads(response.content)
        self.assertEquals(len(followups), 2)

    def testListTickets(self):
        response = self.api_call("list_tickets", {"queue": 2000})
        self.assertEquals(response.status_code,
                          api.STATUS_ERROR_NOT_FOUND)

        response = self.api_call("list_tickets", {"queue": 1})
        self.assertEquals(response.status_code,
                          api.STATUS_OK)
        ticket_list = simplejson.loads(response.content)
        self.assertEquals(len(ticket_list), 1)
        self.assertEquals(ticket_list[0], 1)

        # create a bunch of tickets for testing
        t_reopened = Ticket.objects.create(title="Ticket no. 2 (reopened)",
                                           queue=Queue.objects.get(id=1),
                                           submitter_email="test@test.com",
                                           description="description",
                                           status=Ticket.REOPENED_STATUS)

        t_closed = Ticket.objects.create(title="Ticket no. 3 (closed)",
                                         queue=Queue.objects.get(id=1),
                                         submitter_email="test@test.com",
                                         description="description",
                                         status=Ticket.CLOSED_STATUS)

        t_resolved = Ticket.objects.create(title="Ticket no. 4 (resolved)",
                                           queue=Queue.objects.get(id=1),
                                           submitter_email="test@test.com",
                                           description="description",
                                           status=Ticket.RESOLVED_STATUS)

        t_dup = Ticket.objects.create(title="Ticket no. 5 (duplicate)",
                                      queue=Queue.objects.get(id=1),
                                      submitter_email="test@test.com",
                                      description="description",
                                      status=Ticket.DUPLICATE_STATUS)

        response = self.api_call("list_tickets", {
            "queue": 1,
            "open": 'n',
        })
        self.assertEquals(len(simplejson.loads(response.content)), 0)

        response = self.api_call("list_tickets", {
            "queue": 1,
            "open": 'y',
        })
        self.assertEquals(len(simplejson.loads(response.content)), 2)

        response = self.api_call("list_tickets", {
            "queue": 1,
            "closed": 'y',
        })
        self.assertEquals(len(simplejson.loads(response.content)), 3)

        response = self.api_call("list_tickets", {
            "queue": 1,
            "resolved": 'y',
        })
        self.assertEquals(len(simplejson.loads(response.content)), 3)

        response = self.api_call("list_tickets", {
            "queue": 1,
            "duplicate": 'y',
        })
        self.assertEquals(len(simplejson.loads(response.content)), 3)

        response = self.api_call("list_tickets", {
            "queue": 1,
            "open": 'y',
            "closed": 'y',
            "resolved": 'y',
            "duplicate": 'y',
        })
        self.assertEquals(len(simplejson.loads(response.content)), 5)

    def testUserFromId(self):
        response = self.api_call("find_user_from_id", {
            "user_id": 1,
        })
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.content, "admin")

        response = self.api_call("find_user_from_id", {
            "user_id": 200,
        })
        self.assertEquals(response.status_code, 404)

    def testAddFollowup(self):
        response = self.api_call("add_followup", {
            "ticket": 1,
            "message": "simple followup",
            "public": 'y',
        })
        self.assertEquals(response.status_code, 200)
        response = self.api_call("get_followups", {
            "ticket": 1,
        })
        followups = simplejson.loads(response.content)
        self.assertEqual(len(followups), 1)
        self.assertEqual(followups[0]["comment"], "simple followup")
        self.assertEqual(followups[0]["public"], True)

    def testAddPrivateFollowup(self):
        response = self.api_call("add_followup", {
            "ticket": 1,
            "message": "private followup",
            "public": 'n',
        })
        self.assertEquals(response.status_code, 200)
        response = self.api_call("get_followups", {
            "ticket": 1,
        })
        followups = simplejson.loads(response.content)
        self.assertEqual(len(followups), 1)
        self.assertEqual(followups[0]["comment"], "private followup")
        self.assertEqual(followups[0]["public"], False)

    def testAddFollowupWithSingleAttachment(self):
        "Test a file upload together with an attachment"
        with tempfile.TemporaryFile() as f:
            f.write("content")
            f.seek(0)
            self.api_call("add_followup", {
                "user": "admin",
                "password": "admin",
                "ticket": 1,
                "message": "this followup has an attachment",
                "public": 'y',
                "attachment": [ f ],
            })

        response = self.api_call("get_followups", {
            "ticket": 1,
        })
        followups = simplejson.loads(response.content)
        self.assertEqual(len(followups), 1)
        attachments = followups[0]["attachments"]
        self.assertEqual(len(attachments), 1)

    def testAddFollowupWithMultipleAttachments(self):
        with tempfile.TemporaryFile() as f1:
            with tempfile.TemporaryFile() as f2:
                f1.write("content1")
                f2.write("content2")

                f1.seek(0)
                f2.seek(0)

                self.api_call("add_followup", {
                    "user": "admin",
                    "password": "admin",
                    "ticket": 1,
                    "message": "this followup has two attachments",
                    "public": 'y',
                    "attachment": [ f1, f2 ],
                })

        response = self.api_call("get_followups", {
            "ticket": 1,
        })
        followups = simplejson.loads(response.content)
        self.assertEqual(len(followups), 1)
        attachments = followups[0]["attachments"]
        self.assertEqual(len(attachments), 2)
