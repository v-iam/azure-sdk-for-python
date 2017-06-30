from azure.mgmt.keyvault import KeyVaultManagementClient
from azure.mgmt.keyvault.models import (
    VaultCreateOrUpdateParameters, VaultProperties, Sku, AccessPolicyEntry, Permissions, KeyPermissions, SecretPermissions, SkuName,
    CertificatePermissions, StoragePermissions
)

from azure_devtools.scenario_tests import AzureTestError

from . import AzureMgmtPreparer


class KeyVaultPreparer(AzureMgmtPreparer):
    def __init__(self, name_prefix='', sku='standard', location='westus', parameter_name='key_vault',
                 resource_group_parameter_name='resource_group',
                 disable_recording=True, playback_fake_resource=None,
                 skip_delete=True):
        super(KeyVaultPreparer, self).__init__(name_prefix, 24,
                                               disable_recording=True,
                                               playback_fake_resource=playback_fake_resource)
        self.location = location
        self.sku = sku
        self.resource_group_parameter_name = resource_group_parameter_name
        self.skip_delete = skip_delete
        self.parameter_name = parameter_name

    def create_resource(self, name, **kwargs):
        if self.is_live:
            self.client = self.create_mgmt_client(KeyVaultManagementClient)

            access_policies = [AccessPolicyEntry(
                tenant_id=self.test_class_instance.settings.TENANT_ID,
                object_id=self.test_class_instance.settings.CLIENT_OID,
                permissions={'keys': ['all'], 'secrets': ['all']}
            )]
            properties = VaultProperties(
                tenant_id=self.test_class_instance.settings.TENANT_ID,
                sku=Sku(self.sku or SkuName.premium.value),
                access_policies=access_policies,
                vault_uri=None,
                enabled_for_deployment=True,
                enabled_for_disk_encryption=True,
                enabled_for_template_deployment=True,
                enable_soft_delete=None,
            )
            parameters = VaultCreateOrUpdateParameters(
                location='westus',
                properties=properties
            )

            group = self._get_resource_group(**kwargs)

            self.resource = self.client.vaults.create_or_update(
                group.name, name, parameters
            )

        return {self.parameter_name: self.resource}

    def remove_resource(self, name, **kwargs):
        if self.is_live:
            group = self._get_resource_group(**kwargs)
            self.client.vaults.delete(group.name, name)

    def _get_resource_group(self, **kwargs):
        try:
            return kwargs.get(self.resource_group_parameter_name)
        except KeyError:
            template = 'To create a KeyVault a resource group is required. Please add ' \
                       'decorator @{} in front of this KeyVault preparer.'
            raise AzureTestError(template.format(KeyVaultPreparer.__name__))
