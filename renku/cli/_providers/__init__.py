# -*- coding: utf-8 -*-
#
# Copyright 2019 - Swiss Data Science Center (SDSC)
# A partnership between École Polytechnique Fédérale de Lausanne (EPFL) and
# Eidgenössische Technische Hochschule Zürich (ETHZ).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Third party data registry integration."""
from urllib.parse import urlparse

from renku.cli._providers.dataverse import DataverseProvider
from renku.cli._providers.zenodo import ZenodoProvider
from renku.utils.doi import is_doi


class ProviderFactory:
    """Create a provider type from URI."""

    PROVIDERS = {'dataverse': DataverseProvider, 'zenodo': ZenodoProvider}

    @staticmethod
    def from_uri(uri):
        """Get provider type based on uri."""
        is_doi_ = is_doi(uri)
        if is_doi_ is None:
            url = urlparse(uri)
            if bool(url.scheme and url.netloc and url.params == '') is False:
                return None, 'Cannot parse URL.'

        provider = None
        err = ''

        for _, potential_provider in ProviderFactory.PROVIDERS.items():
            try:
                if potential_provider.supports(uri):
                    provider = potential_provider
                    break
            except (Exception, BaseException) as e:
                err += 'Couldn\'t test provider {prov}: {err}\n'.format(
                    prov=potential_provider, err=e
                )

        supported_providers = ', '.join(ProviderFactory.PROVIDERS.keys())

        if is_doi_ and provider is None:
            return None, (
                err + 'Provider {} not found. '.format(
                    uri.split('/')[1].split('.')[0]  # Get DOI provider name.
                ) + 'Currently supporting following providers: {}'.
                format(supported_providers)
            )
        elif provider is None:
            return None, (
                err + 'Provider not found for {}. '.format(uri) +
                'Currently supporting following providers: {}'.
                format(supported_providers)
            )
        else:
            return provider(is_doi=is_doi_), err

    @staticmethod
    def from_id(provider_id):
        """Get provider type based on identifier."""
        return ProviderFactory.PROVIDERS[provider_id]()