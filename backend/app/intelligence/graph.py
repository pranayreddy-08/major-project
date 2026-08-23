from app.intelligence.common import event_id, stable_id
from app.schemas.events import NormalizedEventCreate
from app.schemas.intelligence import (
    AttackGraph,
    AttackGraphEdge,
    AttackGraphNode,
    EvidencePath,
)


def _node(entity_type: str, key: str) -> AttackGraphNode:
    return AttackGraphNode(
        id=stable_id("node", f"{entity_type}:{key}"),
        entity_type=entity_type,
        key=key,
        label=key,
    )


def build_attack_graph(events: list[NormalizedEventCreate]) -> AttackGraph:
    nodes: dict[str, AttackGraphNode] = {}
    edges: dict[str, AttackGraphEdge] = {}

    for event in sorted(events, key=lambda item: (item.timestamp, event_id(item))):
        identifier = event_id(event)
        entities: dict[str, AttackGraphNode] = {}
        values = {
            "source_ip": str(event.source_ip) if event.source_ip else None,
            "destination_ip": str(event.destination_ip) if event.destination_ip else None,
            "user": event.user.strip().lower() if event.user else None,
            "host": event.host.strip().lower() if event.host else None,
        }
        for role, value in values.items():
            if value is None:
                continue
            entity_type = "ip" if role.endswith("_ip") else role
            graph_node = _node(entity_type, value)
            nodes[graph_node.id] = graph_node
            entities[role] = graph_node

        relationships = (
            ("source_ip", "destination_ip", "network_connection"),
            ("user", "host", "user_activity"),
            ("source_ip", "host", "source_observed_on_host"),
        )
        for source_role, target_role, relationship in relationships:
            if source_role not in entities or target_role not in entities:
                continue
            source = entities[source_role].id
            target = entities[target_role].id
            edge_id = stable_id("edge", f"{source}|{target}|{relationship}|{identifier}")
            edges[edge_id] = AttackGraphEdge(
                id=edge_id,
                source=source,
                target=target,
                relationship=relationship,
                event_id=identifier,
                timestamp=event.timestamp,
            )

    return AttackGraph(
        nodes=sorted(nodes.values(), key=lambda node: (node.entity_type, node.key, node.id)),
        edges=sorted(edges.values(), key=lambda edge: (edge.timestamp, edge.id)),
    )


def explain_graph_node(graph: AttackGraph, node_id: str, *, limit: int = 5) -> EvidencePath:
    node = next((candidate for candidate in graph.nodes if candidate.id == node_id), None)
    if node is None:
        raise ValueError(f"unknown graph node: {node_id}")
    connected = [
        edge for edge in graph.edges if edge.source == node_id or edge.target == node_id
    ][:limit]
    return EvidencePath(
        node_id=node_id,
        summary=f"{node.label} is supported by {len(connected)} connected event relationship(s).",
        supporting_edge_ids=[edge.id for edge in connected],
        supporting_event_ids=sorted({edge.event_id for edge in connected}),
        limitations=(
            "This evidence path shows deterministic event relationships; it does not prove "
            "causality or malicious intent."
        ),
    )
