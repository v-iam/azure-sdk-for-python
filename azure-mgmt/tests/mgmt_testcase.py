#-------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#--------------------------------------------------------------------------
import json
import os.path
import time
from azure.mgmt.resource import ResourceManagementClient

from azure_devtools.scenario_tests.base import ScenarioTest
from azure_devtools.scenario_tests.const import DUMMY_HEADER_DEACTIVATE_VCR_RECORDING

from azure.common.exceptions import (
    CloudError
)
from azure_devtools.scenario_tests.preparers import (
    AbstractPreparer,
    SingleValueReplacer,
)
from testutils.common_recordingtestcase import (
    RecordingTestCase,
    TestMode,
)
import tests.mgmt_settings_fake as fake_settings


should_log = os.getenv('SDK_TESTS_LOG', '0')
if should_log.lower() == 'true' or should_log == '1':
    import logging
    logger = logging.getLogger('msrest')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


class HttpStatusCode(object):
    OK = 200
    Created = 201
    Accepted = 202
    NoContent = 204
    NotFound = 404


class AzureMgmtPreparer(AbstractPreparer, SingleValueReplacer):
    def __init__(self, **kwargs):
        super(AzureMgmtPreparer, self).__init__(self, **kwargs)
        self.fake_settings = fake_settings
        if TestMode.is_playback(self.test_mode):
            self.settings = self.fake_settings
        else:
            import tests.mgmt_settings_real as real_settings
            self.settings = real_settings

    def _make_unrecorded_request(self, func, *args, **kwargs):
        kwargs.setdefault('custom_headers', {})[DUMMY_HEADER_DEACTIVATE_VCR_RECORDING] = ''
        return func(*args, **kwargs)

    def create_basic_client(self, client_class, **kwargs):
        # Whatever the client, if credentials is None, fail
        with self.assertRaises(ValueError):
            client = client_class(
                credentials=None,
                **kwargs
            )
        # Whatever the client, if accept_language is not str, fail
        with self.assertRaises(TypeError):
            client = client_class(
                credentials=self.settings.get_credentials(),
                accept_language=42,
                **kwargs
            )

        # Real client creation
        client = client_class(
            credentials=self.settings.get_credentials(),
            **kwargs
        )
        if self.is_playback():
            client.config.long_running_operation_timeout = 0
        return client

    def create_mgmt_client(self, client_class, **kwargs):
        # Whatever the client, if subscription_id is None, fail
        with self.assertRaises(ValueError):
            self.create_basic_client(
                client_class,
                subscription_id=None,
                **kwargs
            )
        # Whatever the client, if subscription_id is not a string, fail
        with self.assertRaises(TypeError):
            self.create_basic_client(
                client_class,
                subscription_id=42,
                **kwargs
            )

        return self.create_basic_client(
            client_class,
            subscription_id=self.settings.SUBSCRIPTION_ID,
            **kwargs
        )

class AzureMgmtTestCase(ScenarioTest):

    def setUp(self):
        self.working_folder = os.path.dirname(__file__)

        super(AzureMgmtTestCase, self).setUp()

        self.fake_settings = fake_settings
        if TestMode.is_playback(self.test_mode):
            self.settings = self.fake_settings
        else:
            import tests.mgmt_settings_real as real_settings
            self.settings = real_settings

        self.resource_client = self.create_mgmt_client(ResourceManagementClient)

        # Every test uses a different resource group name calculated from its
        # qualified test name.
        #
        # When running all tests serially, this allows us to delete
        # the resource group in teardown without waiting for the delete to
        # complete. The next test in line will use a different resource group,
        # so it won't have any trouble creating its resource group even if the
        # previous test resource group hasn't finished deleting.
        #
        # When running tests individually, if you try to run the same test
        # multiple times in a row, it's possible that the delete in the previous
        # teardown hasn't completed yet (because we don't wait), and that
        # would make resource group creation fail.
        # To avoid that, we also delete the resource group in the
        # setup, and we wait for that delete to complete.
        self.group_name = self.get_resource_name(
            self.qualified_test_name.replace('.', '_')
        )
        self.region = 'westus'

        if not self.is_playback():
            self.delete_resource_group(wait_timeout=600)

    def tearDown(self):
        if not self.is_playback():
            self.delete_resource_group(wait_timeout=None)
        return super(AzureMgmtTestCase, self).tearDown()

    def create_basic_client(self, client_class, **kwargs):
        # Whatever the client, if credentials is None, fail
        with self.assertRaises(ValueError):
            client = client_class(
                credentials=None,
                **kwargs
            )
        # Whatever the client, if accept_language is not str, fail
        with self.assertRaises(TypeError):
            client = client_class(
                credentials=self.settings.get_credentials(),
                accept_language=42,
                **kwargs
            )

        # Real client creation
        client = client_class(
            credentials=self.settings.get_credentials(),
            **kwargs
        )
        if self.is_playback():
            client.config.long_running_operation_timeout = 0
        return client

    def create_mgmt_client(self, client_class, **kwargs):
        # Whatever the client, if subscription_id is None, fail
        with self.assertRaises(ValueError):
            self.create_basic_client(
                client_class,
                subscription_id=None,
                **kwargs
            )
        # Whatever the client, if subscription_id is not a string, fail
        with self.assertRaises(TypeError):
            self.create_basic_client(
                client_class,
                subscription_id=42,
                **kwargs
            )

        return self.create_basic_client(
            client_class,
            subscription_id=self.settings.SUBSCRIPTION_ID,
            **kwargs
        )

    def _scrub(self, val):
        val = super(AzureMgmtTestCase, self)._scrub(val)
        real_to_fake_dict = {
            self.settings.SUBSCRIPTION_ID: self.fake_settings.SUBSCRIPTION_ID,
            self.settings.AD_DOMAIN:  self.fake_settings.AD_DOMAIN
        }
        val = self._scrub_using_dict(val, real_to_fake_dict)
        return val


class ResourceGroupPreparer(AzureMgmtPreparer):
    def __init__(self, name_prefix='sdktest.rg',
                 parameter_name='resource_group_name',
                 parameter_name_for_location='location', location='westus',
                 parameter_name_for_client='resource_client',
                 random_name_length=75):
        super(ResourceGroupPreparer, self).__init__(name_prefix, random_name_length)
        self.location = location
        self.parameter_name = parameter_name
        self.parameter_name_for_location = parameter_name_for_location
        self.parameter_name_for_client = parameter_name_for_client

        self.client = self.create_mgmt_client(
            azure.mgmt.resource.ResourceManagementClient
        )

    def create_resource(self, name, **kwargs):
        self.group = self._make_unrecorded_request(
            self.client.resource_groups.create_or_update,
            name, {'location': self.region}
        )
        return {
            self.parameter_name: name,
            self.parameter_name_for_location: self.location,
            self.parameter_name_for_client: self.client,
        }

    def remove_resource(self, name, **kwargs):
        try:
            if wait_timeout:
                azure_poller = self._make_unrecorded_request(
                    self.resource_client.resource_groups.delete,
                    name
                )
                azure_poller.wait(kw.get('wait_timeout'))
                if azure_poller.done():
                    return
                self.assertTrue(False, 'Timed out waiting for resource group to be deleted.')            
            else:
                self._make_unrecorded_request(
                    self.resource_client.resource_groups.delete,
                    name,
                    raw=True
                )
        except CloudError:
            pass