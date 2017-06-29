from collections import namedtuple

from azure.mgmt.media import MediaServicesManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.sql import SqlManagementClient

from devtools_testutils import (
    AzureMgmtTestCase, ResourceGroupPreparer, StorageAccountPreparer, FakeResource
)


FAKE_STORAGE_ID = 'STORAGE-FAKE-ID'
FAKE_STORAGE = FakeResource(name='teststorage', id=FAKE_STORAGE_ID)


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
        self.client.resource_groups.delete(group.name)


class ExampleSqlServerTestCase(AzureMgmtTestCase):
    def setUp(self):
        super(ExampleSqlServerTestCase, self).setUp()
        self.client = self.create_mgmt_client(SqlManagementClient)

    @ResourceGroupPreparer(location='westus2')
    def test_create_sql_server(self, resource_group, location):
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


class ExampleMediaServiceTestCase(AzureMgmtTestCase):
    def setUp(self):
        super(ExampleMediaServiceTestCase, self).setUp()
        self.client = self.create_mgmt_client(MediaServicesManagementClient)

    @ResourceGroupPreparer(parameter_name='group',
                           location='westus')
    @StorageAccountPreparer(playback_fake_resource=FAKE_STORAGE,
                            name_prefix='testmedia',
                            resource_group_parameter_name='group')
    def test_create_media_service(self, group, location, storage_account, storage_account_key):
        test_media_name = self.get_resource_name('pymediatest')
        media_obj = self.client.media_service.create(
            group.name,
            test_media_name,
            {
                'location': location,
                'storage_accounts': [{
                    'id': storage_account.id,
                    'is_primary': True,
                }]
            }
        )
        self.assertEqual(media_obj.name, test_media_name)
        self.client.media_service.delete(group.name, test_media_name)
