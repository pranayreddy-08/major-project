import cytoscape, { type Core, type StylesheetJson } from "cytoscape";
import { useEffect, useRef, useState } from "react";

import type { AttackGraph, GraphNode } from "./types";

const graphStyles: StylesheetJson = [
  {
    selector: "node",
    style: {
      "background-color": "#17263b",
      "border-color": "#54d6c2",
      "border-width": 2,
      color: "#e7f3f7",
      label: "data(label)",
      "font-size": 11,
      "text-valign": "bottom",
      "text-margin-y": 8,
      width: "mapData(risk, 0, 100, 34, 58)",
      height: "mapData(risk, 0, 100, 34, 58)",
    },
  },
  {
    selector: 'node[type = "user"]',
    style: { shape: "round-rectangle", "border-color": "#8b9bff" },
  },
  {
    selector: 'node[type = "host"]',
    style: { shape: "hexagon", "border-color": "#f4bf65" },
  },
  {
    selector: "edge",
    style: {
      width: 1.5,
      "line-color": "#40536a",
      "target-arrow-color": "#54d6c2",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      label: "data(label)",
      color: "#8298aa",
      "font-size": 8,
      "text-background-color": "#0b1422",
      "text-background-opacity": 0.9,
      "text-background-padding": "3px",
    },
  },
  {
    selector: ":selected",
    style: { "border-color": "#ff6b79", "border-width": 4 },
  },
];

export default function AttackGraphView({ graph }: { graph: AttackGraph | null }) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<Core | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);

  useEffect(() => {
    if (!container.current || !graph) return;
    instance.current?.destroy();
    const nodeLookup = new Map(graph.nodes.map((node) => [node.id, node]));
    const cy = cytoscape({
      container: container.current,
      elements: [
        ...graph.nodes.map((node) => ({
          data: {
            id: node.id,
            label: node.label,
            type: node.entity_type,
            risk: node.risk_score,
          },
        })),
        ...graph.edges.map((edge) => ({
          data: {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: edge.relationship.replaceAll("_", " "),
          },
        })),
      ],
      style: graphStyles,
      layout: { name: "cose", animate: false, padding: 48 },
      minZoom: 0.55,
      maxZoom: 2.2,
    });
    cy.on("tap", "node", (event) => {
      setSelected(nodeLookup.get(event.target.id()) ?? null);
    });
    instance.current = cy;
    return () => {
      cy.destroy();
      instance.current = null;
    };
  }, [graph]);

  if (!graph) return <div className="empty-state">Select an incident to load its graph.</div>;
  if (!graph.nodes.length) return <div className="empty-state">This incident has no graph evidence.</div>;

  return (
    <div className="graph-shell">
      <div className="graph-canvas" ref={container} aria-label="Interactive attack graph" />
      <aside className="graph-inspector">
        <p className="section-kicker">Selected entity</p>
        {selected ? (
          <>
            <h3>{selected.label}</h3>
            <dl>
              <div><dt>Type</dt><dd>{selected.entity_type}</dd></div>
              <div><dt>Risk</dt><dd>{selected.risk_score.toFixed(1)}</dd></div>
              <div><dt>Evidence</dt><dd>Deterministic event links</dd></div>
            </dl>
          </>
        ) : (
          <p>Click a node to inspect its entity type and risk score.</p>
        )}
        <p className="limitation">Graph relationships support investigation; they do not prove causality.</p>
      </aside>
    </div>
  );
}
