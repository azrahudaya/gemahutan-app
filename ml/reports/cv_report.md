# Cross-Validation Report (5-fold stratified)

- Pool: 924 samples, 26 classes
- Config: epochs=200 hidden=256 lr=0.001 dropout=0.3 wd=0.0001 seed=42
- LR schedule: ReduceLROnPlateau(factor=0.5,patience=15,min=1e-5)
- Class weight: balanced via sklearn

## Headline metrics (mean +/- std)

- Best val acc: 0.7405 +/- 0.0399
- Test acc:    0.6970 +/- 0.0116
- F1 macro:    0.6819 +/- 0.0130

## Per-fold

| Fold | Train | Val | Test | best_val_acc | test_acc | F1 macro | Epochs |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 665 | 74 | 185 | 0.6892 | 0.6973 | 0.6906 | 32 |
| 2 | 665 | 74 | 185 | 0.7568 | 0.6811 | 0.6646 | 33 |
| 3 | 665 | 74 | 185 | 0.7297 | 0.6919 | 0.6809 | 33 |
| 4 | 665 | 74 | 185 | 0.7297 | 0.7027 | 0.6756 | 32 |
| 5 | 666 | 74 | 184 | 0.7973 | 0.7120 | 0.6981 | 32 |

## Per-class accuracy (mean +/- std across folds)

| Species | mean | std | folds_with_class |
|---|---:|---:|---:|
| Spilopelia chinensis | 0.9429 | 0.1278 | 5 |
| Merops philippinus | 0.9333 | 0.0913 | 5 |
| Corvus macrorhynchos | 0.9000 | 0.0913 | 5 |
| Lonchura punctulata | 0.8667 | 0.0745 | 5 |
| Arachnothera longirostra | 0.8600 | 0.2191 | 5 |
| Rhipidura javanica | 0.8533 | 0.1643 | 5 |
| Haliastur indus | 0.8333 | 0.2041 | 5 |
| Passer montanus | 0.8139 | 0.1788 | 5 |
| Chalcophaps indica | 0.8100 | 0.1084 | 5 |
| Todiramphus chloris | 0.8000 | 0.1629 | 5 |
| Centropus bengalensis | 0.7857 | 0.1808 | 5 |
| Cisticola juncidis | 0.7778 | 0.0621 | 5 |
| Geopelia striata | 0.7714 | 0.2167 | 5 |
| Amaurornis phoenicurus | 0.6964 | 0.2059 | 5 |
| Dicrurus macrocercus | 0.6900 | 0.1342 | 5 |
| Pycnonotus goiavier | 0.6750 | 0.3601 | 5 |
| Anthreptes malacensis | 0.6429 | 0.1582 | 5 |
| Aegithina tiphia | 0.6429 | 0.1429 | 5 |
| Cinnyris jugularis | 0.6306 | 0.1700 | 5 |
| Pycnonotus aurigaster | 0.6278 | 0.0908 | 5 |
| Gallus gallus | 0.6000 | 0.4183 | 5 |
| Orthotomus sutorius | 0.6000 | 0.2733 | 5 |
| Aplonis panayensis | 0.5667 | 0.1966 | 5 |
| Hirundo tahitica | 0.4900 | 0.3248 | 5 |
| Prinia familiaris | 0.4667 | 0.0745 | 5 |
| _negative | 0.4255 | 0.0668 | 5 |
