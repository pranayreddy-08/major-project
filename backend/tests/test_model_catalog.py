from app.api.v1.platform import model_catalog


def test_model_catalog_distinguishes_runtime_and_evaluated_models() -> None:
    catalog = model_catalog()
    models = {model.id: model for model in catalog.models}

    assert models["severity-anomaly-baseline"].deployment == "runtime"
    assert models["severity-anomaly-baseline"].metrics is None
    assert models["graphsage"].kind == "graph_neural_network"
    assert models["graphsage"].deployment == "evaluated_offline"
    assert models["graphsage"].metrics is not None
    assert models["graphsage"].metrics.f1 == 0.8
    assert any("not the detector" in limitation for limitation in catalog.limitations)


def test_model_catalog_metrics_remain_bounded() -> None:
    for model in model_catalog().models:
        if model.metrics is None:
            continue
        assert 0 <= model.metrics.precision <= 1
        assert 0 <= model.metrics.recall <= 1
        assert 0 <= model.metrics.f1 <= 1
        assert 0 <= model.metrics.roc_auc <= 1
        assert model.metrics.samples == 18
