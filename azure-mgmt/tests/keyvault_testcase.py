#-------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#--------------------------------------------------------------------------
import json
import os.path
import re
import time
from uuid import uuid4

import azure.mgmt.resource
from azure.mgmt.keyvault import KeyVaultManagementClient
from azure.mgmt.keyvault.models import \
    (VaultCreateOrUpdateParameters, VaultProperties, Sku, AccessPolicyEntry, Permissions, KeyPermissions, SecretPermissions, SkuName,
     CertificatePermissions, StoragePermissions)
from azure.keyvault import KeyVaultClient, KeyVaultAuthentication, KeyVaultAuthBase, HttpBearerChallenge

from azure.common.exceptions import (
    CloudError
)
from tests.mgmt_testcase import HttpStatusCode, AzureMgmtTestCase
from testutils.common_recordingtestcase import (
    RecordingTestCase,
    TestMode,
)

from azure.common.client_factory import get_client_from_cli_profile
from azure_devtools.scenario_tests.preparers import (
    AbstractPreparer,
    SingleValueReplacer,
)
from azure_devtools.scenario_tests.exceptions import AzureTestError

import tests.mgmt_settings_fake as fake_settings

should_log = os.getenv('SDK_TESTS_LOG', '0')
if should_log.lower() == 'true' or should_log == '1':
    import logging
    logger = logging.getLogger('msrest')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


def privatevault(permissions=None, enabled_for_deployment=True, enabled_for_disk_encryption=True,
             enabled_for_template_deployment=True, enable_soft_delete=None):
    def testvault_decorator(f):
        def wrapper(self):
            with self.recording():
                vault = self.setup_private_vault(permissions=permissions,
                                                 enabled_for_deployment=enabled_for_deployment,
                                                 enabled_for_disk_encryption=enabled_for_disk_encryption,
                                                 enabled_for_template_deployment=enabled_for_template_deployment,
                                                 enable_soft_delete=enable_soft_delete)
                try:
                    f(self, vault=vault)
                finally:
                    self.cleanup_private_vault(vault)
        wrapper.__name__ = f.__name__
        testvault_decorator.__name__ = f.__name__
        return wrapper
    return testvault_decorator

def sharedvault(f):
    def wrapper(self):
        with self.recording():
            vault = self.setup_shared_vault()
            f(self, vault=vault)
    wrapper.__name__ = f.__name__
    return wrapper

class AzureKeyVaultTestCase(AzureMgmtTestCase):

    shared_vault = None
    default_group = 'azkv-pytest'
    default_vault = 'pytest-shared-vault'
    default_permissions = Permissions(keys=[
                                          KeyPermissions.encrypt,
                                          KeyPermissions.decrypt,
                                          KeyPermissions.wrap_key,
                                          KeyPermissions.unwrap_key,
                                          KeyPermissions.sign,
                                          KeyPermissions.verify,
                                          KeyPermissions.get,
                                          KeyPermissions.list,
                                          KeyPermissions.create,
                                          KeyPermissions.update,
                                          KeyPermissions.import_enum,
                                          KeyPermissions.delete,
                                          KeyPermissions.backup,
                                          KeyPermissions.restore,
                                          KeyPermissions.recover,
                                          KeyPermissions.purge],
                                      secrets=[
                                          SecretPermissions.get,
                                          SecretPermissions.list,
                                          SecretPermissions.set,
                                          SecretPermissions.delete,
                                          SecretPermissions.backup,
                                          SecretPermissions.restore,
                                          SecretPermissions.recover,
                                          SecretPermissions.purge],
                                      certificates=[
                                          CertificatePermissions.get,
                                          CertificatePermissions.list,
                                          CertificatePermissions.delete,
                                          CertificatePermissions.create,
                                          CertificatePermissions.import_enum,
                                          CertificatePermissions.update,
                                          CertificatePermissions.managecontacts,
                                          CertificatePermissions.getissuers,
                                          CertificatePermissions.listissuers,
                                          CertificatePermissions.setissuers,
                                          CertificatePermissions.deleteissuers,
                                          CertificatePermissions.manageissuers,
                                          CertificatePermissions.recover,
                                          CertificatePermissions.purge],
                                      storage=[
                                          StoragePermissions.get,
                                          StoragePermissions.list,
                                          StoragePermissions.delete,
                                          StoragePermissions.set,
                                          StoragePermissions.update,
                                          StoragePermissions.regeneratekey,
                                          StoragePermissions.setsas,
                                          StoragePermissions.listsas,
                                          StoragePermissions.getsas,
                                          StoragePermissions.deletesas])

    def setUp(self):
        self.working_folder = os.path.dirname(__file__)

        super(AzureKeyVaultTestCase, self).setUp()

        def mock_key_vault_auth_base(self, request):
            challenge = HttpBearerChallenge(request.url, 'Bearer authorization=fake-url,resource=https://vault.azure.net')
            self.set_authorization_header(request, challenge)
            return request

        self.fake_settings = fake_settings
        if TestMode.is_playback(self.test_mode):
            self.settings = self.fake_settings
            KeyVaultAuthBase.__call__ = mock_key_vault_auth_base
        else:
            import tests.mgmt_settings_real as real_settings
            self.settings = real_settings

        self.client = self.create_keyvault_client()
        self.mgmt_client = self.create_mgmt_client(azure.mgmt.keyvault.KeyVaultManagementClient)

        if not self.is_playback():
            self.create_resource_group()


    def tearDown(self):
        return super(AzureKeyVaultTestCase, self).tearDown()

    def create_keyvault_client(self):

        def _auth_callback(server, resource, scope):
            if TestMode.is_playback(self.test_mode):
                return ('Bearer', 'fake-token')
            credentials = self.settings.get_credentials()
            credentials.resource = resource
            credentials.set_token()
            return credentials.scheme, credentials.__dict__['token']['access_token']
        return KeyVaultClient(KeyVaultAuthentication(_auth_callback))

    def _ensure_resource_group(self, group_name):
        return self.resource_client.resource_groups.create_or_update(
            group_name,
            {
                'location': self.region
            }
        )

    def setup_shared_vault(self):
        if not self.is_playback():
            self._ensure_resource_group(self.default_group)
        if not AzureKeyVaultTestCase.shared_vault:
            AzureKeyVaultTestCase.shared_vault = self.create_vault(self.default_group, self.default_vault)
        return AzureKeyVaultTestCase.shared_vault;

    def setup_private_vault(self, permissions=None, enabled_for_deployment=True, enabled_for_disk_encryption=True,
                         enabled_for_template_deployment=True, enable_soft_delete=None, sku=None):
        vault_name = self.get_resource_name('vault-')
        vault = self.create_vault(self.group_name, vault_name,
                                  permissions=permissions,enabled_for_deployment=enabled_for_deployment,
                                  enabled_for_template_deployment=enabled_for_template_deployment, enable_soft_delete=enable_soft_delete,
                                  sku=sku)

        return vault

    def create_vault(self, group_name, vault_name, permissions=None, enabled_for_deployment=True, enabled_for_disk_encryption=True,
                         enabled_for_template_deployment=True, enable_soft_delete=None, sku=None):
        creds = self.settings.get_credentials()
        access_policies = [AccessPolicyEntry(tenant_id=self.settings.TENANT_ID,
                                             object_id=self.settings.CLIENT_OID,
                                             permissions=permissions or self.default_permissions)]
        properties = VaultProperties(tenant_id=self.settings.TENANT_ID,
                                     sku=Sku(sku or SkuName.premium.value),
                                     access_policies=access_policies,
                                     vault_uri=None,
                                     enabled_for_deployment=enabled_for_deployment,
                                     enabled_for_disk_encryption=enabled_for_disk_encryption,
                                     enabled_for_template_deployment=enabled_for_template_deployment,
                                     enable_soft_delete=enable_soft_delete)
        parameters = VaultCreateOrUpdateParameters(location='westus',
                                                   properties=properties)

        vault = self.mgmt_client.vaults.create_or_update(group_name, vault_name, parameters)

        if not self.is_playback():
            self.sleep(10)

        return vault

    def cleanup_private_vault(self, vault):
        # we only need to cleanup if the vault has soft delete enabled otherwise base teardown will
        # delete when the resource group is deleted
        if not self.is_playback() and vault.properties.enable_soft_delete:
            self.mgmt_client.vaults.delete(self.group_name, vault.name)
            self.sleep(10)
            self.mgmt_client.vaults.purge_deleted(vault.name, vault.location)

    def _scrub_sensitive_request_info(self, request):
        request = super(AzureKeyVaultTestCase, self)._scrub_sensitive_request_info(request)
        # prevents URI mismatch between Python 2 and 3 if request URI has extra / chars
        request.uri = re.sub('//', '/', request.uri)
        request.uri = re.sub('/', '//', request.uri, count=1)
        # do not record token requests
        if '/oauth2/token' in request.uri:
            request = None
        return request

    def _scrub_sensitive_response_info(self, response):
        from pprint import pprint
        response = super(AzureKeyVaultTestCase, self)._scrub_sensitive_response_info(response)
        # ignore any 401 responses during playback
        if response['status']['code'] == 401:
            response = None
        return response

    def _scrub(self, val):
        val = super(AzureKeyVaultTestCase, self)._scrub(val)
        real_to_fake_dict = {
            self.settings.SUBSCRIPTION_ID: self.fake_settings.SUBSCRIPTION_ID,
            self.settings.AD_DOMAIN:  self.fake_settings.AD_DOMAIN
        }
        val = self._scrub_using_dict(val, real_to_fake_dict)
        return val


# KeyVault Preparer and its shorthand decorator

class KeyVaultPreparer(AbstractPreparer, SingleValueReplacer):
    def __init__(self,  # pylint: disable=too-many-arguments
                 name_prefix='clitest', sku='standard', location='westus',
                 parameter_name='key_vault', resource_group_parameter_name='resource_group',
                 skip_delete=True, dev_setting_name='AZURE_CLI_TEST_DEV_KEY_VAULT_NAME'):
        super(KeyVaultPreparer, self).__init__(name_prefix, 24)
        self.location = location
        self.sku = sku
        self.resource_group_parameter_name = resource_group_parameter_name
        self.skip_delete = skip_delete
        self.parameter_name = parameter_name

        self.dev_setting_name = os.environ.get(dev_setting_name, None)

        self.client = get_client_from_cli_profile(KeyVaultManagementClient)

    def create_resource(self, name, **kwargs):
        if not self.dev_setting_name:
            self.client.vaults.create_or_update(
                self._get_resource_group(**kwargs),
                name,
                {
                    'location': self.location,
                    'properties': {
                        'sku': self.sku,
                    },
                    # Fake random GUID
                    'tenant_id': uuid4(),
                    'access_policies': []
                }
            )
            return {self.parameter_name: name}
        else:
            return {self.parameter_name: self.dev_setting_name}

    def remove_resource(self, name, **kwargs):
        if not self.skip_delete and not self.dev_setting_name:
            group = self._get_resource_group(**kwargs)
            # execute('az keyvault delete -n {} -g {} --yes'.format(name, group))

    def _get_resource_group(self, **kwargs):
        try:
            return kwargs.get(self.resource_group_parameter_name)
        except KeyError:
            template = 'To create a KeyVault a resource group is required. Please add ' \
                       'decorator @{} in front of this KeyVault preparer.'
            raise AzureTestError(template.format(KeyVaultPreparer.__name__))
