---
name: god-search-engineering
description: "God-level search engineering skill covering Elasticsearch and OpenSearch (inverted index, mappings, analyzers, query DSL, aggregations, performance tuning, cluster management), Typesense (fast typo-tolerant search, faceting, synonyms), Apache Solr (SolrCloud, schema design, relevance tuning), search relevance engineering (BM25, TF-IDF, learning to rank), vector search (KNN, HNSW algorithm, dense vector fields, hybrid search), and the art of making users find what they need — even when they don't know exactly what they're looking for."
metadata:
  version: "1.0.0"
---

# God-Level Search Engineering Skill

## Researcher-Warrior Mandate

You are a search engineer who has debugged mapping explosions in production, traced relevance regressions in BM25 scoring, and tuned HNSW parameters for billion-vector corpora. You never hallucinate query DSL syntax. You never confuse Elasticsearch and OpenSearch divergences without flagging them. You know that bad search relevance silently destroys user trust — users don't complain, they leave.

**Anti-Hallucination Rules:**
- Query DSL syntax must reflect actual Elasticsearch/OpenSearch documentation — no invented field names or clause types
- HNSW parameter names (`m`, `ef_construction`, `ef`) must be correctly attributed to the library/engine
- BM25 parameter names (`k1`, `b`) are correct — do not rename them
- Distinguish Elasticsearch (Elastic BV) from OpenSearch (AWS fork at version 7.10) — they have diverged since 2021
- Version-specific features must be flagged (e.g., kNN in Elasticsearch 8.x vs OpenSearch 1.x implementation differs)
- Typesense API fields must reflect actual Typesense documentation

---

## Mental Model: What Is Search?

Search is **relevance ranking over an indexed corpus**. The fundamental pipeline:
1. **Ingestion**: raw content → parse → analyze (tokenize, normalize) → index (inverted index, vector index)
2. **Query processing**: raw query string → analyze → match against index → score → rank → return
3. **Relevance evaluation**: are the top results actually what users wanted? This is an engineering problem, not just a UX problem.

The failure modes of search:
- **Precision failure**: returning irrelevant results (users see junk)
- **Recall failure**: missing relevant results (users can't find what exists)
- **Ranking failure**: returning relevant results in wrong order (the answer is on page 3)
- **Latency failure**: correct results, too slow to be useful

---

## The Inverted Index: Foundation of Full-Text Search

An inverted index maps from **term → list of documents containing that term** (called a posting list). This inverts the document-centric structure (document → list of terms) into a term-centric structure optimized for lookup.

```
Text: "The quick brown fox jumps over the lazy dog"

After analysis (tokenize + lowercase + stop word removal):
Terms: [quick, brown, fox, jump, lazi, dog]  (stemmed)

Inverted index:
"quick" → [doc1, doc5, doc23]
"brown" → [doc1, doc7]
"fox"   → [doc1, doc12, doc45]
```

A search for "quick fox" becomes:
1. Analyze the query: ["quick", "fox"]
2. Lookup posting lists for each term
3. Intersect (AND) or union (OR) the posting lists
4. Score each document using BM25
5. Return top K by score

**Why O(1) term lookup**: inverted index is a hash map or B-tree over terms. Looking up "fox" is a direct index lookup, not a scan of all documents. This is why full-text search at scale (billions of documents) is feasible.

**Posting list entries** typically store: document ID, term frequency (TF), term positions (for phrase matching), offsets (for highlighting). More stored data = richer queries, higher storage cost.

---

## Elasticsearch and OpenSearch: Core Concepts

### Mappings: The Schema of Your Index

**Dynamic mapping** (default): Elasticsearch infers field types from the first document. Dangers:
- A field first indexed as `long` cannot then receive `text` — type conflict causes indexing failures
- **Mapping explosion**: dynamic mapping on nested JSON creates a new field for every unique key. With high-cardinality nested objects (user-defined properties, event metadata), this can create tens of thousands of fields → heap exhaustion → cluster instability
- Dynamic mapping infers `text` for strings AND creates a `.keyword` sub-field — correct default, but doubles field count

**Production rule: always use explicit mapping.** Define every field before indexing:

```json
PUT /products
{
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "product_id": { "type": "keyword" },
      "name": {
        "type": "text",
        "analyzer": "english",
        "fields": {
          "keyword": { "type": "keyword", "ignore_above": 256 }
        }
      },
      "description": { "type": "text", "analyzer": "english" },
      "price": { "type": "double" },
      "category": { "type": "keyword" },
      "created_at": { "type": "date", "format": "strict_date_optional_time" },
      "in_stock": { "type": "boolean" }
    }
  }
}
```

`"dynamic": "strict"` — reject documents with unmapped fields. Prevents accidental mapping explosion.

### Field Types: Critical Distinctions

| Field Type | Use For | Notes |
|-----------|---------|-------|
| `text` | Full-text search, analyzed | Not sortable, not aggregatable (without `.keyword`) |
| `keyword` | Exact match, filtering, aggregations, sorting | Not analyzed, case-sensitive |
| `integer`, `long`, `double` | Numeric range queries, sorting | |
| `date` | Date/time range queries, date histograms | Supports multiple formats |
| `boolean` | Filtering | |
| `nested` | Arrays of objects where inner object fields must be queried | Stored as hidden documents |
| `object` | Structured data (flat inner fields) | Arrays of objects treated as flat — use nested if querying inner objects |
| `dense_vector` | Vector similarity search | Specify `dims`, `index: true`, `similarity` |
| `geo_point` | Geographic lat/lon | Enables geo-distance queries and filters |

**`nested` vs `object` — the most common mapping mistake**:
```json
// Wrong for querying "find products where variants.color=red AND variants.size=M"
"variants": { "type": "object" }
// Object flattens arrays: color=[red,blue] AND size=[M,L] — any combination matches

// Correct: nested stores each array element as a separate hidden document
"variants": { "type": "nested" }
// nested query correctly scopes to individual array elements
```

### Analyzers: How Text Becomes Terms

An analyzer is a pipeline: **character filters → tokenizer → token filters**

**Standard analyzer** (default):
- Tokenizer: Unicode text segmentation (splits on whitespace and punctuation)
- Token filters: lowercase
- Removes no stop words by default (use `stop` filter explicitly)

**Custom analyzer example for autocomplete** (edge n-gram):
```json
"settings": {
  "analysis": {
    "analyzer": {
      "autocomplete": {
        "type": "custom",
        "tokenizer": "standard",
        "filter": ["lowercase", "autocomplete_filter"]
      },
      "autocomplete_search": {
        "type": "custom",
        "tokenizer": "standard",
        "filter": ["lowercase"]
      }
    },
    "filter": {
      "autocomplete_filter": {
        "type": "edge_ngram",
        "min_gram": 1,
        "max_gram": 20
      }
    }
  }
}
```

**Why two analyzers for autocomplete**: index-time uses edge n-gram (indexes "qu", "qui", "quic", "quick"). Query-time uses standard (analyzes "qui" as just "qui"). If you use edge n-gram at query time, you'd match "qu" inside "quiet" — wrong.

**Language analyzers**: `english` analyzer uses Porter stemmer (running → run), removes stop words (the, a, is). Use language-specific analyzers for non-English content: `french`, `german`, `japanese` (uses Kuromoji tokenizer for CJK).

**Synonym filter**: add to token filter chain. Two modes:
- Expand: `laptop, notebook => laptop, notebook` (index both — flexible querying)
- Contraction: `laptop, notebook => laptop` (index one canonical form — smaller index, less flexible)
- Index-time synonyms are fixed (require reindex to change). Query-time synonyms (in search analyzer) update without reindex.

**Stemmer vs lemmatizer**: stemmers (fast, algorithmic, sometimes produce non-words: "running" → "run") vs lemmatizers (dictionary-based, always produce real words: "better" → "good"). Stemmers used in Elasticsearch — lemmatization requires custom plugins.

---

## Query DSL: When to Use What

### Core Query Types

```json
// match — analyzed full-text search (the right query for text fields)
{ "match": { "description": "quick brown fox" } }
// Analyzes the query string, then OR-matches terms (operator: "and" for stricter matching)
{ "match": { "description": { "query": "quick brown fox", "operator": "and" } } }

// term — exact match (use on keyword, numeric, date — never on text fields)
{ "term": { "category": "electronics" } }
{ "term": { "price": 99.99 } }

// range — numeric or date ranges
{ "range": { "price": { "gte": 50, "lte": 200 } } }
{ "range": { "created_at": { "gte": "now-30d/d", "lte": "now/d" } } }

// match_phrase — words must appear adjacent and in order (analyzed)
{ "match_phrase": { "description": "quick brown fox" } }

// multi_match — search across multiple fields
{ "multi_match": { "query": "laptop computer", "fields": ["name^3", "description", "tags^2"] } }
// ^3 boosts name field score by 3×

// more_like_this — find documents similar to given content
{ "more_like_this": { "fields": ["description"], "like": "wireless noise canceling headphones", "min_term_freq": 1 } }
```

### The `bool` Query: Production Workhorse

```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "name": "laptop" } }
      ],
      "should": [
        { "term": { "brand": "apple" } },
        { "range": { "rating": { "gte": 4.5 } } }
      ],
      "must_not": [
        { "term": { "in_stock": false } }
      ],
      "filter": [
        { "term": { "category": "electronics" } },
        { "range": { "price": { "lte": 1000 } } }
      ],
      "minimum_should_match": 1
    }
  }
}
```

**Critical distinction — `must` vs `filter`**:
- `must`: query participates in **scoring** + must match (documents without match are excluded)
- `filter`: must match but does **not affect score** — filter clauses are **cached** for performance
- Use `filter` for structured data (category, price range, date range, boolean flags) — it's faster and cacheable
- Use `must` for full-text queries where relevance score matters

**`should` without `must`**: if there are no `must` or `filter` clauses, at least one `should` must match (effectively acts as `must`). With `must` present, `should` is optional but boosts score if matched.

---

## Relevance Tuning: BM25 and Beyond

### BM25 Scoring

BM25 (Best Match 25) is the default scoring algorithm in Elasticsearch/OpenSearch. It improves on TF-IDF with term frequency saturation and field length normalization.

**BM25 parameters**:
- `k1` (default 1.2): controls term frequency saturation. Higher values = less saturation (more TF impact). Range 1.2–2.0 for most use cases.
- `b` (default 0.75): controls field length normalization. 0 = no normalization (all lengths equal), 1 = full normalization (shorter docs score higher for same term match). For technical search where document length is consistent, reduce `b`. For web search with varied doc lengths, keep at 0.75.

```json
PUT /products
{
  "settings": {
    "similarity": {
      "my_bm25": { "type": "BM25", "k1": 1.5, "b": 0.6 }
    }
  },
  "mappings": {
    "properties": {
      "description": { "type": "text", "similarity": "my_bm25" }
    }
  }
}
```

### Function Score Queries

`function_score` wraps a query and modifies scores with custom functions:

```json
{
  "query": {
    "function_score": {
      "query": { "match": { "name": "laptop" } },
      "functions": [
        {
          "gauss": {
            "created_at": {
              "origin": "now",
              "scale": "30d",
              "decay": 0.5
            }
          }
        },
        {
          "field_value_factor": {
            "field": "rating",
            "factor": 1.2,
            "modifier": "log1p",
            "missing": 1
          }
        }
      ],
      "score_mode": "multiply",
      "boost_mode": "multiply"
    }
  }
}
```

**Decay functions**: `gauss` (Gaussian curve), `linear`, `exp` (exponential). Use for recency boost (newer = higher score), geo-proximity boost (closer = higher score).

**`field_value_factor`**: multiply BM25 score by a field value (e.g., rating, click count). Use `modifier: "log1p"` to prevent single high-value field from overwhelming relevance score.

**Index-time vs query-time boosting**:
- Query-time boosting (`^2.0` in `fields`): flexible, no reindex needed, applied per query
- Index-time boosting (deprecated in ES 7+): avoid — cannot change without reindex

### Learning to Rank (LTR)

LTR uses machine learning to optimize ranking. Requires: labeled dataset (query, document, relevance judgment), feature extraction, model training (LambdaMART, LambdaRank), and a plugin (Elasticsearch LTR plugin, OpenSearch LTR).

LTR features typically include: BM25 scores for various fields, click-through rate, recency, document quality signals, personalization signals.

LTR is complex infrastructure — only worth it when rule-based tuning has plateaued and you have labeled relevance data.

---

## Aggregations

Aggregations compute analytics over the result set or entire index. They run alongside search queries.

```json
{
  "query": { "match": { "category": "electronics" } },
  "aggs": {
    "price_ranges": {
      "range": {
        "field": "price",
        "ranges": [
          { "to": 100 },
          { "from": 100, "to": 500 },
          { "from": 500 }
        ]
      }
    },
    "top_brands": {
      "terms": {
        "field": "brand",
        "size": 10
      }
    },
    "daily_sales": {
      "date_histogram": {
        "field": "created_at",
        "calendar_interval": "day"
      }
    },
    "avg_price": {
      "avg": { "field": "price" }
    }
  }
}
```

**`terms` aggregation**: computes approximate top-N values. Default size is 10. Increasing size improves accuracy but increases heap usage. For exact counts on all values, use `composite` aggregation with pagination.

**Aggregations on text fields require keyword subfield**: you cannot aggregate on an analyzed `text` field. Map as:
```json
"brand": {
  "type": "text",
  "fields": { "keyword": { "type": "keyword" } }
}
```
Aggregate on `brand.keyword`, search on `brand`.

**Pipeline aggregations**: compute from other aggregation results.
- `moving_avg` / `moving_fn`: smoothed time series
- `derivative`: rate of change between buckets
- `cumulative_sum`: running total
- `bucket_selector`: filter buckets based on aggregation values

**Nested aggregations**: to aggregate on nested fields, use nested aggregation wrapper:
```json
"aggs": {
  "variants": {
    "nested": { "path": "variants" },
    "aggs": {
      "colors": { "terms": { "field": "variants.color" } }
    }
  }
}
```

---

## Performance Engineering

### Sharding Strategy

Primary shards are fixed at index creation (cannot change without reindex). Plan carefully:

- **Rule of thumb**: 1 shard per 30–50GB of index size (not a hard limit — measure your workload)
- **Oversharding is common and harmful**: each shard is a Lucene index with overhead. 1000 shards × 5MB each is worse than 5 shards × 1GB each
- **Under-sharding limits parallelism**: too few shards = single-node bottleneck on write-heavy workloads
- **For time-series data**: use ILM rollover — start with small initial index, create new index as size/document count threshold is crossed. Each rolled-over index has the right number of shards for its current size.
- **Search parallelism**: each shard is searched separately, results merged. More shards = more parallel search (up to the number of data nodes × cores), but more coordination overhead.

### Replicas

Replica shards are copies of primary shards on different nodes. They:
- Increase **read throughput** (queries can hit any copy)
- Increase **availability** (surviving node still serves queries if another node fails)
- Do NOT help write throughput (writes go to primary, then replicate)
- Can be added/removed without downtime (unlike primary shards)

**During bulk indexing**: set `number_of_replicas=0`, index data, then restore replicas. Replicas during initial load double the write amplification.

### Indexing Performance

```json
// Increase refresh interval during bulk indexing
PUT /my-index/_settings
{ "refresh_interval": "30s" }
// Default: 1s (causes frequent small segments, high overhead during bulk)
// After indexing: restore to 1s or -1 (manual refresh only)

// Disable refresh entirely during initial load
{ "refresh_interval": "-1" }
```

**`_forcemerge`**: merge Lucene segments into fewer larger segments. Use on read-heavy, static indices (e.g., yesterday's logs). Do NOT run on active write indices — it competes with indexing and can cause issues.

```bash
POST /logs-2024-01-14/_forcemerge?max_num_segments=1
```

**Indexing buffer**: `indices.memory.index_buffer_size` (default 10% of heap). Increase for write-heavy workloads.

**Bulk API**: always use bulk indexing (never index one document at a time). Optimal batch size: 5MB–15MB per bulk request (not document count — measure by payload size). Too large = GC pressure; too small = overhead.

### Heap and JVM

**Heap sizing rule**: set JVM heap to 50% of available RAM, maximum 32GB. Why 32GB maximum? Above 32GB, the JVM switches from Compressed Ordinary Object Pointers (compressed OOPs — 32-bit pointers for heap < 32GB) to 64-bit pointers — effectively wasting memory per object.

```bash
# Elasticsearch JVM options
-Xms16g -Xmx16g  # Equal min and max to prevent heap resizing
# Never go above 32g
```

**GC pauses cause Elasticsearch node drops**: long GC pauses (>10s) cause nodes to miss heartbeats and be ejected from the cluster. Monitor GC pause durations: should be < 1s for stop-the-world (G1GC young gen), with infrequent full GC.

**Circuit breakers**: prevent OOM by rejecting requests that would exceed memory thresholds.
- `fielddata` circuit breaker: limits field data cache (loaded from disk for keyword aggregations in older ES)
- `request` circuit breaker: limits memory per individual request
- `total` circuit breaker: overall JVM heap limit

### Node Roles

In a production cluster, separate node roles (do not run all roles on every node):

| Node Role | Purpose |
|-----------|---------|
| `master` | Cluster coordination, index management, node membership |
| `data` | Stores shards, handles search and indexing |
| `ingest` | Runs ingest pipelines (transform documents before indexing) |
| `coordinating` | Routes requests, merges results — no data, no master |
| `ml` (ES) | Runs machine learning jobs |
| `remote_cluster_client` | Cross-cluster search participation |

**Minimum 3 master-eligible nodes** to prevent split-brain. Cluster requires quorum (`(master_nodes / 2) + 1`) to elect a master. With 2 master nodes, you cannot achieve quorum if one fails.

**Shard allocation awareness**: prevent all shards of an index from landing on nodes in the same availability zone:
```json
PUT /my-index/_settings
{
  "index.routing.allocation.awareness.attributes": "zone"
}
```
Node startup: set `node.attr.zone: us-east-1a` per node. This ensures replicas are on different AZs.

### Index Lifecycle Management (ILM) / Index State Management (ISM)

**ILM** (Elasticsearch) / **ISM** (OpenSearch) automates the progression of time-series indices through lifecycle phases:

```json
// ILM policy for log indices
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": { "max_size": "50gb", "max_age": "1d" }
        }
      },
      "warm": {
        "min_age": "3d",
        "actions": {
          "shrink": { "number_of_shards": 1 },
          "forcemerge": { "max_num_segments": 1 },
          "allocate": { "require": { "data": "warm" } }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "allocate": { "require": { "data": "cold" } }
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": { "delete": {} }
      }
    }
  }
}
```

Rollover creates a new index when the current index exceeds a size or age threshold. Use an alias pointing to the write index — application always writes to the alias.

---

## Vector Search

### Dense Vector Fields

```json
PUT /products
{
  "mappings": {
    "properties": {
      "name_embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine"
      }
    }
  }
}
```

**Similarity metrics**:
- `cosine`: angle between vectors — most common for text embeddings (direction matters, not magnitude)
- `dot_product`: cosine equivalent for unit-normalized vectors (faster computation)
- `l2_norm`: Euclidean distance — for spatial embeddings where magnitude matters

**Normalization**: for cosine similarity to be computed correctly with `dot_product` (for performance), vectors must be L2-normalized. Most embedding models (OpenAI, Sentence Transformers) produce L2-normalized vectors.

### HNSW Algorithm (Hierarchical Navigable Small Worlds)

HNSW is the approximate nearest neighbor (ANN) algorithm used for vector search. It builds a multi-layer graph where:
- Higher layers: long-range connections (coarse navigation)
- Bottom layer: dense connections (fine-grained search)

**Index-time parameters**:
- `m` (default 16): number of bidirectional links per node per layer. Higher = more accurate, more memory, slower indexing. Range: 4–64. For most use cases: 16–32.
- `ef_construction` (default 100): size of candidate list during index construction. Higher = more accurate index, slower build. Range: 50–500.

**Query-time parameters**:
- `num_candidates` (Elasticsearch term) / `ef` (internal parameter): how many candidates to explore during search. Higher = more accurate, slower. Must be ≥ `k` (number of results requested). Typical: 100–500.

```json
// kNN query
{
  "knn": {
    "field": "name_embedding",
    "query_vector": [0.1, 0.2, ...],  // 1536 dims
    "k": 10,
    "num_candidates": 100
  }
}
```

**Approximate vs exact**: HNSW is approximate — it may miss some true nearest neighbors for speed. For exact search (brute force), use `"index": false` on the field and `exact: true` in the query — only practical for small corpora (<100K vectors).

### Hybrid Search

Combining keyword (BM25) and vector (HNSW) search for better relevance than either alone:

**Reciprocal Rank Fusion (RRF)**: combines rankings from multiple retrieval methods without needing to calibrate score scales.
```
RRF_score(d) = Σ 1 / (k + rank_in_result_set_i(d))
```
Where `k` is a constant (default 60 in Elasticsearch's RRF implementation). Document's final score is the sum over all result sets.

```json
// Elasticsearch 8.8+ hybrid search with RRF
{
  "query": { "match": { "description": "wireless headphones" } },
  "knn": {
    "field": "description_embedding",
    "query_vector": [...],
    "k": 50,
    "num_candidates": 200
  },
  "rank": { "rrf": { "window_size": 100 } }
}
```

**Linear combination** (alternative): normalize scores from each retrieval method to [0,1] and combine with weights. Requires careful normalization — scores from different methods are not on the same scale.

**When hybrid beats either alone**:
- Keyword search: misses semantic matches ("vehicle" vs "car")
- Vector search: misses exact match for rare terms, product IDs, codes
- Hybrid: handles both semantic similarity and lexical precision

---

## Typesense: Fast Typo-Tolerant Search

Typesense is a purpose-built search engine emphasizing simplicity, speed, and built-in typo tolerance. It is not a replacement for Elasticsearch at scale, but excels for product search, documentation search, and developer-friendly deployments.

### Collection Schema

```json
{
  "name": "products",
  "fields": [
    { "name": "id", "type": "string" },
    { "name": "name", "type": "string" },
    { "name": "description", "type": "string" },
    { "name": "price", "type": "float" },
    { "name": "category", "type": "string", "facet": true },
    { "name": "rating", "type": "float" },
    { "name": "in_stock", "type": "bool", "facet": true }
  ],
  "default_sorting_field": "rating"
}
```

### Search Parameters

```json
{
  "q": "labtop",
  "query_by": "name,description",
  "query_by_weights": "3,1",
  "filter_by": "price:<1000 && in_stock:true",
  "facet_by": "category,in_stock",
  "sort_by": "rating:desc",
  "num_typos": "2",
  "typo_tokens_threshold": 1,
  "per_page": 20,
  "page": 1
}
```

**Typo tolerance**: Typesense uses built-in fuzzy matching. `num_typos: 2` allows up to 2 character edits (insertions, deletions, transpositions). `"labtop"` matches `"laptop"`. Configurable per field.

**Synonyms**: configure one-way or multi-way synonyms:
```json
// Multi-way: any term matches others
{ "synonyms": ["laptop", "notebook", "ultrabook"], "id": "computer-synonyms" }
// One-way: searching "smart tv" also finds "television"
{ "root": "smart tv", "synonyms": ["television"], "id": "tv-synonym" }
```

**Curations** (pinned/hidden results): override ranking for specific queries. Pin specific products to top positions or hide irrelevant results.

**Analytics queries**: Typesense tracks queries with no results and top search terms. Use to discover vocabulary gaps and missing content.

**Typesense limitations**: no aggregation pipeline comparable to Elasticsearch, no complex join queries, no distributed transactions, designed for single-datacenter deployments with simple replication. Not suitable for log analytics or complex analytics workloads.

---

## Relevance Evaluation: The Measurement Problem

### Offline Metrics

**NDCG (Normalized Discounted Cumulative Gain)**: measures ranking quality accounting for graded relevance.

```
DCG@k = Σ(i=1 to k) rel_i / log2(i + 1)
NDCG@k = DCG@k / IDCG@k
```

Where `rel_i` is the relevance grade of result at position i (e.g., 0=not relevant, 1=partially relevant, 2=highly relevant), and IDCG is the ideal DCG (perfect ranking).

- NDCG = 1.0: perfect ranking
- NDCG = 0.0: worst possible ranking
- Higher positions count more (the log2 discount)

**MRR (Mean Reciprocal Rank)**: for queries where only one result is relevant (e.g., navigational queries).
```
MRR = (1/|Q|) × Σ(q) 1/rank_q
```
Where `rank_q` is the rank of the first relevant result for query q.

**Precision@k**: fraction of top-k results that are relevant. Does not account for ranking order.
**Recall@k**: fraction of all relevant documents that appear in top-k.

### Online Metrics

**Click-through rate (CTR)**: clicks / impressions at position k. Implicit relevance signal — high CTR at low position suggests result is relevant. Low CTR at position 1 suggests top result is not what users wanted.

**A/B testing**: split traffic between ranking variants. Measure: CTR, session depth (how many results viewed), conversion (downstream business metric). Run for statistical significance (minimum 2 weeks to account for weekly seasonality).

**Session-based metrics**: zero-result rate, query reformulation rate (user immediately changes query = bad result), session depth, time-to-click.

### Human Relevance Judgments

Build a judgment dataset: collect top queries (by volume), retrieve results from current system, present to human judges, collect relevance grades (irrelevant/fair/good/perfect). Use for NDCG evaluation when comparing ranking variants.

**Judgment collection tools**: Amazon Mechanical Turk (scale), in-house raters (quality), Quepid (open-source relevance evaluation tool).

---

## Cross-Domain Connections

**Vector search + LLM embeddings**: Large language models (OpenAI `text-embedding-ada-002`, `text-embedding-3-large`, Sentence Transformers, Cohere Embed) produce dense vector representations of text. These embeddings capture semantic meaning. Elasticsearch/OpenSearch stores these as `dense_vector` fields and retrieves semantically similar documents using HNSW.

**Real-time index updates via Kafka**: Kafka connects to Elasticsearch via the Elasticsearch Kafka Connector (Confluent) or custom consumer. Debezium CDC publishes database row changes to Kafka; a consumer transforms and indexes them. This gives near-real-time search index updates without polling the database.

**Relevance tuning and ML**: learning-to-rank is an ML problem. Feature engineering for LTR includes BM25 scores, field statistics, clickstream features, user personalization signals. This connects search engineering to ML pipelines and feature stores.

**Search as a microservice**: the search service consumes events from the event bus (new products, price changes, inventory updates) and maintains its own search index. This is the CQRS pattern applied to search — the search index is a read model built from events.

---

## Self-Review Checklist

Before delivering any search engineering design, code, or analysis, verify:

1. **Explicit mapping defined** — are all fields explicitly mapped? Is `dynamic: strict` set to prevent mapping explosion?
2. **text vs keyword** — are full-text search fields mapped as `text`? Are aggregation/sort/filter fields mapped as `keyword`?
3. **nested vs object** — if querying inside arrays of objects, is `nested` used? Not just `object`?
4. **Analyzer correctness** — does the analyzer at index time match at query time (for exact match fields)? Are autocomplete fields using edge n-gram at index time only?
5. **filter vs must** — are structured filters (category, price range, boolean) in the `filter` clause (cached, no scoring) rather than `must`?
6. **Aggregations on keyword** — are all aggregations running on `.keyword` subfields, not analyzed text fields?
7. **Shard count** — has shard count been planned based on expected index size (30–50GB per shard guideline)? Avoiding over-sharding?
8. **Heap sizing** — is JVM heap set to 50% of RAM with a maximum of 32GB? Are `Xms` and `Xmx` equal?
9. **Replica count** — are replicas set to ≥ 1 in production for availability?
10. **ILM/ISM configured** — for time-series data, is there a lifecycle policy to rollover, shrink, and delete old indices?
11. **Vector similarity metric** — is the correct similarity (`cosine` vs `dot_product` vs `l2_norm`) chosen for the embedding model?
12. **HNSW parameters** — are `m` and `ef_construction` set appropriately? Is `num_candidates` ≥ `k`?
13. **Hybrid search justification** — if using hybrid, is there evidence that keyword + vector outperforms either alone on this workload?
14. **Relevance evaluation** — is there an offline evaluation dataset (NDCG)? Is there an online A/B test plan?
15. **ES vs OpenSearch divergence** — have you verified whether the feature you're recommending exists in the specific version the team is running?

---

## Anti-Hallucination Reminders

- Elasticsearch and OpenSearch **have diverged** since the fork at ES 7.10 (January 2021). Features added in ES 8.x may not exist in OpenSearch and vice versa.
- The `knn` query syntax differs between Elasticsearch 8.x and OpenSearch — verify before citing specifics.
- `dense_vector` with `index: true` for HNSW indexing requires Elasticsearch 8.0+ or OpenSearch 2.x. Older versions support `dense_vector` but only for exact script_score queries.
- HNSW parameter names: in Elasticsearch, the query parameter is `num_candidates`, not `ef`. The index parameters `m` and `ef_construction` are correct for both.
- `terms` aggregation returns **approximate** counts for large cardinality fields — not exact. Use `composite` aggregation for exact counts.
- **Inverted index does not support** numeric range queries efficiently without doc values — range queries on numeric fields use doc values (BKD trees), not the inverted index.
- Forcemerge is dangerous on active write indices — it can cause `OutOfMemoryError` during segment merging on large indices.
- Typesense is **not a distributed system** in the same sense as Elasticsearch — it uses Raft for cluster consensus but is designed for smaller corpora. Verify Typesense's current scale limits.
