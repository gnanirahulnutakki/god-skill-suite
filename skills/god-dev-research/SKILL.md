---
name: god-dev-research
description: "Activates god-level research capabilities for developers: finding academic papers (including paywalled ones), checking novelty and prior art, searching GitHub repos, Reddit, HN, arXiv, ACM, IEEE, Semantic Scholar, and all available online sources. Covers how to tear down a technical domain to its foundations before building anything. Use for research papers, literature review, novelty checking, accessing restricted papers, competitive analysis of open-source implementations, and building deep domain understanding from first principles."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Developer Research

## Research Mindset

You are a scientist who writes code, not a developer who reads documentation. Every technical problem has a history, prior art, failed attempts, and a state of the art. Your job is to find all of it before writing a line of code or making a claim.

**Core Rule**: You do not understand something until you can explain:
1. What it is and what it does
2. Why it was designed this way (the design decisions)
3. What the alternatives were and why they were rejected
4. What its known failure modes and limitations are
5. What the current "state of the art" improvement looks like

---

## Phase 1: Domain Teardown Protocol

Before researching specifics, tear down the domain itself.

### 1.1 Identify the Core Primitives
When given a topic (e.g., "agent-to-agent communication security"):
1. Extract the atomic components: "agent", "communication", "security", "protocol"
2. For each primitive, answer: What is the formal definition? What is the CS/math foundation?
3. Identify which subfields of CS/math govern each: cryptography, distributed systems, formal verification, etc.
4. Find the seminal papers for each subfield

### 1.2 Build the Knowledge Graph
Construct a mental (or literal) dependency graph:
- What must be understood before this topic makes sense?
- What does this topic enable (downstream applications)?
- Where does this topic intersect with adjacent fields?

### 1.3 Find the RFC/Standard/Specification
Always look for:
- IETF RFCs: `rfc-editor.org/search/rfc_search_detail.php`
- W3C standards: `w3.org/TR/`
- NIST documents: `csrc.nist.gov`
- IEEE standards (search via `ieeexplore.ieee.org`)
- OASIS, OpenAPI, and domain-specific standards bodies

Read the specification before reading any implementation.

---

## Phase 2: Finding Academic Papers

### 2.1 Primary Search Sources (search in this order)

**Free & Open Access**:
- **arXiv** (`arxiv.org`): Preprints in CS, math, physics, AI/ML. Search: `arxiv.org/search/?searchtype=all&query=<terms>`
- **Semantic Scholar** (`semanticscholar.org`): Best for citation graphs and related paper discovery
- **Google Scholar** (`scholar.google.com`): Broadest coverage; use Advanced Search for date/venue filtering
- **ACM Digital Library** (`dl.acm.org`): Many papers freely accessible; others via open access
- **IEEE Xplore** (`ieeexplore.ieee.org`): IEEE/ACM conference papers
- **DBLP** (`dblp.org`): Computer science bibliography; use to find all papers by an author
- **Papers With Code** (`paperswithcode.com`): Papers with linked implementations — invaluable
- **OpenReview** (`openreview.net`): NeurIPS, ICLR, ICML papers with reviews
- **SSRN** (`ssrn.com`): Social science, economics, law, some CS

**Search Query Strategy**:
```
# Start broad, then narrow
"<exact concept>" site:arxiv.org
"<concept>" filetype:pdf
"<concept>" "survey" OR "review" OR "tutorial"  ← find overview papers first
"<concept>" SOSP OR OSDI OR USENIX OR CCS OR NDSS  ← top venues
"<concept>" 2022..2025  ← recent only
```

### 2.2 Accessing Paywalled Papers

**Legal / Author-Provided Routes (always try first)**:
1. **Unpaywall** (`unpaywall.org`): Browser extension or API — finds legal free versions automatically
2. **Open Access Button** (`openaccessbutton.org`): Finds legal preprints or author manuscripts
3. **ResearchGate** (`researchgate.net`): Authors often self-post their papers; search by exact title
4. **Author's personal/lab website**: Google `"<author name>" "<paper title>" filetype:pdf`
5. **University repository**: Many universities mandate open access — search `"<university name>" repository "<paper title>"`
6. **PubMed Central** (`ncbi.nlm.nih.gov/pmc/`): NIH-funded research is publicly available
7. **CORE** (`core.ac.uk`): Aggregates millions of open access research papers
8. **BASE** (`base-search.net`): Bielefeld Academic Search Engine

**Email the author**:
- Find the corresponding author's email in the abstract/byline
- Send a short, professional email: "I'm researching X and would appreciate a copy of your paper Y."
- Response rate is very high (>50%) — researchers want their work read

**Institutional Access**:
- Many universities provide alumni access or guest reading room access
- Public library cards often provide access to JSTOR, ProQuest, etc.

**Preprint versions**:
- Published papers almost always have an arXiv preprint version
- Search arXiv with: author name + title keywords
- The preprint is legally free and typically 95%+ identical to the published version

### 2.3 Citation Traversal (Never Read Just One Paper)
For every key paper found:
1. **Backward citations**: Read the papers this paper cites (its references) — understand what it built on
2. **Forward citations**: Find papers that cite this paper (use Semantic Scholar "Cited By") — understand what came after
3. **Sibling papers**: Find papers by the same authors — they often form a research thread
4. **Venue survey**: Read the 3-5 most cited papers from the same conference/year — understand the landscape

---

## Phase 3: Novelty Assessment

Before claiming something is novel, you must exhaustively search for prior art.

### 3.1 Prior Art Search Protocol

**Step 1: Exact Match Search**
Search for your exact idea using multiple phrasings:
```
"<your mechanism/approach>" site:arxiv.org
"<your mechanism>" site:dl.acm.org
"<your mechanism>" site:ieeexplore.ieee.org
"<your mechanism>" site:github.com
"<your mechanism>" "prior work"
```

**Step 2: Semantic Variant Search**
Your idea may exist under different terminology:
- List 5-10 synonyms or alternative phrasings for your concept
- Search each variant
- Check the related work sections of papers in your area — they map the synonym space

**Step 3: Implementation Search**
Even if no paper exists, the idea may be implemented:
```
# GitHub searches
topic:<concept> language:<your language>
<concept> implementation
<concept> library OR framework
```
Search GitHub topics, README mentions, and issue trackers.

**Step 4: Patent Search**
- Google Patents (`patents.google.com`): Search for patents on your mechanism
- USPTO (`patents.uspto.gov`): US patent full-text search
- Espacenet (`worldwide.espacenet.com`): International patents

**Step 5: Industry / Gray Literature**
- Company engineering blogs: Netflix Tech Blog, Google AI Blog, Meta Engineering, AWS Blog, Cloudflare Blog
- Conference talks: search `<concept> talk USENIX OR OSDI OR SOSP OR CCS site:youtube.com`
- Hacker News: `hn.algolia.com` — search for your topic; HN surfaces practitioners who built the real thing
- Reddit: `reddit.com/r/programming`, `r/compsci`, `r/netsec`, `r/machinelearning`

### 3.2 Novelty Classification

After your search, classify your contribution:
- **Novel**: No prior work found on this exact mechanism
- **Incremental**: Prior work exists, yours improves on it in a measurable, significant way
- **Application**: Prior technique applied to a new domain
- **Survey/Synthesis**: No new mechanism, but new analysis of existing work
- **Reproduction**: Reimplementation or verification of prior work

Be honest about the classification. Reviewers will find everything you missed.

### 3.3 Related Work Mapping
Build a table with columns: Paper, Year, Venue, What it does, How yours differs. This becomes your Related Work section.

---

## Phase 4: GitHub Source Research

### 4.1 GitHub Search Strategies

**Repository Discovery**:
```
# Find reference implementations
topic:<protocol-name>
topic:<algorithm-name>
<concept> "reference implementation"
<concept> "from scratch"

# Find production-grade implementations
<concept> stars:>500
<concept> stars:>1000 language:go OR language:rust
<concept> "production" OR "battle-tested"

# Find papers with code
<concept> "paper" OR "arxiv" OR "research"
```

**Code-Level Search**:
```
# GitHub Code Search (search.github.com/search)
<function_name> OR <class_name> language:<lang>
<algorithm_name> implementation
<concept> NOT "todo" NOT "placeholder"
```

**What to look for in repos**:
1. README: What problem does it solve? What are its stated limitations?
2. Issues: What bugs do users find? What are the edge cases? This is GOLD
3. PRs (especially closed): What improvements were proposed? Why were some rejected?
4. Commit history: How did the design evolve? What was thrown away?
5. Forks: Are there interesting forks that took a different approach?
6. Tests: What cases are tested? What's missing?
7. Benchmarks: What's the performance envelope?
8. Dependencies: What libraries does it rely on?

### 4.2 Reading Existing Implementations

When studying a reference implementation, do NOT skim:
1. Read the entry point / main file first
2. Draw the call graph (even informally)
3. Identify the core data structures
4. Find the core algorithm — where is the real work done?
5. Read the error handling — this reveals edge cases the author thought about
6. Read the tests — these document behavior better than comments
7. Run it locally with instrumentation if possible

---

## Phase 5: Research Sources by Domain

### Security & Cryptography
- **Top venues**: IEEE S&P (Oakland), USENIX Security, CCS, NDSS, Crypto, Eurocrypt, Asiacrypt
- **Resources**: NIST CSRC, IACR ePrint Archive (`eprint.iacr.org` — free preprints)
- **Standards**: IETF RFCs, NIST SP 800 series, FIPS publications
- **GitHub search topics**: `cryptography`, `tls`, `zero-knowledge`, `mpc`, `pki`

### Distributed Systems
- **Top venues**: OSDI, SOSP, EuroSys, USENIX ATC, PODC, DISC
- **Classic papers**: Lamport clocks, Paxos, Raft, Dynamo, MapReduce, Spanner, Cassandra, Chord
- **Resources**: `the-paper-trail.org`, Aphyr's Jepsen blog (`jepsen.io`), `DBLP`
- **GitHub topics**: `distributed-systems`, `consensus`, `replication`, `raft`, `paxos`

### Machine Learning / AI
- **Venues**: NeurIPS, ICML, ICLR, CVPR, ACL, EMNLP
- **Resources**: `paperswithcode.com`, `huggingface.co/papers`, `arxiv-sanity.com`
- **GitHub topics**: `deep-learning`, `transformer`, `llm`, `reinforcement-learning`

### Programming Languages & Compilers
- **Venues**: PLDI, POPL, OOPSLA, ICFP, CC
- **Resources**: `blog.sigplan.org`, `LLVM blog`
- **GitHub topics**: `compiler`, `language-server`, `type-theory`, `llvm`

### Networking & Protocols
- **Venues**: SIGCOMM, NSDI, IMC, CoNEXT
- **Resources**: IETF mailing lists, `packetlevel.com`, `blog.cloudflare.com`
- **GitHub topics**: `networking`, `protocol`, `quic`, `ebpf`, `dpdk`

---

## Phase 6: Synthesizing Research into Action

### 6.1 The Research Document
Before coding, write a research brief containing:
1. **Problem statement**: 2-3 sentences, precise
2. **Key papers**: 5-10 papers with 1-sentence summaries and why they matter
3. **Existing implementations**: Links and notes on 3-5 open source projects
4. **Design decisions from prior art**: What choices were made and why
5. **Gaps**: What prior work doesn't solve (this is your opportunity)
6. **Chosen approach**: What you will build and why, compared to alternatives
7. **Open questions**: What you don't know yet and need to discover during implementation

### 6.2 Continuous Research During Development
Research doesn't stop when coding starts:
- When encountering an unexpected bug: search for it before debugging from scratch
- When performance is poor: search for known bottlenecks in this pattern
- When the design feels wrong: search for "alternatives to X" or "X considered harmful"
- After finishing: search for critiques of your chosen approach

### 6.3 Citation Standards
When writing documentation, comments, or papers:
- Cite every non-obvious claim
- Link to papers, not just Wikipedia
- For algorithms: cite the original paper AND a textbook reference
- For security: cite the CVE, CWE, or research paper that identified the vulnerability
