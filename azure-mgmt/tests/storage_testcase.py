import os

from azure.mgmt.storage import StorageManagementClient

from azure_devtools.scenario_tests.preparers import (
    AbstractPreparer,
    SingleValueReplacer,
)
from azure_devtools.scenario_tests.exceptions import AzureTestError
from .mgmt_testcase import AzureMgmtPreparer, ResourceGroupPreparer


# Storage Account Preparer and its shorthand decorator

class StorageAccountPreparer(AzureMgmtPreparer):
    def __init__(self,
                 name_prefix='sdktest', sku='Standard_LRS', location='westus',
                 parameter_name='storage_account_name',
                 resource_group_parameter_name='resource_group',
                 client_parameter_name='storage_client',
                 skip_delete=True):
        super(StorageAccountPreparer, self).__init__(name_prefix, 24)
        self.location = location
        self.sku = sku
        self.resource_group_parameter_name = resource_group_parameter_name
        self.skip_delete = skip_delete
        self.parameter_name = parameter_name

        self.client = self.create_mgmt_client(StorageManagementClient)

    def create_resource(self, name, **kwargs):
        group = self._get_resource_group(**kwargs)

        storage_async_operation = self.client.storage_accounts.create(
            group,
            name,
            {
                'sku': self.sku,
                'location': self.location,
            }
        )
        storage_async_operation.wait()

        return {
            self.parameter_name: name,
            self.client_parameter_name: self.client,
        }

    def remove_resource(self, name, **kwargs):
        if not self.skip_delete and not self.dev_setting_name:
            group = self._get_resource_group(**kwargs)
            self.client.storage_accounts.delete(group, name)

    def _get_resource_group(self, **kwargs):
        try:
            return kwargs.get(self.resource_group_parameter_name)
        except KeyError:
            template = 'To create a storage account a resource group is required. Please add ' \
                       'decorator @{} in front of this storage account preparer.'
            raise AzureTestError(template.format(ResourceGroupPreparer.__name__))

