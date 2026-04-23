---
name: god-vector-databases
description: "God-level vector database and embedding skill covering embedding models (sentence-transformers, OpenAI embeddings, Cohere, BGE, E5), vector database selection and operation (Pinecone, Qdrant, Weaviate, Milvus, pgvector, Chroma, FAISS), approximate nearest neighbor algorithms (HNSW, IVF, PQ — tradeoffs), hybrid search (dense + sparse), metadata filtering, index configuration, production scaling, and embedding evaluation (MTEB benchmark). The researcher-warrior understands that 'vector search' is not magic — it is applied linear algebra and information retrieval, and the quality of retrieval depends entirely on the quality of embeddings and the correctness of the index configuration."
metadata:
  version: "1.0.0"
---

# God-Level Vector Databases and Embeddings

## Researcher-Warrior Mindset

Vector search is not magic. An embedding is a point in high-dimensional space. Cosine similarity is an angle. HNSW is a graph. When your retrieval quality is poor, it is because your embeddings are wrong, your index is misconfigured, or your data is garbage — not because the database vendor failed you. You diagnose retrieval problems by evaluating embeddings on your domain, not by switching to a trendier vector database.

**Anti-hallucination rules:**
- Never claim a specific embedding model achieves a particular MTEB score without citing the leaderboard date and version — scores change as models are updated.
- Never invent vector database pricing — check vendor docs directly.
- Do not claim HNSW recall percentages without specifying ef, M, and dataset size.
- Do not recommend a specific vector database for a workload without asking about data size, latency requirements, and infrastructure preferences.
- When describing algorithm internals, state the level of abstraction — do not present simplified explanations as complete specifications.

---

## Part 1: Embedding Fundamentals

### What Is an Embedding?
An embedding is a dense, fixed-size real-valued vector that encodes the semantic meaning of an input (text, image, audio, code) in a continuous vector space. Semantically similar inputs map to nearby points in this space.

A text embedding model takes a string → returns a vector of shape [d], where d is the embedding dimension (e.g., 384, 768, 1536, 3072).

The embedding model learns this mapping from training data (typically contrastive learning on pairs of similar/dissimilar text). The critical insight: **the geometry of the space encodes semantics only for inputs that resemble the training distribution.**

### Why Cosine Similarity Works
Cosine similarity measures the angle between two vectors:
```
cosine_sim(a, b) = (a · b) / (||a|| × ||b||)
```
Range: -1 (opposite) to +1 (identical direction).

For embeddings, the direction encodes meaning — not the magnitude. Two texts with the same semantic content will have embeddings pointing in the same direction, regardless of length differences that might inflate or deflate the vector norm.

**Dot product similarity** is faster (no normalization step) and equivalent to cosine similarity on unit-norm vectors. Many embedding APIs return unit-normalized vectors — verify before choosing your distance metric.

**L2 (Euclidean) distance** is appropriate when magnitude matters, less common for text embeddings.

### Dimensionality Tradeoffs
Higher dimensionality = more information capacity = larger memory footprint + slower search.

| Dimension | Memory per 1M vectors (float32) | Typical use |
|-----------|----------------------------------|-------------|
| 384 | ~1.5 GB | Lightweight, fast, sentence-transformers small models |
| 768 | ~3 GB | Standard BERT-sized embeddings |
| 1536 | ~6 GB | OpenAI text-embedding-3-small |
| 3072 | ~12 GB | OpenAI text-embedding-3-large |

**Matryoshka Representation Learning (MRL):** A training technique that allows truncation of embeddings to lower dimensions while retaining most quality. OpenAI's text-embedding-3 models use MRL — you can truncate to 256 dimensions for speed at modest quality cost.

---

## Part 2: Embedding Model Selection

### The Golden Rule
**Evaluate on your domain data, not just MTEB.** MTEB is a proxy. A model ranked #3 on MTEB may outperform #1 on your specific corpus and query distribution. Domain-specific fine-tuning frequently beats top MTEB models for specialized domains.

### Sentence-Transformers (SBERT)
The `sentence-transformers` library (UKP Lab) provides dozens of pretrained models with a unified API.

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('BAAI/bge-large-en-v1.5')
embeddings = model.encode(["Hello world", "Goodbye world"], normalize_embeddings=True)
```

Key models in the ecosystem:
- `all-MiniLM-L6-v2`: 384-dim, fast, good for high-throughput
- `all-mpnet-base-v2`: 768-dim, higher quality, slower
- `BAAI/bge-large-en-v1.5`: Strong retrieval, requires instruction prefix for queries
- `intfloat/e5-large-v2`: Microsoft E5, instruction-prefixed

### OpenAI Embeddings
**text-embedding-3-small:** 1536-dim (reducible with MRL), strong quality, cost-effective. Suitable for most RAG applications.

**text-embedding-3-large:** 3072-dim (reducible), highest OpenAI quality, 2× cost of small.

**Ada-002 (legacy):** 1536-dim, no MRL support, still widely deployed but superseded by v3.

```python
from openai import OpenAI
client = OpenAI()
response = client.embeddings.create(model="text-embedding-3-small", input=["text"])
embedding = response.data[0].embedding
```

**Considerations:** API latency adds to query time. Rate limits apply. Embedding requests are logged — consider data privacy implications for sensitive content.

### Cohere Embed
**embed-multilingual-v3.0:** Supports 100+ languages. Strong for cross-lingual retrieval. 1024-dim.

**embed-english-v3.0:** English-optimized. Strong retrieval scores.

Cohere's models support input types: `search_document`, `search_query`, `classification`, `clustering` — use the correct type for better results.

### BGE Models (BAAI)
BGE (BAAI General Embedding) models consistently rank at the top of MTEB for retrieval.

**Important:** BGE models require instruction prefixes for queries in retrieval mode:
- Query: `"Represent this sentence for searching relevant passages: {query}"`
- Document: no prefix needed

Available in small/base/large sizes. `bge-m3` is a multilingual variant with sparse retrieval support.

### E5 Models (Microsoft)
Must prefix all inputs:
- Query: `"query: {query_text}"`
- Document: `"passage: {document_text}"`

`e5-mistral-7b-instruct`: Large model (7B), top MTEB scores, compute-intensive.

### Domain Fine-Tuning
When general embeddings underperform on specialized domains (legal, medical, code, financial), fine-tune on domain-specific pairs.

```python
from sentence_transformers import SentenceTransformer, losses
from torch.utils.data import DataLoader

model = SentenceTransformer('BAAI/bge-large-en-v1.5')
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
train_loss = losses.MultipleNegativesRankingLoss(model)
model.fit(train_objectives=[(train_dataloader, train_loss)], epochs=3)
```

**MultipleNegativesRankingLoss** is the standard loss for retrieval fine-tuning — in-batch negatives are automatically used.

---

## Part 3: MTEB Benchmark

### What MTEB Measures
MTEB (Massive Text Embedding Benchmark) evaluates embeddings across:
- **Retrieval:** BEIR benchmark tasks (BM25 baseline ≈ 41 nDCG@10 on average)
- **Semantic Textual Similarity:** Correlation with human similarity judgments
- **Classification:** Embedding → linear probe accuracy
- **Clustering:** K-means clustering quality
- **Pair classification:** Detecting paraphrase/duplicate pairs
- **Reranking:** Reranking retrieved results

56+ tasks across 112+ languages (MTEB multilingual). The leaderboard lives at `huggingface.co/spaces/mteb/leaderboard`.

### Limitations of MTEB
1. **Test set contamination:** Large models may have seen MTEB benchmark texts during training
2. **Domain mismatch:** MTEB corpora (news, Wikipedia, academic papers) may not represent your domain
3. **Query distribution mismatch:** MTEB queries are often longer and more formal than production user queries
4. **Recency:** MTEB scores are static snapshots — a model that was #1 six months ago may not be #1 today

### Running Custom Evaluation with BEIR
```python
from beir import util
from beir.datasets.data_loader import GenericDataLoader
from beir.retrieval.evaluation import EvaluateRetrieval
from beir.retrieval import models

# Load your dataset in BEIR format
corpus, queries, qrels = GenericDataLoader(data_folder="my_dataset/").load(split="test")

# Evaluate
model = models.SentenceBERT("BAAI/bge-large-en-v1.5")
retriever = EvaluateRetrieval(model, score_function="dot")
results = retriever.retrieve(corpus, queries)
ndcg, _map, recall, precision = retriever.evaluate(qrels, results, [1, 10, 100])
```

**Metrics to care about for retrieval:** nDCG@10 (primary), Recall@100 (measures how many relevant docs are in top-100 for reranking), MRR@10 (mean reciprocal rank).

---

## Part 4: Approximate Nearest Neighbor Algorithms

### Why Not Exact Search?
Brute force (IndexFlatL2 in FAISS) computes the exact nearest neighbor by comparing the query to every vector. For 1M vectors at 768 dimensions: ~1B floating point operations per query. Unacceptable for production at any meaningful scale. ANN algorithms trade small amounts of recall for massive speed improvements.

### HNSW (Hierarchical Navigable Small World)
HNSW is a graph-based ANN algorithm. It builds a multi-layer graph where:
- Upper layers have long-range connections (sparse, for fast navigation)
- Lower layers have short-range connections (dense, for precise local search)
- Layer 0 has all vectors; upper layers have exponentially fewer

**Search process:** Enter the graph at the top layer, greedily navigate toward the query vector, descend to lower layers, refine the search in the dense local neighborhood.

**Key parameters:**

| Parameter | What it controls | Typical range | Effect |
|-----------|-----------------|---------------|--------|
| `M` | Connections per node at each layer | 8–64 | ↑M = ↑recall, ↑memory, ↑index build time |
| `ef_construction` | Beam width during index build | 100–500 | ↑ef_construction = ↑recall, ↑build time |
| `ef` (query) | Beam width during search | 50–500 | ↑ef = ↑recall, ↑query latency |

**Practical defaults:** M=16, ef_construction=200, ef=100 — good starting point, then tune ef upward until recall meets SLA.

**Memory cost:** Each vector requires original storage + graph edges. For M=16, HNSW adds ~(M × 2 × 4 bytes × num_layers) per vector. Roughly 2-4× more memory than flat index for typical M values.

**Best for:** Most production use cases where memory is available. Consistently best recall/speed tradeoff among ANN algorithms.

### IVF (Inverted File Index)
Partitions the vector space into `nlist` Voronoi cells (clusters via k-means). During search, identifies `nprobe` nearest cluster centroids, searches only vectors within those clusters.

| Parameter | What it controls | Typical value |
|-----------|-----------------|---------------|
| `nlist` | Number of clusters | sqrt(N) to 4*sqrt(N) |
| `nprobe` | Clusters searched at query time | 1–nlist (↑nprobe = ↑recall, ↑latency) |

**Best for:** Very large datasets (100M+) where HNSW memory is prohibitive. Slightly lower recall than HNSW for same query time, but scales to larger datasets.

### PQ (Product Quantization)
Lossy vector compression. Splits each vector into `m` sub-vectors, quantizes each sub-vector to the nearest of `k*` centroids (codewords). Stores the codebook index (1 byte) per sub-vector instead of 4 bytes per float.

**Compression ratio:** A 768-dim float32 vector (3072 bytes) with m=96, k*=256 becomes 96 bytes — 32× compression.

**Cost:** Recall degradation (typically 2-8% loss) and slower query than flat IVF due to asymmetric distance computation.

**IVFPQ (combination):** IVF for coarse quantization + PQ for vector compression. Enables billions of vectors on commodity hardware. FAISS's `IndexIVFPQ`.

### Quantization in Modern Vector DBs
Qdrant supports:
- **Scalar quantization (int8):** 4× compression, <1% recall loss
- **Binary quantization:** 32× compression, moderate recall loss — use oversampling + rescoring

---

## Part 5: Vector Database Comparison

### Pinecone
**Architecture:** Fully managed cloud service. Pod-based (dedicated compute, fixed capacity) or serverless (pay-per-query, auto-scales).

**Strengths:**
- Zero infrastructure management
- Namespaces for multi-tenancy (logical separation within an index)
- Metadata filtering with boolean/range conditions
- Hybrid search (sparse+dense) with Pinecone's own sparse index

**Limitations:**
- No self-hosting option — data leaves your infrastructure
- Pod-based pricing can be expensive at scale
- Less flexibility in index configuration vs open-source

**When to use:** Teams that need production vector search immediately, no infrastructure team, willing to pay the managed premium.

### Qdrant
**Architecture:** Open source (Rust), cloud managed option, or self-hosted (Docker/Kubernetes). Apache 2.0 license.

**Strengths:**
- Rust performance — low latency, low memory overhead
- HNSW index with quantization (scalar, binary, product)
- Payload filtering: pre-filter (before vector search) or post-filter
- Sparse vector support for hybrid search (via `SparseVector` type)
- On-disk vector storage: mmap-based, large datasets without RAM
- Named vectors: multiple embedding spaces per point

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

client = QdrantClient("localhost", port=6333)
client.create_collection(
    collection_name="docs",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)
client.upsert(
    collection_name="docs",
    points=[PointStruct(id=1, vector=[0.1]*768, payload={"source": "wiki"})]
)
results = client.search(
    collection_name="docs",
    query_vector=[0.1]*768,
    query_filter=Filter(must=[FieldCondition(key="source", match=MatchValue(value="wiki"))]),
    limit=10
)
```

**When to use:** Strong first choice for new self-hosted projects. Best feature set in open source category.

### Weaviate
**Architecture:** Open source (Go), managed cloud (Weaviate Cloud), or self-hosted.

**Strengths:**
- GraphQL API (and REST) — familiar for GraphQL teams
- Built-in vectorization modules: `text2vec-openai`, `text2vec-cohere`, `text2vec-huggingface`
- Hybrid search: BM25F (sparse) + vector (dense) with RRF fusion — built in
- Multi-tenancy: class-level isolation
- Modules: `qna-openai`, `generative-openai` — LLM integration built in

**Limitations:** GraphQL complexity can be verbose for simple queries. Go-based, so slightly less memory-efficient than Rust-based Qdrant.

**When to use:** Teams that want vectorization and LLM integration built into the database, prefer GraphQL, or need multi-tenancy with strict isolation.

### Milvus
**Architecture:** Open source, cloud-native (Kubernetes-first), distributed. Backed by Zilliz.

**Strengths:**
- Multiple index types: IVF_FLAT, IVF_PQ, IVF_SQ8, HNSW, DISKANN
- GPU indexing and search (NVIDIA GPU support)
- Collection-level schema, partition-level organization
- Billion-scale data (designed for massive scale)
- Cloud offering: Zilliz Cloud

**Limitations:** More complex deployment than Qdrant (requires etcd, MinIO by default). Heavier operational overhead.

**When to use:** Billion-scale vector workloads, GPU-accelerated search requirements, Kubernetes-native infrastructure teams.

### pgvector
**Architecture:** PostgreSQL extension. Adds `vector` data type, `ivfflat` and `hnsw` index types, and distance operators.

```sql
CREATE EXTENSION vector;
CREATE TABLE documents (id bigserial, content text, embedding vector(768));
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);

SELECT id, content, 1 - (embedding <=> '[0.1,...]'::vector) AS similarity
FROM documents
WHERE metadata_field = 'value'  -- standard SQL filtering
ORDER BY embedding <=> '[0.1,...]'
LIMIT 10;
```

**Strengths:**
- Single system: vectors live alongside relational data — join vector search results with SQL tables
- No new infrastructure for existing Postgres teams
- Full SQL: WHERE clauses, JOINs, aggregations on vector search results
- ACID transactions across vector updates and relational data
- `pg_embedding` (Neon) and `pgvector-rs` are alternative implementations

**Limitations:**
- Performance ceiling below dedicated vector databases for high-QPS, large-scale workloads
- HNSW index is single-threaded during build
- Filtering is post-filter only (no pre-filter) with index — may miss results under heavy filter

**When to use:** Existing Postgres infrastructure, data volumes under ~10M vectors, team prefers SQL, or vector search is supplementary to a relational workload.

### Chroma
**Architecture:** Open source, Python-native, in-memory or persistent (DuckDB + Parquet).

```python
import chromadb

client = chromadb.Client()  # or chromadb.PersistentClient(path="/data")
collection = client.create_collection("docs")
collection.add(documents=["doc1", "doc2"], ids=["id1", "id2"])
results = collection.query(query_texts=["search query"], n_results=5)
```

**Strengths:** Dead-simple setup, great for development and prototyping, Python-first API.

**Limitations:** Not designed for production at scale, limited operational features.

**When to use:** Development, prototyping, small-scale projects (<100K vectors), demos.

### FAISS (Facebook AI Similarity Search)
FAISS is a C++ library (with Python bindings), not a database. It has no server, no persistence, no authentication.

**Key index types:**
- `IndexFlatL2` / `IndexFlatIP`: Exact search. Baseline for measuring ANN recall.
- `IndexHNSWFlat`: HNSW index. Good recall, high memory.
- `IndexIVFFlat`: IVF index. Lower memory, requires training.
- `IndexIVFPQ`: IVF + Product Quantization. Maximum compression.

```python
import faiss, numpy as np

d = 768  # dimension
index = faiss.IndexHNSWFlat(d, 32)  # M=32
index.hnsw.efConstruction = 200
index.add(vectors)  # np.float32 array shape [N, d]
distances, indices = index.search(query_vectors, k=10)
```

**When to use:** Building a custom retrieval system, embedding in existing applications, benchmarking, when you need GPU-accelerated search (FAISS GPU) and can manage the infrastructure yourself.

---

## Part 6: Hybrid Search

### When Vector Search Alone Fails
Pure semantic search fails on:
- Exact product codes, SKUs, identifiers
- Technical acronyms (RAG, FSDP — model may not recognize domain-specific meaning)
- Proper nouns (rare names, new brand names)
- Numeric values (model may not encode "price > $500" semantically)

### Sparse Retrieval: BM25
BM25 (Best Match 25) is the gold standard sparse retrieval algorithm. Ranks by term frequency (TF) × inverse document frequency (IDF):
```
BM25(q, d) = Σ IDF(q_i) × [TF(q_i, d) × (k1+1)] / [TF(q_i, d) + k1 × (1 - b + b × |d|/avgdl)]
```
- k1 (1.2–2.0): term frequency saturation
- b (0.75): length normalization
- IDF penalizes common terms, rewards rare terms

BM25 requires no model inference — it's pure index lookup. Extremely fast.

### Reciprocal Rank Fusion (RRF)
Combines rankings from multiple retrieval systems without score normalization:
```python
def rrf(rankings: list[list[int]], k: int = 60) -> dict[int, float]:
    scores = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])
```
k=60 is the standard constant. RRF is robust to score scale differences between retrieval systems. Works better than linear combination of scores for most scenarios.

### When Hybrid Beats Pure Vector
Empirically, hybrid search outperforms pure vector search when:
- Query contains specific technical terms, product names, or codes
- Document collection is large and diverse (many topics)
- Users mix informational queries with navigational queries
- Domain is specialized (legal, medical, code)

**Conservative estimate:** Hybrid search typically improves nDCG@10 by 2-8% over pure vector for mixed query types.

---

## Part 7: Metadata Filtering Strategies

### Pre-Filter (Before Vector Search)
Restrict the search space before ANN lookup.
- **Advantage:** Faster for large filter sets (search only relevant vectors)
- **Risk:** If filter is very restrictive, few vectors remain — ANN graph traversal becomes less efficient, HNSW may miss relevant results

Qdrant implements pre-filter as a `must` condition in the query filter.

### Post-Filter (After Vector Search)
Search full index, then filter results.
- **Advantage:** Maximum ANN recall — full graph is traversed
- **Risk:** If filter is restrictive, you may get zero results (all top-k vectors are filtered out)

### Oversampling Pattern
Best of both: search for k×N results, filter, return top k.

```python
# Get 100 results, filter to those matching criteria, return top 10
results = collection.search(query_vector, limit=100)
filtered = [r for r in results if r.payload["category"] == "sports"][:10]
```

**When to use oversampling:** When filter selectivity is unknown, when recall is critical, when dataset is smaller than the index can scan efficiently.

---

## Part 8: Production Considerations

### Index Warm-Up
HNSW graph traversal is memory-access-heavy. Cold index (not in RAM cache) results in very high latency from disk reads. After startup or index load:
```python
# Send a batch of representative warm-up queries before serving traffic
for warmup_query in warmup_queries:
    collection.search(warmup_query, limit=10)
```

Kubernetes readiness probe should not return ready until warm-up completes.

### Multi-Tenancy Patterns
| Pattern | Implementation | Isolation | Overhead |
|---------|---------------|-----------|---------|
| Namespaces | Pinecone namespaces, Weaviate classes | Logical | Low |
| Metadata filtering | Filter by `tenant_id` payload | Logical | Low (scan overhead) |
| Collections per tenant | Separate collections/indexes | Physical | High (memory per collection) |
| Separate deployments | One cluster per tenant | Physical | Highest |

For high-isolation requirements (regulated industries), separate collections or deployments. For SaaS with many tenants, metadata filtering with oversampling is practical up to ~1000 tenants.

### Monitoring
Critical metrics for vector database monitoring:
- **Query latency (p50, p95, p99):** Alert on p99 > SLA threshold
- **QPS (queries per second):** Capacity planning, alert on sustained high load
- **Recall rate:** Periodically evaluate against a labeled retrieval test set
- **Index memory usage:** Alert before OOM
- **Upsert throughput and lag:** For real-time embedding pipelines
- **Cache hit rate:** For in-memory tier caching

---

## Part 9: RAG-Specific Embedding Considerations

### Chunking Strategy Affects Retrieval Quality
Embedding quality depends heavily on chunk boundaries:
- Too small (50 tokens): Missing context — embedding cannot capture full concept
- Too large (1000+ tokens): Multiple topics mixed in one embedding — dilutes similarity signal
- **Sweet spot:** 256–512 tokens with 50–100 token overlap

**Sentence-aware chunking:** Split on sentence boundaries, not character count. NLTK or spaCy sentence tokenizer.

**Semantic chunking:** Embed each sentence, detect topic shifts by cosine distance drops, create chunks at semantic boundaries. More expensive but better quality.

### Embedding Queries vs Documents
Many embedding models are trained asymmetrically — the query embedding space may differ from the document embedding space. BGE and E5 explicitly use different instruction prefixes for queries vs documents. If you embed queries the same way as documents for asymmetric models, recall drops significantly.

### Reranking Pipeline
Two-stage retrieval:
1. **Stage 1 (recall):** Vector search, retrieve top-100 candidates (optimized for recall)
2. **Stage 2 (precision):** Cross-encoder reranking, rerank top-100, return top-5

Cross-encoders (e.g., `cross-encoder/ms-marco-MiniLM-L-12-v2`) jointly encode query+document — much higher quality than bi-encoder similarity but O(N) compute per query (impractical as first-stage retriever).

```python
from sentence_transformers import CrossEncoder
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')
scores = reranker.predict([(query, doc) for doc in candidates])
reranked = sorted(zip(candidates, scores), key=lambda x: -x[1])
```

Cohere Rerank API provides a managed reranking service.

---

## Part 10: Cross-Domain Connections

### pgvector ↔ Existing Postgres Workloads
pgvector's superpower is eliminating data synchronization complexity. If your application data already lives in Postgres, embedding vectors in the same table means:
- Vector search results can JOIN with user tables, permission tables, metadata tables
- Transactional consistency: embedding updates and document updates in same transaction
- No eventual consistency lag between relational and vector data
- Backup/restore covers both dimensions

**Pattern:** `documents` table with `content TEXT`, `embedding vector(768)`, and standard columns. Index on `embedding` for vector search, B-tree on other columns for metadata filters.

### Kafka ↔ Real-Time Embedding Updates
For real-time content (news, product catalog, user-generated content), embedding updates cannot be batch-only. Pattern:
1. Document creation/update triggers Kafka message
2. Embedding consumer reads from topic, calls embedding API
3. Upserts to vector database

Qdrant and Weaviate both support upserts (insert or update by ID). For Pinecone, use upsert with same ID. The challenge: embedding API calls are the bottleneck — batch embed when possible (most APIs support batch input up to 2048 inputs per call).

### Vector Search ↔ RAG Architecture
The researcher-warrior knows that vector search is infrastructure, not the product. In a RAG system:
- Retrieval quality is the multiplier on LLM quality — bad retrieval makes the best LLM useless
- Evaluate retrieval quality separately from generation quality (decomposed evaluation)
- Embedding fine-tuning typically yields more improvement than switching LLMs for knowledge-grounded tasks

---

## Self-Review Checklist (15 Items)

Before delivering any vector database advice, verify:

1. [ ] Is the embedding model appropriate for the query type (symmetric vs asymmetric retrieval)?
2. [ ] Is the correct instruction prefix used for BGE/E5 models (query vs document prefixes)?
3. [ ] Is MTEB performance verified on a domain-specific test set, not just the leaderboard?
4. [ ] Is the distance metric (cosine/dot/L2) consistent between index configuration and embedding properties?
5. [ ] Are HNSW parameters (M, ef_construction, ef) tuned and not left at defaults?
6. [ ] Is hybrid search considered for queries with technical terms, proper nouns, or identifiers?
7. [ ] Is metadata filtering strategy (pre/post/oversample) chosen based on filter selectivity?
8. [ ] Is index warm-up handled before traffic is served after restart?
9. [ ] Is recall evaluated on a labeled test set (not just "it looks good")?
10. [ ] Is vector memory footprint calculated for the target dataset size?
11. [ ] Is multi-tenancy isolation level matched to security/compliance requirements?
12. [ ] Is a reranking stage considered for precision-critical retrieval?
13. [ ] Are query and document embedding paths symmetric (same model, appropriate instruction prefixes)?
14. [ ] Is chunking strategy appropriate (256-512 tokens, sentence-aware boundaries)?
15. [ ] Is the vector database choice appropriate for data scale and infrastructure team capabilities?

---

## Reference: Vector Database Selection Matrix

| Criteria | Pinecone | Qdrant | Weaviate | Milvus | pgvector | Chroma | FAISS |
|----------|----------|--------|----------|--------|----------|--------|-------|
| Self-hosted | No | Yes | Yes | Yes | Yes | Yes | Library |
| Managed cloud | Yes | Yes | Yes | Yes (Neon) | No | No | No |
| Scale ceiling | ~1B (pods) | ~100M | ~100M | ~1B+ | ~10M | ~1M | ~1B (GPU) |
| Hybrid search | Yes | Yes | Yes | Partial | No | No | No |
| SQL integration | No | No | No | No | Yes | No | No |
| GPU search | No | No | No | Yes | No | No | Yes |
| Primary language | Go | Rust | Go | Go | C/SQL | Python | C++ |
| Best for | Managed, fast start | OSS, all-around | GraphQL, modules | Billion-scale | Postgres shops | Dev/prototype | Custom pipelines |
