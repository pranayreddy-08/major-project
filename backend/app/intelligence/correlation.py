from collections import defaultdict
from datetime import timedelta

from app.intelligence.common import event_entities, event_id, stable_id
from app.schemas.events import NormalizedEventCreate
from app.schemas.intelligence import CorrelatedIncident, CorrelationLink


class _DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[max(left_root, right_root)] = min(left_root, right_root)


def correlate_events(
    events: list[NormalizedEventCreate], *, window: timedelta = timedelta(minutes=15)
) -> list[CorrelatedIncident]:
    ordered = sorted(events, key=lambda item: (item.timestamp, event_id(item)))
    identifiers = [event_id(event) for event in ordered]
    disjoint = _DisjointSet(len(ordered))
    recent_by_entity: dict[tuple[str, str], list[int]] = defaultdict(list)
    links: list[CorrelationLink] = []

    for current_index, current in enumerate(ordered):
        for entity_type, entity_value in event_entities(current):
            prior_indexes = recent_by_entity[(entity_type, entity_value)]
            cutoff = current.timestamp - window
            prior_indexes[:] = [
                index for index in prior_indexes if ordered[index].timestamp >= cutoff
            ]
            for prior_index in prior_indexes:
                prior = ordered[prior_index]
                disjoint.union(prior_index, current_index)
                links.append(
                    CorrelationLink(
                        source_event_id=identifiers[prior_index],
                        target_event_id=identifiers[current_index],
                        relationship=f"shared_{entity_type}",
                        entity=entity_value,
                        time_delta_seconds=(current.timestamp - prior.timestamp).total_seconds(),
                    )
                )
            prior_indexes.append(current_index)

    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(ordered)):
        groups[disjoint.find(index)].append(index)

    incidents: list[CorrelatedIncident] = []
    for indexes in groups.values():
        if len(indexes) < 2:
            continue
        member_ids = [identifiers[index] for index in indexes]
        member_set = set(member_ids)
        member_links = [
            link
            for link in links
            if link.source_event_id in member_set and link.target_event_id in member_set
        ]
        incidents.append(
            CorrelatedIncident(
                id=stable_id("inc", "|".join(sorted(member_ids))),
                event_ids=member_ids,
                started_at=ordered[indexes[0]].timestamp,
                ended_at=ordered[indexes[-1]].timestamp,
                links=member_links,
            )
        )
    return sorted(incidents, key=lambda incident: (incident.started_at, incident.id))
