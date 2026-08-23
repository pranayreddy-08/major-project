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
          The development stack is ready. Detection and analyst workflows will be
          connected here in later phases.
        </p>
        <div className="status">
          <span className="status-dot" aria-hidden="true" />
          Phase 3 data pipeline complete
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
