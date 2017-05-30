import os

from azure.common.client_factory import get_client_from_cli_profile
from azure.mgmt.resource import ResourceManagementClient

from azure_devtools.scenario_tests.preparers import (
    AbstractPreparer,
    SingleValueReplacer,
)
from azure_devtools.scenario_tests.exceptions import AzureTestError


# Resource Group Preparer and its shorthand decorator

class ResourceGroupPreparer(AbstractPreparer, SingleValueReplacer):
    def __init__(self, name_prefix='sdktest.rg',
                 parameter_name='resource_group',
                 parameter_name_for_location='resource_group_location', location='westus',
                 dev_setting_name='AZURE_CLI_TEST_DEV_RESOURCE_GROUP_NAME',
                 dev_setting_location='AZURE_CLI_TEST_DEV_RESOURCE_GROUP_LOCATION',
                 random_name_length=75):
        super(ResourceGroupPreparer, self).__init__(name_prefix, random_name_length)
        self.location = location
        self.parameter_name = parameter_name
        self.parameter_name_for_location = parameter_name_for_location

        self.dev_setting_name = os.environ.get(dev_setting_name, None)
        self.dev_setting_location = os.environ.get(dev_setting_location, location)

        # This should work with 'az login'
        self.client = get_client_from_cli_profile(ResourceManagementClient)

    def create_resource(self, name, **kwargs):
        if self.dev_setting_name:
            return {self.parameter_name: self.dev_setting_name,
                    self.parameter_name_for_location: self.dev_setting_location}
        else:
            # template = 'az group create --location {} --name {} --tag use=az-test'
            self.client.resource_groups.create_or_update(
                name,
                {
                    'location': self.location,
                    'tags': {
                        'use': 'az-test',
                    }
                }
            )
            return {self.parameter_name: name, self.parameter_name_for_location: self.location}

    def remove_resource(self, name, **kwargs):
        if not self.dev_setting_name:
            # execute('az group delete --name {} --yes --no-wait'.format(name))
            self.client.resource_groups.delete(name)

