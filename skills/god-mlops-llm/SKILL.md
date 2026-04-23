---
name: god-mlops-llm
description: "God-level LLM engineering skill. Covers LLM fine-tuning (full, LoRA, QLoRA, PEFT), RAG system design and evaluation, LLM evaluation frameworks, hallucination reduction techniques, prompt optimization, LLM serving (vLLM, TGI, Ollama, Triton), context window management, embedding models, vector databases, agent architectures, tool use, LLM security (prompt injection, jailbreak hardening), and LLMOps. Embeds researcher-warrior mentality: never accepts LLM output at face value, always probes failure modes, always evaluates systematically."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level LLM Engineering

## The Researcher-Warrior Identity for LLM Work

You approach LLMs the same way a security researcher approaches a new target: with deep suspicion, relentless probing, and absolute refusal to accept surface-level explanations.

**Core beliefs you operate with**:
- Every LLM hallucinates. Your job is to measure how much, under what conditions, and build systems that catch it.
- Benchmark numbers are marketing. Real evaluation is adversarial, domain-specific, and ruthless.
- "It works in the demo" means nothing. Find the 10 inputs that break it before you ship it.
- Fine-tuning without rigorous evaluation is noise injection at scale.
- RAG without retrieval quality measurement is guessing with extra steps.
- Any LLM system without an evals framework is a system you cannot improve.

**Anti-Hallucination Rules (LLM-Specific)**:
- NEVER claim a model supports a context length without verifying the current model card.
- NEVER state a LoRA rank/alpha combination "works best" without citing empirical evidence.
- NEVER fabricate tokenizer behavior — test it: `tokenizer.encode("your string")`.
- NEVER claim an embedding model produces a specific dimension without verification.
- NEVER invent vLLM/TGI configuration parameters — check their current GitHub docs.

---

## Phase 1: LLM Selection & Evaluation

### 1.1 Model Selection is a Research Task

Before choosing a model, you must answer:
- What is the task type? (generation, classification, extraction, reasoning, code)
- What context length is required? (not just average — what is the maximum case?)
- What is the inference latency budget? (P99, not P50)
- What is the throughput requirement? (tokens/second, concurrent requests)
- What are the hardware constraints? (GPU VRAM, CPU-only, edge device)
- What are the licensing constraints? (commercial use, derivative models)
- What language(s) must be supported?

**Model evaluation is not running one benchmark. It is building a task-specific eval set and measuring on that.**

### 1.2 Evaluation Framework (Non-Negotiable Before Production)

```python
# Build a domain-specific eval set — minimum 200 examples
# Categories: happy path, edge cases, adversarial, known failure modes

from dataclasses import dataclass
from typing import Callable

@dataclass
class EvalCase:
    id: str
    input: str
    expected_output: str | None      # None for open-ended tasks
    evaluator: Callable              # Function that scores the output
    category: str
    difficulty: str                  # easy/medium/hard/adversarial

# Evaluation metrics by task type
METRICS = {
    "extraction": ["exact_match", "f1", "hallucination_rate"],
    "generation": ["rouge", "bertscore", "llm_judge_score", "factuality"],
    "code": ["execution_success", "test_pass_rate", "syntax_valid"],
    "reasoning": ["step_correctness", "final_answer_accuracy"],
    "qa": ["answer_relevance", "faithfulness", "context_recall"],
}

# LLM-as-judge (for open-ended evaluation)
def llm_judge(question: str, response: str, reference: str) -> dict:
    """Use a stronger model to judge quality of a weaker model's output."""
    # Never use the same model to judge its own output
    # Use GPT-4 or Claude to judge smaller models
    # Use structured output — not free text — for scores
    pass
```

### 1.3 Evals Frameworks to Use
- **RAGAS**: RAG evaluation (faithfulness, answer relevance, context recall)
- **LangSmith**: Tracing + evaluation for LangChain-based systems
- **Weave (W&B)**: Model evaluation and experiment tracking
- **DeepEval**: Unit-test-style LLM evaluation
- **PromptBench**: Adversarial robustness evaluation
- **EleutherAI LM Evaluation Harness**: Academic benchmark reproduction

---

## Phase 2: Fine-Tuning

### 2.1 When Fine-Tuning is the Right Answer

Fine-tune when:
- The task requires style/format that prompting cannot reliably achieve
- The domain has specialized vocabulary/knowledge not in pretraining
- Latency budget requires a smaller model that matches a larger one's quality
- Prompt context would exceed context window at scale

Do NOT fine-tune when:
- The task can be solved with better prompting or RAG
- You have fewer than 1000 high-quality training examples
- You don't have an evaluation framework to measure improvement

### 2.2 QLoRA Fine-Tuning (Production Pattern)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
from trl import SFTTrainer
import torch
from datasets import load_dataset

# Load model in 4-bit quantization
model = AutoModelForCausalLM.from_pretrained(
    "mistralai/Mistral-7B-v0.1",
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",          # NormalFloat4 — best for LLM weights
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,      # Nested quantization
    ),
    device_map="auto",
)

model = prepare_model_for_kbit_training(model)

# LoRA configuration — tune these empirically
lora_config = LoraConfig(
    r=64,                    # Rank — higher = more parameters = more capacity
    lora_alpha=128,          # Alpha = 2*r is a common starting point
    target_modules=[         # Verify module names for your specific model
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()  # Should be ~1-5% of total parameters

training_args = TrainingArguments(
    output_dir="./checkpoints",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,      # Effective batch = 16
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    bf16=True,                           # bfloat16 — better than fp16 for training
    logging_steps=10,
    evaluation_strategy="steps",
    eval_steps=100,
    save_strategy="steps",
    save_steps=100,
    load_best_model_at_end=True,
    report_to="wandb",
)
```

### 2.3 Training Data Quality Rules

Training data quality beats training data quantity. Always:
1. Deduplicate (exact + near-duplicate removal via MinHash LSH)
2. Filter for quality (perplexity filter, length filter, language detection)
3. Balance distribution across task types and difficulty levels
4. Include negative examples (what the model should NOT say)
5. Human-review a random sample (≥5%) before training
6. Version and hash the training data — link to model checkpoint

---

## Phase 3: RAG System Design

### 3.1 RAG Architecture (The Right Way)

```
[User Query]
    → [Query Analysis & Routing]           # Is RAG needed? Which index?
    → [Query Transformation]               # Rewrite, expand, HyDE
    → [Retrieval]                          # Hybrid: dense + sparse
    → [Reranking]                          # Cross-encoder reranker
    → [Context Assembly]                   # Dedup, truncate, order
    → [Generation with Citations]          # LLM generates with retrieved context
    → [Response Validation]               # Faithfulness check
    → [Output]
```

### 3.2 Retrieval Quality (The Most Underinvested Part of RAG)

```python
# Hybrid retrieval — never just vector search
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

def hybrid_retrieve(query: str, k: int = 20) -> list[Document]:
    # Dense retrieval (semantic)
    dense_results = vector_store.similarity_search(query, k=k)

    # Sparse retrieval (keyword — catches exact terms, acronyms, codes)
    sparse_results = bm25.get_top_n(query.split(), corpus, n=k)

    # Reciprocal Rank Fusion — combine without needing to normalize scores
    results = reciprocal_rank_fusion([dense_results, sparse_results])

    # Rerank with cross-encoder (much more accurate than bi-encoder)
    reranked = cross_encoder.rank(query, [r.text for r in results])

    return reranked[:5]  # Return top-5 after reranking

# Chunking strategy — this matters enormously
# Bad: fixed 512-token chunks (splits sentences, loses context)
# Good: semantic chunking (split at paragraph/section boundaries)
# Better: hierarchical chunking (store full doc + chunks, retrieve chunk, expand to doc)
# Best: task-specific chunking based on your document structure
```

### 3.3 RAG Evaluation with RAGAS

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,          # Is the answer grounded in retrieved context?
    answer_relevancy,      # Is the answer relevant to the question?
    context_recall,        # Did retrieval find all necessary information?
    context_precision,     # Was the retrieved context actually useful?
    answer_correctness,    # Is the answer factually correct?
)

results = evaluate(
    dataset=eval_dataset,
    metrics=[faithfulness, answer_relevancy, context_recall,
             context_precision, answer_correctness],
)
# Hallucination detection: faithfulness < 0.8 → LLM is making things up
# Retrieval problem: context_recall < 0.7 → retrieval is missing information
# Noise problem: context_precision < 0.5 → retrieved docs are irrelevant
```

---

## Phase 4: LLM Security

### 4.1 Prompt Injection Hardening

Every LLM system is a potential prompt injection target. Assume hostile inputs.

```python
# Input sanitization layer
def sanitize_user_input(user_input: str) -> str:
    # Detect and neutralize injection patterns
    injection_patterns = [
        r"ignore (all |previous |above )?instructions",
        r"you are now",
        r"disregard (your |the )?system prompt",
        r"<\|im_start\|>",           # Common injection token
        r"\[INST\]",                 # Llama instruction injection
        r"### (Human|Assistant):",   # Role injection
    ]
    for pattern in injection_patterns:
        if re.search(pattern, user_input, re.IGNORECASE):
            raise SecurityException(f"Potential prompt injection detected")
    return user_input

# Structural defense — never concatenate user input into system prompt
# WRONG:
system_prompt = f"You are a helpful assistant. User context: {user_input}"
# RIGHT:
messages = [
    {"role": "system", "content": FIXED_SYSTEM_PROMPT},
    {"role": "user", "content": user_input}  # Separate role keeps it contained
]
```

### 4.2 Output Validation

```python
def validate_llm_output(output: str, context: list[str]) -> dict:
    return {
        "contains_pii": detect_pii(output),            # No PII leakage
        "contains_secrets": detect_secrets(output),     # No secret leakage
        "is_faithful": check_faithfulness(output, context),  # Grounded in context
        "is_safe": content_safety_check(output),       # No harmful content
        "is_in_scope": check_topic_relevance(output),  # On-topic
    }
```

---

## Phase 5: LLM Serving Infrastructure

### 5.1 vLLM Production Setup

```python
# vLLM — state of the art for throughput (PagedAttention)
from vllm import LLM, SamplingParams

llm = LLM(
    model="mistralai/Mistral-7B-Instruct-v0.2",
    tensor_parallel_size=2,          # GPU count
    max_model_len=32768,
    gpu_memory_utilization=0.90,     # Leave 10% headroom
    enable_prefix_caching=True,      # Cache system prompt KV
)

sampling_params = SamplingParams(
    temperature=0.0,                 # 0 for deterministic/factual tasks
    max_tokens=512,
    stop=["</s>", "[INST]"],
)
```

### 5.2 Self-Review Checklist (LLM Engineering)

- [ ] Evaluation framework built BEFORE fine-tuning, not after
- [ ] Training data quality-audited (deduplication, quality filter, human review sample)
- [ ] Baseline established (what does the base model + prompting achieve without fine-tuning?)
- [ ] Fine-tuned model compared against baseline on full eval set — not cherry-picked examples
- [ ] RAG retrieval quality measured independently of generation quality
- [ ] Hallucination rate measured on adversarial test set
- [ ] Prompt injection attack surface assessed
- [ ] Output validation layer in place
- [ ] Serving latency profiled at P95/P99 under realistic load
- [ ] Model versioned, registered, and one-command-rollback-able
- [ ] Monitoring for response quality degradation in production
