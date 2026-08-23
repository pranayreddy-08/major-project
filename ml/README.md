# Machine learning

This package owns leakage-safe data preparation. It chronologically splits cleaned records before
fitting median imputation, constant categorical imputation, one-hot encoding, or standard scaling.
Only the training partition fits those transformations; validation and test partitions are transform
only. Phase 4 will add baseline and graph models.

Install and test it from the repository root:

```powershell
python -m pip install -e ".\ml[dev]"
pytest ml\tests
python -m ecti_ml.cli data\samples\synthetic-events-v1.csv `
  --config ml\configs\preprocessing-v1.json
```

Never use the test partition for tuning, feature selection, threshold selection, or early stopping.
Generated models, processed data, and experiment artifacts must not be committed to Git.
