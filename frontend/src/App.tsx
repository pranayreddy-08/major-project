const modules = [
  "Event ingestion",
  "Threat detection",
  "Attack correlation",
  "Risk assessment",
  "Explainability",
];

function App() {
  return (
    <main className="shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">Foundation environment</p>
        <h1 id="page-title">Explainable Cyber Threat Intelligence</h1>
        <p className="summary">
          The intelligence agents and audited analyst workflow are ready. The full
          dashboard will be connected here in Phase 6.
        </p>
        <div className="status">
          <span className="status-dot" aria-hidden="true" />
          Phase 5 multi-agent workflow complete
        </div>
      </section>

      <section className="modules" aria-label="Planned platform modules">
        {modules.map((module, index) => (
          <article className="module-card" key={module}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <h2>{module}</h2>
            <p>Interface contract reserved</p>
          </article>
        ))}
      </section>
    </main>
  );
}

export default App;
