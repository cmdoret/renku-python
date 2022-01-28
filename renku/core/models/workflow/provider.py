# -*- coding: utf-8 -*-
#
# Copyright 2017-2021 - Swiss Data Science Center (SDSC)
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
"""Workflow executor provider."""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Tuple

if TYPE_CHECKING:
    import networkx as nx


class IWorkflowProvider(metaclass=ABCMeta):
    """Abstract class for executing ``Plan``."""

    @abstractmethod
    def workflow_provider(self) -> Tuple[IWorkflowProvider, str]:
        """Supported workflow description formats.

        :returns: a tuple of ``self`` and format.
        """
        pass

    @abstractmethod
    def workflow_execute(self, dag: "nx.DiGraph", basedir: Path, config: Dict[str, Any]):
        """Executes a given ``AbstractPlan`` using the provider.

        :returns: a list of output paths that were generated by this workflow.
        """
        pass