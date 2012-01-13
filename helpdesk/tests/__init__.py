from django.utils import unittest

TEST_MODULES = [
    "helpdesk.tests.api",
]

def suite():
    suite = unittest.TestSuite()

    for module in TEST_MODULES:
        testloader = unittest.TestLoader()
        suite.addTest(testloader.loadTestsFromName(module))

    return suite
