from collections import namedtuple

from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.sql import SqlManagementClient

from devtools_testutils import (
    AzureMgmtTestCase, ResourceGroupPreparer, StorageAccountPreparer
)


FakeStorageAccount = namedtuple(
    'FakeStorageAccount',
    ['name', 'kind']
)
FAKE_STORAGE = FakeStorageAccount(name='teststorage', kind='BlobStorage')


class ExampleResourceGroupTestCase(AzureMgmtTestCase):
    def setUp(self):
        super(ExampleResourceGroupTestCase, self).setUp()
        self.client = self.create_mgmt_client(ResourceManagementClient)

    def test_create_resource_group(self):
        test_group_name = self.get_resource_name('testgroup')
        group = self.client.resource_groups.create_or_update(
            test_group_name,
            {'location': 'westus'}
        )
        self.assertEqual(group.name, test_group_name)
        result_delete = self.client.resource_groups.delete(group.name)
        result_delete.wait()


class ExampleSqlServerTestCase(AzureMgmtTestCase):
    def setUp(self):
        super(ExampleSqlServerTestCase, self).setUp()
        self.client = self.create_mgmt_client(SqlManagementClient)

    @ResourceGroupPreparer()
    def test_get_resource_groups(self, resource_group, location):
        test_server_name = self.get_resource_name('testsqlserver')
        server_creation = self.client.servers.create_or_update(
            resource_group.name,
            test_server_name,
            {
                'location': location,
                'version': '12.0',
                'administrator_login': 'mysecretname',
                'administrator_login_password': 'HusH_Sec4et'
            }
        )
        server = server_creation.result()
        self.assertEqual(server.name, test_server_name)
        self.client.servers.delete(resource_group.name, server.name)


class ExampleGetStorageTestCase(AzureMgmtTestCase):
    def setUp(self):
        super(ExampleGetStorageTestCase, self).setUp()
        self.client = self.create_mgmt_client(StorageManagementClient)

    @ResourceGroupPreparer(parameter_name='group')
    @StorageAccountPreparer(playback_fake_resource=FAKE_STORAGE,
                            name_prefix='teststorageprops',
                            resource_group_parameter_name='group',
                            kind='BlobStorage')
    def test_get_storage_properties(self, group, storage_account, storage_account_key):
        props = self.client.storage_accounts.get_properties(group.name, storage_account.name)
        self.assertEqual(storage_account.kind, 'BlobStorage')
