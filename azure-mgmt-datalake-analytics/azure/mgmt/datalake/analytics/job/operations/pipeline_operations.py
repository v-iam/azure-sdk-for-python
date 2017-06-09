# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.pipeline import ClientRawResponse
from msrestazure.azure_exceptions import CloudError
import uuid

from .. import models


class PipelineOperations(object):
    """PipelineOperations operations.

    :param client: Client for service requests.
    :param config: Configuration of service client.
    :param serializer: An object model serializer.
    :param deserializer: An objec model deserializer.
    :ivar api_version: Client Api Version. Constant value: "2016-11-01".
    """

    def __init__(self, client, config, serializer, deserializer):

        self._client = client
        self._serialize = serializer
        self._deserialize = deserializer
        self.api_version = "2016-11-01"

        self.config = config

    def list(
            self, account_name, start_date_time=None, end_date_time=None, custom_headers=None, raw=False, **operation_config):
        """Lists all pipelines.

        :param account_name: The Azure Data Lake Analytics account to execute
         job operations on.
        :type account_name: str
        :param start_date_time: The start date for when to get the list of
         pipelines. The startDateTime and endDateTime can be no more than 30
         days apart.
        :type start_date_time: datetime
        :param end_date_time: The end date for when to get the list of
         pipelines. The startDateTime and endDateTime can be no more than 30
         days apart.
        :type end_date_time: datetime
        :param dict custom_headers: headers that will be added to the request
        :param bool raw: returns the direct response alongside the
         deserialized response
        :param operation_config: :ref:`Operation configuration
         overrides<msrest:optionsforoperations>`.
        :rtype: :class:`JobPipelineInformationPaged
         <azure.mgmt.datalake.analytics.job.models.JobPipelineInformationPaged>`
        :raises: :class:`CloudError<msrestazure.azure_exceptions.CloudError>`
        """
        def internal_paging(next_link=None, raw=False):

            if not next_link:
                # Construct URL
                url = '/pipelines'
                path_format_arguments = {
                    'accountName': self._serialize.url("account_name", account_name, 'str', skip_quote=True),
                    'adlaJobDnsSuffix': self._serialize.url("self.config.adla_job_dns_suffix", self.config.adla_job_dns_suffix, 'str', skip_quote=True)
                }
                url = self._client.format_url(url, **path_format_arguments)

                # Construct parameters
                query_parameters = {}
                if start_date_time is not None:
                    query_parameters['startDateTime'] = self._serialize.query("start_date_time", start_date_time, 'iso-8601')
                if end_date_time is not None:
                    query_parameters['endDateTime'] = self._serialize.query("end_date_time", end_date_time, 'iso-8601')
                query_parameters['api-version'] = self._serialize.query("self.api_version", self.api_version, 'str')

            else:
                url = next_link
                query_parameters = {}

            # Construct headers
            header_parameters = {}
            header_parameters['Content-Type'] = 'application/json; charset=utf-8'
            if self.config.generate_client_request_id:
                header_parameters['x-ms-client-request-id'] = str(uuid.uuid1())
            if custom_headers:
                header_parameters.update(custom_headers)
            if self.config.accept_language is not None:
                header_parameters['accept-language'] = self._serialize.header("self.config.accept_language", self.config.accept_language, 'str')

            # Construct and send request
            request = self._client.get(url, query_parameters)
            response = self._client.send(
                request, header_parameters, **operation_config)

            if response.status_code not in [200]:
                exp = CloudError(response)
                exp.request_id = response.headers.get('x-ms-request-id')
                raise exp

            return response

        # Deserialize response
        deserialized = models.JobPipelineInformationPaged(internal_paging, self._deserialize.dependencies)

        if raw:
            header_dict = {}
            client_raw_response = models.JobPipelineInformationPaged(internal_paging, self._deserialize.dependencies, header_dict)
            return client_raw_response

        return deserialized

    def get(
            self, account_name, pipeline_identity, start_date_time=None, end_date_time=None, custom_headers=None, raw=False, **operation_config):
        """Gets the Pipeline information for the specified pipeline ID.

        :param account_name: The Azure Data Lake Analytics account to execute
         job operations on.
        :type account_name: str
        :param pipeline_identity: Pipeline ID.
        :type pipeline_identity: str
        :param start_date_time: The start date for when to get the pipeline
         and aggregate its data. The startDateTime and endDateTime can be no
         more than 30 days apart.
        :type start_date_time: datetime
        :param end_date_time: The end date for when to get the pipeline and
         aggregate its data. The startDateTime and endDateTime can be no more
         than 30 days apart.
        :type end_date_time: datetime
        :param dict custom_headers: headers that will be added to the request
        :param bool raw: returns the direct response alongside the
         deserialized response
        :param operation_config: :ref:`Operation configuration
         overrides<msrest:optionsforoperations>`.
        :rtype: :class:`JobPipelineInformation
         <azure.mgmt.datalake.analytics.job.models.JobPipelineInformation>`
        :rtype: :class:`ClientRawResponse<msrest.pipeline.ClientRawResponse>`
         if raw=true
        :raises: :class:`CloudError<msrestazure.azure_exceptions.CloudError>`
        """
        # Construct URL
        url = '/pipelines/{pipelineIdentity}'
        path_format_arguments = {
            'accountName': self._serialize.url("account_name", account_name, 'str', skip_quote=True),
            'adlaJobDnsSuffix': self._serialize.url("self.config.adla_job_dns_suffix", self.config.adla_job_dns_suffix, 'str', skip_quote=True),
            'pipelineIdentity': self._serialize.url("pipeline_identity", pipeline_identity, 'str')
        }
        url = self._client.format_url(url, **path_format_arguments)

        # Construct parameters
        query_parameters = {}
        if start_date_time is not None:
            query_parameters['startDateTime'] = self._serialize.query("start_date_time", start_date_time, 'iso-8601')
        if end_date_time is not None:
            query_parameters['endDateTime'] = self._serialize.query("end_date_time", end_date_time, 'iso-8601')
        query_parameters['api-version'] = self._serialize.query("self.api_version", self.api_version, 'str')

        # Construct headers
        header_parameters = {}
        header_parameters['Content-Type'] = 'application/json; charset=utf-8'
        if self.config.generate_client_request_id:
            header_parameters['x-ms-client-request-id'] = str(uuid.uuid1())
        if custom_headers:
            header_parameters.update(custom_headers)
        if self.config.accept_language is not None:
            header_parameters['accept-language'] = self._serialize.header("self.config.accept_language", self.config.accept_language, 'str')

        # Construct and send request
        request = self._client.get(url, query_parameters)
        response = self._client.send(request, header_parameters, **operation_config)

        if response.status_code not in [200]:
            exp = CloudError(response)
            exp.request_id = response.headers.get('x-ms-request-id')
            raise exp

        deserialized = None

        if response.status_code == 200:
            deserialized = self._deserialize('JobPipelineInformation', response)

        if raw:
            client_raw_response = ClientRawResponse(deserialized, response)
            return client_raw_response

        return deserialized
