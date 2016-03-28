# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft and contributors.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class ExpressRouteCircuitSku(Model):
    """
    Contains sku in an ExpressRouteCircuit

    :param name: Gets or sets name of the sku.
    :type name: str
    :param tier: Gets or sets tier of the sku. Possible values include:
     'Standard', 'Premium'
    :type tier: str
    :param family: Gets or sets family of the sku. Possible values include:
     'UnlimitedData', 'MeteredData'
    :type family: str
    """ 

    _attribute_map = {
        'name': {'key': 'name', 'type': 'str'},
        'tier': {'key': 'tier', 'type': 'ExpressRouteCircuitSkuTier'},
        'family': {'key': 'family', 'type': 'ExpressRouteCircuitSkuFamily'},
    }

    def __init__(self, name=None, tier=None, family=None, **kwargs):
        self.name = name
        self.tier = tier
        self.family = family