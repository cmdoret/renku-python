# -*- coding: utf-8 -*-
#
# Copyright 2017-2022 - Swiss Data Science Center (SDSC)
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
"""Renku activity database gateway implementation."""

from itertools import chain
from pathlib import Path
from typing import List, Optional, Set, Tuple, Union

from persistent.list import PersistentList

from renku.command.command_builder.command import inject
from renku.core.interface.activity_gateway import IActivityGateway
from renku.core.interface.database_dispatcher import IDatabaseDispatcher
from renku.core.interface.plan_gateway import IPlanGateway
from renku.core.util.os import are_paths_related
from renku.core.workflow.activity import create_activity_graph
from renku.domain_model.provenance.activity import Activity, ActivityCollection
from renku.domain_model.workflow.plan import Plan
from renku.infrastructure.gateway.database_gateway import ActivityDownstreamRelation


class ActivityGateway(IActivityGateway):
    """Gateway for activity database operations."""

    database_dispatcher = inject.attr(IDatabaseDispatcher)

    def get_all_usage_paths(self) -> List[str]:
        """Return all usage paths."""
        database = self.database_dispatcher.current_database

        return list(database["activities-by-usage"].keys())

    def get_all_generation_paths(self) -> List[str]:
        """Return all generation paths."""
        database = self.database_dispatcher.current_database

        return list(database["activities-by-generation"].keys())

    def get_activities_by_generation(self, path: Union[Path, str], checksum: Optional[str] = None) -> List[Activity]:
        """Return the list of all activities that generate a path."""
        by_generation = self.database_dispatcher.current_database["activities-by-generation"]
        activities = by_generation.get(str(path), [])

        if not checksum:
            return activities

        result = []

        for activity in activities:
            generation = next((g for g in activity.generations if g.entity.checksum == checksum), None)

            if generation:
                result.append(activity)

        return result

    def get_downstream_activities(self, activity: Activity, max_depth=None) -> Set[Activity]:
        """Get downstream activities that depend on this activity."""
        # NOTE: since indices are populated one way when adding an activity, we need to query two indices
        database = self.database_dispatcher.current_database

        activity_catalog = database["activity-catalog"]
        tok = activity_catalog.tokenizeQuery
        downstream = set(activity_catalog.findValues("downstream", tok(upstream=activity), maxDepth=max_depth))

        return downstream

    def get_downstream_activity_chains(self, activity: Activity) -> List[Tuple[Activity, ...]]:
        """Get a list of tuples of all downstream paths of this activity."""
        database = self.database_dispatcher.current_database

        activity_catalog = database["activity-catalog"]
        tok = activity_catalog.tokenizeQuery
        downstream_chains = activity_catalog.findRelationChains(tok(upstream=activity))
        downstream_chains = [tuple(r.downstream for r in c) for c in downstream_chains]

        return downstream_chains

    def get_upstream_activity_chains(self, activity: Activity) -> List[Tuple[Activity, ...]]:
        """Get a list of tuples of all upstream paths of this activity."""
        database = self.database_dispatcher.current_database

        activity_catalog = database["activity-catalog"]
        tok = activity_catalog.tokenizeQuery
        upstream_chains = activity_catalog.findRelationChains(tok(downstream=activity))
        upstream_chains = [tuple(r.upstream for r in c) for c in upstream_chains]

        return upstream_chains

    def get_all_activities(self) -> List[Activity]:
        """Get all activities in the project."""
        return list(self.database_dispatcher.current_database["activities"].values())

    def add(self, activity: Activity):
        """Add an ``Activity`` to storage."""

        database = self.database_dispatcher.current_database

        database["activities"].add(activity)

        upstreams = set()
        downstreams = set()

        by_usage = database["activities-by-usage"]
        by_generation = database["activities-by-generation"]

        for usage in activity.usages:
            if usage.entity.path not in by_usage:
                by_usage[usage.entity.path] = PersistentList()
            by_usage[usage.entity.path].append(activity)

            for path, activities in by_generation.items():
                if are_paths_related(path, usage.entity.path):
                    upstreams.update(activities)

        for generation in activity.generations:
            if generation.entity.path not in by_generation:
                by_generation[generation.entity.path] = PersistentList()
            by_generation[generation.entity.path].append(activity)

            for path, activities in by_usage.items():
                if are_paths_related(path, generation.entity.path):
                    downstreams.update(activities)

        if upstreams:
            for s in upstreams:
                database["activity-catalog"].index(ActivityDownstreamRelation(downstream=activity, upstream=s))

        if downstreams:
            for s in downstreams:
                database["activity-catalog"].index(ActivityDownstreamRelation(downstream=s, upstream=activity))

        assert isinstance(activity.association.plan, Plan)

        plan_gateway = inject.instance(IPlanGateway)
        plan_gateway.add(activity.association.plan)

        # NOTE: Check for a cycle if this activity
        upstream_chains = self.get_upstream_activity_chains(activity)
        downstream_chains = self.get_downstream_activity_chains(activity)

        all_activities = set()

        for activity_chain in chain(upstream_chains, downstream_chains):
            for current_activity in activity_chain:
                all_activities.add(current_activity)

        # NOTE: This call raises an exception if there is a cycle
        create_activity_graph(list(all_activities), with_inputs_outputs=True)

    def add_activity_collection(self, activity_collection: ActivityCollection):
        """Add an ``ActivityCollection`` to storage."""
        database = self.database_dispatcher.current_database

        database["activity-collections"].add(activity_collection)

    def get_all_activity_collections(self) -> List[ActivityCollection]:
        """Get all activity collections in the project."""
        return list(self.database_dispatcher.current_database["activity-collections"].values())
