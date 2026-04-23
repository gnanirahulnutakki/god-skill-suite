---
name: god-ml-data-training
description: "God-level ML data preparation and model training skill. Covers data labeling (Label Studio, Scale AI, Prodigy), dataset curation (quality > quantity, curriculum learning), training loop design (PyTorch training loop, gradient accumulation, mixed precision, gradient clipping), loss functions (cross-entropy, focal loss, contrastive loss, triplet loss — when each applies), optimizers (SGD, Adam, AdamW, Lion, LAMB — differences and when to use), learning rate scheduling (warmup, cosine decay, one-cycle), regularization (L1/L2, dropout, weight decay, early stopping), distributed training (DDP, FSDP, DeepSpeed ZeRO stages), and the truth that training a model without understanding your data and loss landscape is driving with your eyes closed."
metadata:
  version: "1.0.0"
---

# God-Level ML Data Preparation and Model Training

## Researcher-Warrior Mindset

You are not a button-pusher who calls `model.fit()` and prays. You are a researcher-warrior who understands every tensor, every gradient, every loss curve. You read the data before you train the model. You instrument every experiment. You know why a loss curve is misbehaving before you touch a hyperparameter. You distrust magic and trust mechanism.

**Anti-hallucination rules:**
- Never invent API signatures. When unsure, say "verify in current PyTorch docs."
- Never claim a model achieves specific benchmark numbers without citing source and date.
- Never recommend a specific learning rate as universal — always frame as "starting point, tune on your data."
- State explicitly when advice is version-specific (e.g., "PyTorch 2.x behavior").
- If asked about a specific model architecture you don't have details on, say so — do not fabricate layer counts or parameter sizes.

---

## Part 1: Data Labeling — The Foundation You Always Underinvest In

### The Uncomfortable Truth
Seventy percent of ML project failures trace back to data, not model architecture. A ResNet-50 trained on clean, well-labeled data beats a transformer trained on garbage. The researcher-warrior labels data with the same rigor applied to writing loss functions.

### Label Studio (Open Source, Self-Hostable)
Label Studio is the Swiss Army knife of annotation. It handles image classification, object detection, NER, relation extraction, audio transcription, time series, and video — all in one tool.

**Key capabilities:**
- Self-hostable via Docker or pip: `pip install label-studio && label-studio`
- Multi-task projects: combine bounding boxes + classification + transcription in a single task
- ML backend integration: connect your model to Label Studio for pre-annotation (model predicts, human corrects — active learning loop)
- S3/GCS/Azure blob storage integration for large-scale datasets
- Webhook support for pipeline automation
- IAA (Inter-Annotator Agreement) metrics built in

**When to use Label Studio:** Any team wanting full data control, no vendor lock-in, cost-sensitive projects, or multi-task annotation workflows.

### Prodigy (Explosion AI — Active Learning Native)
Prodigy is the annotation tool built by the spaCy team. It is opinionated, fast, and built around active learning from day one.

**Core philosophy:** Show annotators the examples the model is most uncertain about. Stop when the model has learned what it needs. Don't label 10,000 random examples when 500 strategically chosen ones teach the same lesson.

**Key capabilities:**
- Active learning recipes: `prodigy ner.teach` starts with uncertainty sampling immediately
- Custom recipes: Python functions that define what to show and how to store
- CLI-first: `prodigy textcat.teach dataset model data.jsonl`
- Binary annotation: fast yes/no for high-volume labeling
- Review workflow: reconcile disagreements across annotators

**When to use Prodigy:** Teams using spaCy, annotation budgets are tight, active learning is a priority, NLP-heavy tasks.

### Scale AI and Labelbox (Enterprise)
**Scale AI:** Managed human labeling workforce, quality auditing, ML-assisted labeling. Best for when you need thousands of labeled examples fast and have budget. Strong in autonomous driving, medical imaging, RLHF data. Quality SLAs exist but must be negotiated. Verify labels — even Scale AI has error rates.

**Labelbox:** Annotation platform + labeling workforce marketplace. Strong workflow management, model-assisted labeling, ontology management. Better for teams who want to manage their own annotators within a structured platform.

**When to use enterprise tools:** >10,000 examples, multiple annotation teams, complex quality workflows, regulated industries.

### Inter-Annotator Agreement (IAA) — Cohen's Kappa
IAA measures how consistently different annotators label the same data. It is the ground truth about whether your annotation guidelines are clear.

**Cohen's Kappa formula:**
```
κ = (P_o - P_e) / (1 - P_e)
```
Where P_o = observed agreement, P_e = expected agreement by chance.

**Interpretation:**
- κ < 0.40: Poor agreement — your guidelines are ambiguous. Stop and fix them.
- κ 0.40–0.60: Moderate — acceptable only for exploratory work
- κ 0.60–0.80: Substantial — good for most production use cases
- κ > 0.80: Near-perfect — what you want for high-stakes annotation

**Practical rule:** Calculate IAA on 10% of your dataset labeled by ≥2 annotators. If κ < 0.70, do not train. Fix the guidelines, retrain annotators, re-label.

**For multi-class:** Use weighted Kappa or Fleiss' Kappa (>2 annotators).

### Annotation Guidelines Quality
The annotation guideline is a product, not an afterthought. Bad guidelines produce bad labels at scale. A good guideline:
- Defines every label with examples AND counter-examples
- Includes edge cases explicitly ("if the entity spans a comma, include the comma")
- Has a decision tree for ambiguous cases
- Is versioned (v1.2 guidelines, not "the doc I sent last week")
- Is tested: give it to a new annotator, measure IAA before full-scale labeling

### Active Learning Loop
1. Label a seed set (200–1000 examples) randomly
2. Train a model on the seed set
3. Run the model on unlabeled data — collect uncertainty scores (entropy, margin sampling, or query-by-committee)
4. Send the most uncertain examples to annotators
5. Retrain — repeat until validation metric plateaus

Active learning reduces labeling cost by 30–80% compared to random sampling for the same model quality. The researcher-warrior never labels randomly when active learning is available.

---

## Part 2: Dataset Quality Principles

### Quality > Quantity — Always
1,000 clean, diverse, correctly labeled examples beat 10,000 noisy ones for virtually every task. Noisy labels corrupt gradient signals. The model learns the noise distribution, not the true distribution.

**Quantifying this:** The "memorization capacity" of a neural network means it will fit noise given enough capacity and epochs. Noisy labels increase the number of epochs needed to overfit, making early stopping less reliable.

### Class Balance
Imbalanced classes cause biased models that predict the majority class. Mitigation strategies:
- **Oversampling minority class:** RandomOverSampler, SMOTE (for tabular), data augmentation (for images/text)
- **Undersampling majority class:** Random undersampling, Tomek links
- **Class weights in loss:** `nn.CrossEntropyLoss(weight=class_weights)` — downweights majority class loss
- **Focal loss:** Automatically down-weights well-classified examples (see Loss Functions section)
- **Stratified splits:** Always use stratified train/val/test splits — `sklearn.model_selection.StratifiedKFold`

### Diversity
A model trained on data from one source generalizes poorly to others. Measure diversity:
- Domain distribution (sources, time periods, geographic regions)
- Length distribution for text, size distribution for images
- Rare but important examples (long-tail coverage)

### Data Lineage
Track where every example came from: source, collection date, annotation version, annotator ID. This enables:
- Debugging: "why does performance drop on these examples?" → trace to source
- Compliance: audit trails for regulated data
- Reproducibility: reproduce any training run exactly

Use tools: DVC (Data Version Control), MLflow with artifact logging, or simple manifests committed to git.

### Curriculum Learning
Train on easy examples first, progressively harder ones later — mimics human learning. Curriculum learning can improve convergence speed and final accuracy, especially for complex tasks.

**Self-paced learning variant:** Let the model determine what is "hard" (high loss examples) and schedule exposure automatically.

---

## Part 3: PyTorch Training Loop Anatomy

### The Complete Training Loop
```python
model = MyModel().to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs)
scaler = torch.cuda.amp.GradScaler()  # for mixed precision

for epoch in range(num_epochs):
    # --- Training phase ---
    model.train()  # enables dropout, batch norm in train mode
    for batch_idx, (inputs, targets) in enumerate(train_loader):
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()  # clear gradients — do NOT accumulate across unrelated batches

        with torch.cuda.amp.autocast():  # mixed precision context
            outputs = model(inputs)
            loss = criterion(outputs, targets)

        scaler.scale(loss).backward()  # scaled backward pass
        scaler.unscale_(optimizer)     # unscale before clipping
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)  # gradient clipping
        scaler.step(optimizer)         # optimizer step
        scaler.update()                # update scale factor

    scheduler.step()  # AFTER optimizer step, AFTER epoch (or after batch depending on scheduler)

    # --- Validation phase ---
    model.eval()  # disables dropout, uses running stats for batch norm
    with torch.no_grad():  # disable gradient computation — saves memory and compute
        for inputs, targets in val_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            val_loss = criterion(outputs, targets)
```

**Order matters — always:**
1. `model.train()` before training loop
2. `optimizer.zero_grad()` before forward pass
3. Forward pass
4. Loss computation
5. `loss.backward()`
6. `clip_grad_norm_()` (before optimizer step, after unscaling)
7. `optimizer.step()`
8. `scheduler.step()` (after optimizer, timing depends on scheduler)
9. `model.eval()` + `torch.no_grad()` for validation

**Common bug:** Calling `scheduler.step()` before `optimizer.step()` — this is wrong. The scheduler reads the current step count; calling it before the optimizer step skews the schedule.

### Gradient Accumulation
Gradient accumulation simulates a larger batch size when GPU VRAM is insufficient.

```python
accumulation_steps = 4  # effective batch = per_device_batch * accumulation_steps * n_gpus

for step, (inputs, targets) in enumerate(train_loader):
    with torch.cuda.amp.autocast():
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss = loss / accumulation_steps  # normalize loss

    scaler.scale(loss).backward()  # accumulate gradients

    if (step + 1) % accumulation_steps == 0:
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad()
        scheduler.step()
```

**Critical:** Divide loss by `accumulation_steps` — otherwise the effective loss is accumulation_steps× larger than intended. **Effective batch size = per_device_batch × accumulation_steps × GPU count.** Learning rate should scale with effective batch (linear scaling rule: lr_new = lr_base × batch_multiplier, though this is approximate and must be validated).

---

## Part 4: Mixed Precision Training

### FP16 vs BF16 — Know the Difference
**FP16 (half precision):**
- 1 sign bit, 5 exponent bits, 10 mantissa bits
- Dynamic range: ~6×10⁻⁸ to ~65504
- Problem: small gradients can underflow to zero → requires loss scaling
- Requires `GradScaler` to prevent gradient underflow

**BF16 (Brain Float 16):**
- 1 sign bit, 8 exponent bits, 7 mantissa bits
- Same dynamic range as FP32 — no underflow risk → **no GradScaler needed**
- Less precision than FP16 but stable for training
- Available on A100, H100, TPUs — preferred when available

**Mixed precision strategy:**
- FP16/BF16 for forward pass and backward pass (fast matrix multiplications)
- FP32 for optimizer state and parameter updates (precision required for convergence)
- `autocast()` automatically selects FP16/BF16 for appropriate operations

```python
# BF16 training (A100/H100 — no scaler needed)
with torch.cuda.amp.autocast(dtype=torch.bfloat16):
    outputs = model(inputs)
    loss = criterion(outputs, targets)
loss.backward()
optimizer.step()
```

**Loss scaling (FP16 only):** GradScaler starts with a large scale factor (e.g., 2¹⁶), halves it when inf/NaN is detected in gradients, doubles it every 2000 successful steps. This keeps gradients in FP16 representable range.

---

## Part 5: Loss Functions — Choose With Intent

### Classification
**Cross-entropy loss:** Standard for multi-class classification. `nn.CrossEntropyLoss()` expects raw logits (not softmax). Combines log-softmax + NLL for numerical stability.

**Binary cross-entropy:** Multi-label classification (each class is independent sigmoid). `nn.BCEWithLogitsLoss()` — prefer over `BCELoss(sigmoid(logits))` for numerical stability.

### Regression
**MSE (Mean Squared Error):** Penalizes large errors heavily. Sensitive to outliers. Use when large errors are truly catastrophic.

**MAE (Mean Absolute Error):** Robust to outliers. Not differentiable at 0 (use smoothed version). Use when outliers exist in targets and shouldn't dominate.

**Huber loss:** Combines MSE (for small errors) and MAE (for large errors). `nn.HuberLoss(delta=1.0)` — delta controls the transition point. Best of both worlds for regression with outliers.

### Imbalanced Classes
**Focal loss:** Down-weights easy examples, focuses training on hard misclassified examples.
```
FL(p_t) = -α_t × (1 - p_t)^γ × log(p_t)
```
- γ=2 is the standard choice (from RetinaNet paper)
- α_t balances class frequency
- When p_t is high (easy example), (1-p_t)^γ ≈ 0 — loss contribution is near zero
- When p_t is low (hard example), focal weight ≈ 1 — full loss contribution

Use focal loss for: object detection, medical imaging (rare pathologies), any heavily imbalanced dataset.

### Similarity / Metric Learning
**Contrastive loss:** Pairs of (similar, dissimilar). Pulls similar pairs together, pushes dissimilar pairs apart.
```
L = y × d² + (1-y) × max(0, margin - d)²
```
Where y=1 for similar pairs, y=0 for dissimilar pairs, d = euclidean distance.

**Triplet loss:** Anchor, positive (same class), negative (different class). Ensures d(anchor, positive) + margin < d(anchor, negative).
```
L = max(0, d(a,p) - d(a,n) + margin)
```
**Hard negative mining** is critical — random negatives are often too easy. Use online hard negative mining: within each batch, find the hardest negatives.

**InfoNCE (used in CLIP, SimCLR):** Contrastive loss for self-supervised learning. Maximizes mutual information between positive pairs. Works in large batch settings — more negatives in batch = better contrastive signal.

---

## Part 6: Optimizers — Know What You're Using

### SGD with Momentum
```python
optimizer = torch.optim.SGD(model.parameters(), lr=0.01, momentum=0.9, weight_decay=5e-4)
```
Still state-of-the-art for image classification (ResNet, EfficientNet benchmarks use SGD + cosine). Requires careful LR tuning — more sensitive than adaptive methods. Momentum accumulates gradient history to smooth updates.

### Adam — Good Default, Has a Bug
```python
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
```
The weight_decay in Adam is **coupled** — it is applied to the gradient-adapted update, not directly to the parameters. This means weight decay effectiveness varies with gradient magnitude. Use AdamW instead.

### AdamW — Adam Done Right
```python
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
```
Decoupled weight decay — applied directly to parameters, not to adapted gradients. This is what you want for transformers and most modern architectures. Default for HuggingFace training.

### AdaFactor — Memory Efficient
Factorizes second moment (v) matrix — stores row and column factors instead of full matrix. Massive memory savings for large embedding layers. Used to train T5. Does not store momentum by default. Can be unstable — use learning rate scheduler and warm-up.

### Lion — Simple and Competitive
Published by Google Brain (2023). Uses only the sign of the update — no adaptive second moment. Lower memory than Adam (no v). Competitive with AdamW on many benchmarks. Smaller learning rate needed (typically 3-10× lower than AdamW).

### LAMB — Large Batch Training
Layer-wise Adaptive Moments for Batch training. Scales gradient by layer norm — enables stable training with very large batch sizes (up to 32K for BERT pretraining). Use specifically when batch size is very large (>4K) and other optimizers produce instability.

---

## Part 7: Learning Rate Scheduling

### Warmup
Warmup gradually increases LR from 0 (or small value) to target LR over the first N steps. Prevents early instability when model parameters are random and gradients are large.

**Rule of thumb:** Warm up for 5–10% of total training steps, or 1 full epoch.

```python
from transformers import get_cosine_schedule_with_warmup
scheduler = get_cosine_schedule_with_warmup(
    optimizer,
    num_warmup_steps=500,
    num_training_steps=10000
)
```

### Cosine Annealing
LR follows a cosine curve from target LR to near-zero. Smooth decay, allows late-training refinement with low LR. Standard for transformer training.

### One-Cycle Policy (Leslie Smith)
LR increases from low to high (super-convergence phase) then decreases. Combined with momentum oscillation (high momentum at low LR, low momentum at high LR). Often achieves good accuracy in fewer epochs.

### Learning Rate Finder (Range Test)
Run training for 1 epoch, exponentially increase LR from 1e-7 to 1. Plot loss vs LR. Choose LR at the point of steepest descent (not the minimum — that's past the optimal). Libraries: `pytorch-lightning` has a built-in LR finder.

### Interaction with Gradient Accumulation
When using gradient accumulation, the scheduler should step every optimizer step (i.e., every N gradient accumulation steps), not every mini-batch. Otherwise the LR schedule completes N× faster than intended.

---

## Part 8: Regularization

### L1 and L2
**L2 (weight decay):** Penalizes large weights, encourages small weights, keeps model simple. Implemented as `weight_decay` in optimizer. Produces diffuse small weights.

**L1 (lasso):** Penalizes absolute weight value, encourages sparsity (exact zeros). Less common in deep learning (not easily differentiable at 0). Use for feature selection scenarios.

### Dropout
```python
self.dropout = nn.Dropout(p=0.1)
```
During training: randomly zeroes p fraction of activations. During eval (`model.eval()`): dropout is a no-op — all activations pass through. The researcher-warrior always verifies `model.eval()` is called before inference.

**Dropout rates:**
- 0.1–0.2: Light regularization for large models
- 0.3–0.5: Standard for fully connected layers
- Too high dropout: underfitting, slow convergence

### Batch Normalization vs Layer Normalization
**BatchNorm:** Normalizes across batch dimension. Requires batch size > 1 during training. Works well for CNNs. Poor for RNNs, transformers.

**LayerNorm:** Normalizes across feature dimension within each example. Works for any batch size (including batch=1). Standard for transformers.

### Early Stopping
Monitor validation metric (loss, accuracy, F1) with patience N. Stop training if metric does not improve for N consecutive evaluations.

```python
# Implementation logic
best_val_loss = float('inf')
patience_counter = 0

if val_loss < best_val_loss:
    best_val_loss = val_loss
    torch.save(model.state_dict(), 'best_model.pt')
    patience_counter = 0
else:
    patience_counter += 1
    if patience_counter >= patience:
        print("Early stopping triggered")
        break
```

**Always save the best checkpoint**, not the last one. Model quality at final epoch ≠ best model.

---

## Part 9: Distributed Training

### DDP (DistributedDataParallel) — Most Common
Each GPU holds a full copy of the model. Forward pass on each GPU independently. Backward pass: AllReduce operation synchronizes gradients across all GPUs. Each GPU applies the same gradient update.

```python
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP

dist.init_process_group(backend='nccl')
model = DDP(model.to(local_rank), device_ids=[local_rank])
```

**Use DDP when:** Model fits on a single GPU. Scales linearly with GPU count.

**DistributedSampler** is required — ensures each GPU sees different data:
```python
sampler = torch.utils.data.distributed.DistributedSampler(dataset)
loader = DataLoader(dataset, sampler=sampler)
```

### FSDP (Fully Sharded Data Parallel) — Large Models
Shards model parameters, optimizer states, and gradients across GPUs. Each GPU only holds 1/N of the parameters at rest. Parameters are gathered before each layer's forward/backward computation (all-gather), then resharded after.

```python
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp import ShardingStrategy

model = FSDP(model, sharding_strategy=ShardingStrategy.FULL_SHARD)
```

**Use FSDP when:** Model does not fit on a single GPU. 7B+ parameter models typically require FSDP or DeepSpeed.

### DeepSpeed ZeRO Stages
ZeRO (Zero Redundancy Optimizer) shards optimizer state, gradients, and parameters progressively.

**ZeRO Stage 1:** Shards optimizer states across GPUs. ~4× memory reduction for optimizer state. Fastest of the three stages.

**ZeRO Stage 2:** Stage 1 + shards gradients. ~8× memory reduction. Most commonly used.

**ZeRO Stage 3:** Stage 2 + shards parameters. Maximum memory reduction — enables training models much larger than single GPU VRAM. Communication overhead is highest.

**ZeRO-Infinity:** Offloads to CPU RAM and NVMe SSD. Enables training 100B+ parameter models on commodity hardware.

```python
# ds_config.json
{
  "zero_optimization": {
    "stage": 2,
    "allgather_partitions": true,
    "reduce_scatter": true
  }
}
```

**Practical rule:** Start with DDP. Move to FSDP or DeepSpeed ZeRO Stage 2 when model doesn't fit on one GPU. Use ZeRO Stage 3 only when Stage 2 is insufficient.

---

## Part 10: Debugging Training

### Loss Not Decreasing
Systematic diagnosis:
1. **Learning rate too low:** Loss decreases extremely slowly. Try 10× higher LR.
2. **Learning rate too high:** Loss oscillates or diverges. Try 10× lower LR.
3. **Data pipeline bug:** `model.eval()` accidentally called during training, labels misaligned with inputs, DataLoader returns corrupted batches. Print 5 examples from DataLoader.
4. **Gradient flow problem:** Use `torch.autograd.set_detect_anomaly(True)` temporarily. Check `param.grad` for None in parameters that should be training.
5. **Loss is wrong:** Verify your criterion is correct for the task. Print loss before any training — does it match theoretical initial loss? For K-class cross-entropy: initial loss ≈ log(K).

### Loss NaN
Causes and fixes:
1. **Gradient explosion:** Add `clip_grad_norm_`. Check if loss is already NaN on step 1 — if so, data issue.
2. **Numerical instability:** Log of zero, division by zero, sqrt of negative. Check data for extreme values.
3. **FP16 overflow:** Without GradScaler, FP16 can overflow. Add GradScaler or switch to BF16.
4. **Bad data:** NaN or inf in input tensors. Add assertion: `assert not torch.isnan(inputs).any()`.

### Overfitting
Signs: training loss decreases, validation loss increases or plateaus.
1. Add dropout
2. Increase weight decay
3. Reduce model capacity
4. Add data augmentation
5. Get more training data
6. Use early stopping
7. Label smoothing: `nn.CrossEntropyLoss(label_smoothing=0.1)`

### Underfitting
Signs: both training and validation loss are high.
1. Increase model capacity (more layers, wider layers)
2. Train longer
3. Reduce regularization (lower dropout, lower weight decay)
4. Tune learning rate (try higher)
5. Verify data quality — may be label noise causing ceiling on learnable signal

---

## Part 11: GPU Memory Management

### Techniques
**Gradient checkpointing:** Recomputes activations during backward pass instead of storing them. Reduces activation memory by ~sqrt(layers) at cost of ~30-40% more compute. Essential for long sequences or deep models.

```python
from torch.utils.checkpoint import checkpoint_sequential
model = checkpoint_sequential(model, segments=4)
```

**Explicit tensor deletion:**
```python
del tensor_variable  # remove Python reference
torch.cuda.empty_cache()  # return memory to CUDA allocator (not to OS — useful for profiling)
```

**Batch size tuning:** Start with a small batch size, double until OOM, then back off by 10%.

**torch.cuda.memory_summary():** Print detailed GPU memory allocation. Use during debugging.

**activation memory vs parameter memory:** For large batch training, activation memory often exceeds parameter memory. Gradient checkpointing directly targets activations.

---

## Part 12: Cross-Domain Connections

### ML Training ↔ Kubernetes GPU Scheduling
DDP and FSDP training jobs require GPU-aware scheduling. Kubernetes GPU scheduling uses `nvidia.com/gpu: 1` resource requests. For multi-node training, use `MPI Operator` or `PyTorch Job` (Kubeflow) controllers. GPU topology matters — NVLINK-connected GPUs communicate faster than PCIe. Node affinity rules ensure DDP processes land on NVLINK-connected nodes.

### Data Pipelines ↔ Training
Training is only as fast as data loading. `torch.utils.data.DataLoader` with `num_workers > 0` enables parallel data loading. `pin_memory=True` enables faster CPU→GPU transfer. For large datasets: FFCV, DALI (GPU-accelerated data loading), or WebDataset (streaming from object storage). Data pipeline bottlenecks are identified when GPU utilization oscillates (loading) vs sustained (compute-bound).

### MLflow ↔ Training Experiments
```python
import mlflow

mlflow.start_run()
mlflow.log_params({"lr": 1e-4, "batch_size": 32})
mlflow.log_metric("train_loss", loss.item(), step=global_step)
mlflow.pytorch.log_model(model, "model")
```
Log every hyperparameter. Log validation metrics every epoch. Log learning rate at every step. Use MLflow Model Registry to version production models. Never run an experiment without tracking — you will regret it.

---

## Self-Review Checklist (20 Items)

Before delivering any ML training advice or code, verify:

1. [ ] Is `model.train()` called before training and `model.eval()` before validation?
2. [ ] Is `optimizer.zero_grad()` called at the correct point (before forward pass, or after optimizer.step() for gradient accumulation)?
3. [ ] Is `torch.no_grad()` context used in validation loop?
4. [ ] Is `scheduler.step()` called after `optimizer.step()` (not before)?
5. [ ] Is gradient clipping applied after loss scaling is removed (GradScaler.unscale_)?
6. [ ] Is loss divided by `accumulation_steps` when using gradient accumulation?
7. [ ] Is BF16 preferred over FP16 on A100/H100 (no GradScaler needed)?
8. [ ] Is AdamW recommended over Adam for transformer training?
9. [ ] Is inter-annotator agreement > 0.8 (κ) for production annotation?
10. [ ] Is class imbalance addressed (class weights, focal loss, or oversampling)?
11. [ ] Is a validation set reserved and never trained on?
12. [ ] Are best checkpoints saved (not just final epoch)?
13. [ ] Is data lineage tracked (source, annotation version, annotator)?
14. [ ] Is the initial loss theoretically reasonable (e.g., log(num_classes) for cross-entropy)?
15. [ ] Is DistributedSampler used with DDP training?
16. [ ] Is gradient checkpointing considered when activation memory is the bottleneck?
17. [ ] Is `torch.autograd.set_detect_anomaly(True)` used only for debugging (not production — major overhead)?
18. [ ] Is the loss function appropriate for the task (not defaulting to cross-entropy for regression)?
19. [ ] Is learning rate warmup included for transformer training?
20. [ ] Are all experiments logged in MLflow or equivalent before the run starts?

---

## Reference: Loss Function Selection Table

| Task | Loss Function | PyTorch Class |
|------|--------------|---------------|
| Multi-class classification | Cross-entropy | `nn.CrossEntropyLoss()` |
| Binary classification | Binary cross-entropy | `nn.BCEWithLogitsLoss()` |
| Multi-label classification | Binary cross-entropy | `nn.BCEWithLogitsLoss()` |
| Regression (sensitive to outliers) | MSE | `nn.MSELoss()` |
| Regression (robust) | MAE | `nn.L1Loss()` |
| Regression (balanced) | Huber | `nn.HuberLoss()` |
| Imbalanced classification | Focal loss | custom or `torchvision.ops.sigmoid_focal_loss` |
| Similarity learning (pairs) | Contrastive | `nn.CosineEmbeddingLoss()` or custom |
| Metric learning (triplets) | Triplet | `nn.TripletMarginLoss()` |
| Self-supervised / CLIP-style | InfoNCE | custom implementation |

---

## Reference: Optimizer Selection Guide

| Scenario | Optimizer | Key Settings |
|----------|-----------|--------------|
| Vision (CNNs) | SGD + momentum | lr=0.01, momentum=0.9, weight_decay=1e-4 |
| Transformers (default) | AdamW | lr=1e-4, weight_decay=0.01 |
| Memory constrained | AdaFactor | relative_step=True for adaptive lr |
| Lower memory than AdamW | Lion | lr ~3-10× lower than AdamW equivalent |
| Very large batches (>4K) | LAMB | Requires specific implementation |
| Quick experiments | Adam | lr=1e-3, but switch to AdamW for final runs |
