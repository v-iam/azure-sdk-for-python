#-------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#--------------------------------------------------------------------------
import inspect
import os.path
import zlib

from azure.common.exceptions import CloudError
from azure.mgmt.resource import ResourceManagementClient

from azure_devtools.scenario_tests import (ReplayableTest, AzureTestError,
                                           AbstractPreparer, SingleValueReplacer)
from testutils.config import TEST_SETTING_FILENAME
import mgmt_settings_fake as fake_settings


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


def get_resource_name(name_prefix, identifier):
    # Append a suffix to the name, based on the fully qualified test name
    # We use a checksum of the test name so that each test gets different
    # resource names, but each test will get the same name on repeat runs,
    # which is needed for playback.
    # Most resource names have a length limit, so we use a crc32
    checksum = zlib.adler32(identifier) & 0xffffffff
    name = '{}{}'.format(name_prefix, hex(checksum)[2:]).rstrip('L')
    if name.endswith('L'):
        name = name[:-1]
    return name


def get_qualified_test_name(test_object, method_name):
    # example of qualified test name:
    # test_mgmt_network.test_public_ip_addresses
    _, filename = os.path.split(inspect.getsourcefile(type(test_object)))
    module_name, _ = os.path.splitext(filename)
    return '{0}.{1}'.format(module_name, method_name)


class AzureMgmtTestCase(ReplayableTest):
    def __init__(self, *args, **kwargs):
        self.working_folder = os.path.dirname(__file__)

        kwargs.setdefault('config_file',
                          os.path.join(self.working_folder, TEST_SETTING_FILENAME))

        self.qualified_test_name = get_qualified_test_name(self, args[0])
        kwargs.setdefault('recording_name', self.qualified_test_name)

        super(AzureMgmtTestCase, self).__init__(*args, **kwargs)

    def is_playback(self):
        return not self.is_live

    def setUp(self):
        super(AzureMgmtTestCase, self).setUp()

        self.fake_settings = fake_settings
        if self.is_live:
            import mgmt_settings_real as real_settings
            self.settings = real_settings
        else:
            self.settings = self.fake_settings

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
        #self.group_name = self.get_resource_name(
        #    self.qualified_test_name.replace('.', '_')
        #)
        self.region = 'westus'

    def tearDown(self):
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

    def create_random_name(self, name):
        return get_resource_name(name, self.qualified_test_name.encode())

    def get_resource_name(self, name):
        """Alias to create_random_name for back compatibility."""
        return self.create_random_name(name)

    def get_preparer_resource_name(self):
        """Random name generation for use by preparers."""
        return self.get_resource_name(self.qualified_test_name.replace('.', '_'))

    def _scrub(self, val):
        val = super(AzureMgmtTestCase, self)._scrub(val)

        constants_to_scrub = ['SUBSCRIPTION_ID', 'AD_DOMAIN', 'TENANT_ID', 'CLIENT_OID']

        real_to_fake_dict = {getattr(self.settings, key): getattr(self.fake_settings, key) for key in constants_to_scrub if
                             hasattr(self.settings, key) and hasattr(self.fake_settings, key)}
        val = self._scrub_using_dict(val, real_to_fake_dict)
        return val


class AzureMgmtPreparer(AbstractPreparer, SingleValueReplacer):
    @property
    def is_live(self):
        return self.test_class_instance.is_live

    @property
    def moniker(self):
        """Override moniker generation for backwards compatibility.

        azure-devtools preparers, by default, generate "monikers" which replace
        resource names in request URIs by tacking on a resource count to
        name_prefix. By contrast, SDK tests used the fully qualified (module + method)
        test name and the hashing process in get_resource_name.

        This property override implements the SDK test name generation so that
        the URIs don't change and tests don't need to be re-recorded.
        """
        if not self.resource_moniker:
            self.resource_moniker = self.test_class_instance.get_preparer_resource_name()
        return self.resource_moniker

    def create_mgmt_client(self, client_class, **kwargs):
        if self.is_live:
            return client_class(
                credentials=self.test_class_instance.settings.get_credentials(),
                **kwargs
            )
        else:
            # Not sure what to do here
            return None


class ResourceGroupPreparer(AzureMgmtPreparer):
    def __init__(self, name_prefix='sdktest.rg',
                 random_name_length=75,
                 parameter_name='resource_group_name',
                 parameter_name_for_location='location', location='westus',
                 disable_recording=True):
        super(ResourceGroupPreparer, self).__init__(name_prefix, random_name_length,
                                                    disable_recording=disable_recording)
        self.location = location
        self.parameter_name = parameter_name
        self.parameter_name_for_location = parameter_name_for_location

        self.client = None

    def create_resource(self, name, **kwargs):
        self.client = self.create_mgmt_client(ResourceManagementClient)
        if self.is_live:
            self.client.resource_groups.create_or_update(name, {'location': self.location})
        return {
            self.parameter_name: name,
            self.parameter_name_for_location: self.location,
        }

    def remove_resource(self, name, **kwargs):
        if self.is_live:
            try:
                if 'wait_timeout' in kwargs:
                    azure_poller = self.client.resource_groups.delete(name)
                    azure_poller.wait(kwargs.get('wait_timeout'))
                    if azure_poller.done():
                        return
                    raise AzureTestError('Timed out waiting for resource group to be deleted.')
                else:
                    self.client.resource_groups.delete(name, raw=True)
            except CloudError:
                pass
