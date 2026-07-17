---
name: Keras 2 model on modern TensorFlow
description: How to load older Keras 2 models with TensorFlow 2.16+ and Python 3.12.
---

# Keras 2 model on modern TensorFlow

A model saved with Keras 2.8.0 (e.g. `model_mb.json` + `model_mb.h5`) fails to load with TensorFlow 2.21 / Keras 3.15 with:

```
TypeError: Could not locate class 'Functional'. Make sure custom classes and functions are decorated with `@keras.saving.register_keras_serializable()`.
```

## Solution

Use the `tf_keras` compatibility package, which provides the Keras 2 API on top of modern TensorFlow.

```python
import tf_keras as keras
from tf_keras import layers
from tf_keras.models import model_from_json

model = model_from_json(open('model.json').read())
model.load_weights('model.h5')
```

## Why

TensorFlow 2.16+ ships with Keras 3 by default. The serialization format for Keras 3 uses different class names. `tf_keras` is maintained by the TensorFlow team as a Keras 2 compatibility layer and does not require downgrading Python or TensorFlow.

## How to apply

When loading any Keras 2-era model in this project, import from `tf_keras`, not `keras` or `tensorflow.keras`.
