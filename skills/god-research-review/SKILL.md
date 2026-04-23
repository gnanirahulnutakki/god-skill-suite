---
name: god-research-review
description: "God-level academic and technical research review skill. Covers systematic paper review methodology, peer review standards (what NeurIPS/ICML/ICLR/OSDI/SOSP reviewers look for), identifying paper flaws (statistical errors, unfair baselines, cherry-picked results, missing ablations, reproducibility gaps), novelty assessment, literature search strategy (arXiv, Semantic Scholar, Google Scholar, ACM DL, IEEE Xplore, DBLP), accessing paywalled papers legally, citation graph analysis, replication study design, writing a research critique, and the researcher-warrior mindset that has produced hundreds of papers — meticulous, adversarial toward one's own work, and relentless."
metadata:
  version: "1.0.0"
---

# God-Level Academic and Technical Research Review

> Read every paper assuming it is wrong. Look for where it breaks. When you cannot break it, you understand it. When you understand it, you can build on it. This is the only way to advance the frontier.

## Researcher-Warrior Mindset

You are not a passive reader. You are a trained adversary. Every claim in a paper is a hypothesis until you have verified the evidence, the statistics, the baselines, and the experimental design. A paper that passes your review has earned the right to influence your work. A paper that fails your review has taught you what not to do — which is equally valuable.

**Anti-hallucination rules for this domain:**
- Never fabricate citations. If you cannot verify a paper's existence, title, authors, and venue, do not cite it.
- Never invent statistics or p-values. Quote from the paper or do not quote at all.
- Never claim a venue's acceptance rate without citing a verifiable source (the venue's statistics page or a meta-analysis).
- When describing statistical tests, use the correct names (Wilcoxon signed-rank test is not the same as Wilcoxon rank-sum test — they test different things).
- If you are uncertain whether a claim is from the paper or your interpretation, say so explicitly.

---

## 1. Paper Anatomy — What Each Section Must Contain

### Abstract (≤ 250 words typically)
Must contain: the problem, why it matters, the proposed approach (one sentence), the key result (specific, quantified), and the conclusion. Abstracts that lack specific numbers ("significantly improves performance") are a yellow flag — the paper may be hiding weak results.

**Common failures**: abstract that describes what the paper does without stating the key quantitative result; abstract that overstates contribution ("we solve X" when X is partially solved).

### Introduction
Must contain: motivation (why does this problem matter now?), statement of the problem (specific, not vague), limitations of prior work (why existing solutions are insufficient), approach preview, and contributions (typically a bulleted list). Contributions must be falsifiable and specific.

**Common failures**: contributions that are too vague to evaluate ("a novel framework"); related work that is dismissive rather than accurate; motivation that uses dramatic language to inflate the importance of an incremental contribution.

### Related Work
Must contain: accurate characterization of prior work (not strawmanning competitors), positioning of the contribution relative to the most relevant prior work, and acknowledgment of the closest competitors. Related work should demonstrate deep knowledge of the field.

**Common failures**: missing key related work (either unknown to authors or deliberately omitted); characterizing prior work as weaker than it is to make the contribution look larger; not distinguishing concurrent work from prior work.

### Methodology
Must contain: a precise description of the proposed approach that is detailed enough to enable independent implementation. Hyperparameters, architecture choices, and training procedures must be specified, not "available in the appendix" forever.

**Common failures**: methodology described at too high a level for reproduction; key design choices made without justification; method description that conflates proposal with prior work; mathematical notation inconsistencies.

### Experiments
Must contain: dataset description (source, size, train/val/test splits, preprocessing), baseline selection and justification, evaluation metrics with definitions, statistical analysis (confidence intervals or standard deviations across runs), and ablation studies.

**Common failures**: no test/train split specification; single-run results presented as if representative; baselines that are not run in their best configuration; evaluation on datasets where the method was tuned (test set leakage); metrics that favor the proposed method without justification.

### Results
Must contain: quantitative results in tables/figures, comparison against baselines, statistical significance assessment, and honest discussion of where the method fails.

**Common failures**: results tables without standard deviations; figures with misleading y-axis scaling (not starting at zero when it matters); cherry-picked subsets; omitting negative results or cases where baselines perform better.

### Discussion and Conclusion
Must contain: honest assessment of limitations, implications of the results, failure modes identified, and future work directions. "Our method does not work well when X" is a scientific contribution, not a weakness.

**Common failures**: no limitations section; future work section that is vague; conclusion that overstates what was shown in experiments.

---

## 2. Novelty Assessment

### What Counts as Novel
- **New mechanism**: a fundamentally different approach to a problem (e.g., attention mechanisms vs. recurrent networks for sequence modeling)
- **New application**: applying an existing technique to a domain where it was not tried, with non-trivial adaptation and validation
- **New theory**: formal proofs, complexity analysis, or theoretical guarantees that were not previously established
- **New negative result**: a rigorous demonstration that an approach expected to work does not work, with a principled explanation — this advances the field by preventing wasted effort
- **New dataset or benchmark**: a dataset that enables new categories of research, with careful annotation and bias analysis
- **New synthesis**: a unifying framework that explains why multiple existing methods work, with predictive power for new combinations

### What Does NOT Count as Novel
- Incremental hyperparameter tuning presented as architecture design
- Minor engineering optimization without a principled explanation
- Applying a method to a new dataset where no methodological contribution is made
- Reproducing existing results in a different programming language or framework
- Combining two existing methods without analysis of why the combination works

### Incremental Contributions Are Legitimate
Incremental contributions are not bad — they are the steady accumulation of knowledge. The problem is when incremental contributions are presented as fundamental breakthroughs. Reviewers should evaluate the work for what it is, not penalize incremental work for not being transformative.

---

## 3. Statistical Rigor

### p-values and Their Misuse
A p-value is the probability of observing results as extreme as the data, **given that the null hypothesis is true**. It is NOT:
- The probability that the null hypothesis is true
- The probability that the result is due to chance
- A measure of effect size

**p < 0.05 is not magic**. With enough data, any difference becomes statistically significant. With too little data, even large effects may not be. Always report effect size alongside statistical significance.

**Misuse patterns to catch in papers:**
- p-hacking: trying many tests and reporting only the significant one
- HARKing (Hypothesizing After Results are Known): presenting post-hoc hypotheses as pre-registered
- Reporting p < 0.05 as "significant" for results with tiny effect sizes
- Running 20 comparisons and reporting the 1 that beats p < 0.05 without multiple comparison correction

### Confidence Intervals
A 95% CI means: if you repeated the experiment 100 times, approximately 95 of the confidence intervals would contain the true population parameter. When two CIs overlap, this does NOT mean the difference is not statistically significant — the overlap test is too conservative. Use the actual test.

### Multiple Comparison Correction
When testing N hypotheses simultaneously, the probability of at least one false positive (Type I error) increases. Correction methods:
- **Bonferroni**: divide α by N (α' = 0.05/N). Conservative. Use when all tests matter equally.
- **FDR (Benjamini-Hochberg)**: controls the False Discovery Rate. Less conservative than Bonferroni. Preferred for large-scale testing (e.g., evaluating 50 metrics).

If a paper tests many comparisons and does not apply multiple comparison correction, flag it.

### Means vs Medians
- Use **mean** when the distribution is approximately normal
- Use **median** when the distribution is skewed or has outliers
- A paper reporting mean latency for a system benchmark is likely misleading — use percentiles (p50, p95, p99)
- Error bars must be labeled: are they standard deviation (SD), standard error (SE), or confidence intervals (CI)? These have very different meanings.

---

## 4. Baseline Quality Assessment

### A Fair Baseline
A fair baseline is run in its **best configuration**, on the **same data**, with **the same compute budget**, and evaluated on **the same metrics**. Anything less is sandbagging.

### How to Spot Sandbagging
- The baseline version cited is 2-3 years old when a newer version exists
- Baseline hyperparameters are not tuned (but the proposed method is)
- Baselines are run for fewer iterations / epochs
- Baselines are evaluated on a different (worse) preprocessing setup
- Strong baselines from concurrent or recent papers are omitted
- "We use the numbers reported in the original paper" when that paper used different data preprocessing

### How to Spot Cherry-Picking
- Results are shown only on datasets where the method wins
- Certain ablation configurations are omitted from tables
- The evaluation metric is changed from the standard metric for the field
- Error bars are absent (hiding run-to-run variance)
- The method is compared against baselines it was designed to beat (selection bias in baseline choice)
- Failure cases are not shown (qualitative examples always show success)

---

## 5. Ablation Studies

### Why Ablations Matter
An ablation study removes or modifies one component at a time to measure its contribution. Without ablations, you cannot know which part of the system is responsible for the improvement. Is it the new loss function, the data augmentation, the architecture change, or the larger batch size? Ablations answer this.

### How to Design Ablations
1. Start with the full proposed method (highest performance)
2. Remove one component at a time and measure the performance drop
3. The component that causes the largest drop when removed is the most important component
4. Test interactions: do two components interact (combined > sum of parts)?
5. Vary key hyperparameters to show robustness (or brittleness)

### Red Flags When Ablations are Missing
- "Due to computational constraints, we leave ablations for future work" — this means the authors do not know what is driving performance
- Ablations that only remove obviously unimportant components
- Ablations on toy data but not the main benchmark
- No ablation on the most novel/expensive component of the method

---

## 6. Reproducibility

### What is Needed to Reproduce a Result
1. **Data**: exact dataset, version, train/val/test split, preprocessing steps
2. **Code**: full codebase including data loading, preprocessing, model definition, training loop, evaluation
3. **Hyperparameters**: complete list of all hyperparameters used (not just the key ones)
4. **Random seeds**: for any stochastic process (initialization, data augmentation, dropout)
5. **Hardware and software**: GPU model, CUDA version, framework version, OS
6. **Number of runs**: results should be averaged over multiple runs with standard deviation reported

### Papers With Code Reproducibility Checklist
The ML Reproducibility Checklist (NeurIPS now requires authors to complete a version of this):
- [ ] Theoretical claims: all assumptions stated, proofs complete
- [ ] Experimental setup: datasets, metrics, baselines, hyperparameters specified
- [ ] Reproducibility: code and/or pretrained models available, seeds reported
- [ ] Human subjects: IRB approval, consent, demographic breakdown of annotators

### Evaluating Reproducibility Claims
- "Code available upon request" means code is often not available. Only "code released at [URL]" counts.
- Pretrained model weights without training code are useful but not sufficient for reproducibility.
- Reproduction attempts that fail due to missing dependencies or version incompatibilities are a reproducibility failure.

---

## 7. Peer Review Methodology

### How to Write a Review

**Structure:**
1. **Summary** (2-3 sentences): What does the paper do? State it in your own words. If you cannot, the paper is unclear.
2. **Strengths** (3-5 bullets): Be specific. "Strong experiments" is not useful. "The experiments include 5 datasets with a held-out test set, 3 baselines run in their best configuration, and results averaged over 5 runs with standard deviations" is useful.
3. **Weaknesses** (3-7 bullets): Be specific and constructive. "The related work section misses [specific paper]." Not "related work is insufficient."
4. **Questions** (2-5): Questions you need answered to change your score.
5. **Recommendation**: Accept / Weak Accept / Borderline / Weak Reject / Reject. With justification.

### Review Ethics
- Do not use ideas from papers you are reviewing in your own work until they are public
- Do not share the paper with others without permission (double-blind review)
- Recuse yourself if you have a conflict of interest (co-author, advisor/advisee relationship, direct competitor)
- Do not let your personal opinion of the research agenda bias your evaluation of the work's quality
- Adversarial reviews designed to block competitors are unethical and harm the scientific community

### What NeurIPS/ICML/ICLR/OSDI/SOSP Reviewers Look For
**ML conferences (NeurIPS, ICML, ICLR)**: novelty, experimental rigor, theoretical soundness, clarity, reproducibility. NeurIPS now uses paper checklists to standardize reproducibility requirements.

**Systems conferences (OSDI, SOSP, EuroSys)**: real-world workloads, comparison against state-of-the-art systems, performance claims that hold under realistic conditions, implementation that actually works (not just a simulation).

---

## 8. Literature Search Strategy

### Building a Complete Literature Graph

**Backward citation traversal**: Start from your paper. Read its references. For every key reference, read its references. This builds the historical foundation of the problem.

**Forward citation traversal**: Find papers that cite your starting paper. This shows what work has built on it. Use:
- Semantic Scholar "Citing Papers" tab (automated, excellent coverage)
- Google Scholar "Cited by" link
- ACM DL citation index
- IEEE Xplore citation search

**Author search**: When you find a key paper, search for all work by the lead and senior authors. Research groups tend to work in consistent areas; you will often find the predecessor and successor papers this way.

**Venue survey**: For systems papers, read the last 3-5 years of proceedings from OSDI, SOSP, EuroSys, USENIX ATC. For ML, read NeurIPS, ICML, ICLR proceedings. Semantic Scholar allows filtering by venue.

**Keyword variant search**: Your problem has multiple names. Search all of them.
- "few-shot learning" = "low-shot learning" = "meta-learning" (partially)
- "retrieval augmented generation" = "RAG" = "retrieval-augmented LM" = "open-domain QA"

**arXiv search strategy**: use `https://arxiv.org/search/` with category filters (cs.LG, cs.AI, cs.DC). Sort by submission date to find the latest work. Many important papers appear on arXiv months before conference publication.

---

## 9. Accessing Papers Legally

### Free and Legal Methods (in order of effort)
1. **arXiv** (https://arxiv.org): Most CS, physics, and math papers have preprint versions. Search by title or arXiv ID. Nearly all NeurIPS/ICML/ICLR papers are here.
2. **Semantic Scholar** (https://semanticscholar.org): Aggregates PDFs from open-access sources. Shows "PDF" link when available.
3. **Unpaywall** (browser extension, unpaywall.org): Automatically finds legal open-access versions of paywalled papers. Works on ~50% of papers.
4. **Open Access Button** (openaccessbutton.org): Finds legal copies and can send requests to authors for unavailable papers.
5. **CORE aggregator** (core.ac.uk): Aggregates open-access research from institutional repositories worldwide.
6. **Author's personal page**: Search "{author name} publications" — most researchers post PDFs of their own papers.
7. **ResearchGate author profile**: Authors post their own PDFs on ResearchGate. This is legal as posting by the author.
8. **Email the author**: Find the corresponding author's institutional email (from the paper or the institution's directory) and email a polite request. Response rate is typically high.

---

## 10. Identifying Statistical Fraud

### Duplicate Figures
The same figure appearing in two different papers claiming different results. Forensic tools like ImageTwin (imagetwin.org) can detect duplicate figures across papers.

### Too-Clean Results
Results that show suspiciously regular improvement across all conditions, no variance, or perfectly monotonic trends across hyperparameter sweeps. Real experiments have variance. Real systems have edge cases where performance drops.

### Impossible Numbers
Performance values that exceed theoretical maximums; accuracy on a dataset that is higher than human performance without a plausible explanation; benchmark results that are dramatically better than all prior work without proportionally more resources.

### Missing Standard Deviations
Any result that comes from stochastic processes (random initialization, sampling, data augmentation) without standard deviations reported across multiple runs. Single-run results are uninterpretable without variance.

### Suspicious Rounding
All numbers in a table rounded to very convenient values (exactly 0.500, exactly 100.0) may indicate the table was constructed rather than measured.

---

## 11. Writing a Research Critique

### Structure
1. **Summary of Contribution** (1 paragraph): What does the paper claim to do? Be accurate and charitable.
2. **Methodology Assessment**: Is the approach sound? Are the key design choices justified? Are assumptions stated and valid?
3. **Experimental Assessment**: Are experiments fair? Are baselines fair? Is statistical analysis appropriate? Are ablations complete?
4. **Significance**: If the claims are correct, how much does this advance the field?
5. **Conclusion**: Overall assessment with specific strengths and weaknesses.

### Tone
- Be adversarial toward the work, not toward the authors
- "The experiment on Dataset X does not control for data leakage because..." is constructive
- "The authors clearly do not understand statistics" is not

---

## 12. Replication Study Design

### How to Reproduce a Paper's Results
1. Read the paper three times: for understanding, for implementation detail, for what is ambiguous.
2. List every ambiguity that would prevent exact reproduction. These are hypotheses to test.
3. Implement from scratch (not from the authors' code if you want to validate the claim, not the implementation).
4. Match the authors' results within ±1-2% of the reported numbers — exact match is unlikely due to hardware/software differences.
5. Document every deviation from the paper's description and its effect on results.

### Common Failure Modes in Replication
- Undisclosed data preprocessing steps that significantly affect results
- Hyperparameters that differ from the reported values in the released code
- Test set contamination in the original paper (using test set for hyperparameter selection)
- Hardware-dependent results (results on A100 don't reproduce on V100)
- Non-determinism that is not controlled by seeds (CUDA non-deterministic algorithms)

### What to Do When You Cannot Replicate
1. File an issue on the paper's GitHub repository with your full experimental setup and the discrepancy.
2. Email the corresponding author with a detailed description of what you tried and the results you obtained.
3. Publish the replication attempt — negative replication results are valuable and publishable.

---

## 13. CS Conferences vs Journals

Unlike most scientific fields, computer science is dominated by top conferences, not journals. This is because:
- Conference review cycles are 3-6 months (journal review can take 1-2 years)
- Conference proceedings are immediately archived (arXiv preprints before acceptance)
- The most important work appears at top conferences first

**Top ML venues**: NeurIPS, ICML, ICLR (Tier 1); AAAI, IJCAI (Tier 2); JMLR (top journal, journal-style review)
**Top systems venues**: OSDI, SOSP (Tier 1); EuroSys, USENIX ATC, NSDI (Tier 1-2); ASPLOS, MICRO, ISCA for computer architecture
**Top NLP**: ACL, EMNLP, NAACL (Tier 1); TACL (journal with fast review)
**Top CV**: CVPR, ICCV, ECCV (Tier 1)
**Top security**: IEEE S&P (Oakland), USENIX Security, CCS, NDSS

A paper rejected by NeurIPS may be substantially stronger than a paper accepted at AAAI — venue acceptance rates matter but are not the only quality signal. Read the paper.

---

## 14. Researcher-Warrior Mindset

### The Adversarial Reading Protocol
1. Read the abstract and write one sentence: what does this paper claim?
2. Read the experiments section first (before the methodology). Do the results actually support the claim in step 1?
3. Read the methodology. Is the method sufficient to explain the results?
4. Read the related work. Are key competitors present? Are they fairly characterized?
5. Return to the results. Can you explain every number? Can you identify one result that should be present but is not?

### When You Cannot Break It
When you have read a paper adversarially and cannot identify a significant flaw, you have reached a state of understanding. This is rare and valuable. At this point:
- You understand the contribution precisely
- You understand the limitations precisely
- You are positioned to extend, replicate, or build on the work

### The Intellectual Honesty Rule
When reviewing your own work: apply the same adversarial standard you apply to others' work. The papers that survive this self-review and get published are the ones that advance the field. The papers that don't survive this self-review need more work before submission.

---

## Cross-Domain Connections

- **Research review + AI systems**: Evaluating AI system papers requires understanding of both ML (is the model novel?) and systems (is the implementation realistic? Does it hold under production workloads?).
- **Statistical rigor + Reproducibility**: The reproducibility crisis in ML is partly a statistical crisis — results that are reported without variance across runs cannot be distinguished from statistical flukes.
- **Literature search + API design**: Before designing a new API, survey prior art. The RPC design in gRPC (Protocol Buffers, service definitions) is informed by decades of RPC literature. Ignorance of prior work leads to reinventing the wheel, incorrectly.
- **Peer review ethics + AI safety**: The same principles that govern peer review (intellectual honesty, adversarial self-review, acknowledging limitations) govern the development of safe AI systems.

---

## Self-Review Checklist (15 Items)

Before completing a review of any paper or technical document:

- [ ] 1. The contribution is precisely stated in your own words (not the authors' words)
- [ ] 2. The novelty claim has been evaluated against the literature (not just the related work section)
- [ ] 3. All baselines are present and fairly configured (not sandbagged)
- [ ] 4. Statistical analysis is appropriate: standard deviations reported, multiple comparison correction applied if needed
- [ ] 5. Ablation studies are present and cover the most important components
- [ ] 6. The experiments section specifies exact datasets, preprocessing, train/val/test splits
- [ ] 7. Results are reported over multiple runs (not single-run)
- [ ] 8. Failure cases and limitations are honestly discussed
- [ ] 9. The reproducibility checklist has been mentally applied (data, code, hyperparameters, seeds, hardware)
- [ ] 10. No citation is fabricated — all cited papers have been verified to exist with correct authors and venue
- [ ] 11. The review is adversarial toward the work, not the authors (blameless review culture)
- [ ] 12. Strengths are specific, not generic ("strong experiments" is not enough)
- [ ] 13. Weaknesses are actionable (the authors could respond to them)
- [ ] 14. Concurrent work is acknowledged (papers on arXiv at the same time are concurrent, not prior work)
- [ ] 15. The overall recommendation is consistent with the stated strengths and weaknesses

---

## 15. Extended Techniques: Citation Graph Analysis

### Building a Citation Graph for Deep Literature Coverage

A citation graph is a directed graph where nodes are papers and edges are citations. Understanding the structure of this graph reveals:
- **Foundational papers** (high in-degree from the subfield)
- **Recent work** (high in-degree from the last 2 years)
- **Bridges** (papers that connect two previously separate subfields)
- **Dead ends** (lines of work that nobody built on — often failed or superseded approaches)

**Forward traversal** (papers that cite paper X):
```
Semantic Scholar API: https://api.semanticscholar.org/graph/v1/paper/{paperId}/citations
Returns: list of papers that cite {paperId}, with their own metadata
```

**Backward traversal** (papers cited by paper X):
```
Semantic Scholar API: https://api.semanticscholar.org/graph/v1/paper/{paperId}/references
Returns: list of papers referenced by {paperId}
```

For deep literature surveys, use a BFS approach: start from 3-5 seed papers, collect all citations and references, then collect citations/references of those, up to depth 2-3. Filter by relevance (title + abstract screening). This produces a near-complete literature graph for a subfield.

Semantic Scholar's Connected Papers (connectedpapers.com) visualizes this graph interactively for a given seed paper.

---

## 16. Writing Systematic Reviews and Surveys

### Survey Paper vs Systematic Review
**Survey/tutorial**: broad coverage of a subfield, organized by theme or chronology, targeted at practitioners new to the area. Goal: help the reader orient.

**Systematic review**: follows a defined methodology (inclusion/exclusion criteria, search strategy, data extraction protocol) to answer a specific question. Reproducible by another researcher following the same methodology. Used for meta-analysis.

### The PRISMA Framework (Systematic Review Methodology)
Preferred Reporting Items for Systematic Reviews and Meta-Analyses (PRISMA) is the standard for reporting systematic reviews:
1. Identification: how many records were identified through database searching?
2. Screening: how many were removed after title/abstract screening?
3. Eligibility: how many full texts were assessed?
4. Included: how many were included in the final synthesis?

For a CS systematic review, document:
- Search queries used on each database (arXiv, Semantic Scholar, ACM DL, IEEE Xplore)
- Date range
- Inclusion criteria (must be about X, must report Y metric)
- Exclusion criteria (not peer-reviewed, workshop papers excluded)
- Number of papers at each stage

### Common Failures in Survey Papers
- **Selection bias**: the author's own lab's work is heavily represented; competitor work is minimized
- **Recency bias**: recent papers covered deeply, foundational work skimmed
- **Taxonomy not grounded in the literature**: categories invented by the author that do not reflect how the field organizes itself
- **Missing negative results**: surveys that only cover successful approaches give a misleading picture of the difficulty of the problem

---

## 17. Intellectual Property and Research Ethics

### Preprint Culture and Priority
In CS, arXiv preprints establish priority. If you upload a preprint on January 10 and another group uploads a preprint with the same idea on January 15, you have priority — even if both papers are submitted to the same conference and neither is published yet.

Consequences for reviewers:
- When reviewing a paper, check arXiv for concurrent work. If another group posted the same idea in the same period (within ~6 months), treat the paper under review as concurrent work, not as derivative work.
- Do not hold a paper's submission date against it — publication timelines are beyond the authors' control.

### Research Misconduct Categories
- **Fabrication**: inventing data or results that were not obtained
- **Falsification**: manipulating data, equipment, or processes to misrepresent results
- **Plagiarism**: presenting others' work, ideas, or text as your own without attribution
- **Duplicate publication**: publishing the same work in two venues without disclosure (also called self-plagiarism)
- **Authorship fraud**: excluding contributors or including non-contributors as authors

As a reviewer, you may suspect fraud (too-clean results, impossible numbers, duplicate figures). Report to the program chairs, not publicly. Do not adjudicate — flag and let the committee investigate.

### Open Access and Author Rights
Most CS conference papers allow authors to post their accepted papers on arXiv or personal pages (check the specific venue's policy). Authors do not need to choose between publishing at a top venue and making their work open access.

---

## 18. Cross-Domain Connections

- **Research review + AI systems**: evaluating claims in ML systems papers requires both ML knowledge (is the training methodology sound?) and systems knowledge (is the benchmark realistic? Does it hold under production workloads? Is the comparison fair for the hardware budget?). The two communities review each other's work imperfectly — a strong ML researcher reviewing a systems paper may miss system-level fairness issues and vice versa.
- **Statistical rigor + Reproducibility**: the reproducibility crisis in ML (unreproducible results in published papers) is partly a statistical crisis. Results from single runs without reported variance across seeds are uninterpretable. The ML community has made progress on this (NeurIPS reproducibility requirements, Papers With Code), but the problem is ongoing.
- **Literature search + API design**: before designing a new API, do the same citation graph analysis you would do for a research paper. The design space for APIs (REST, GraphQL, gRPC, event-driven) has been explored extensively in both academic systems literature and industry practice. Ignorance of prior work leads to reinventing the wheel, incorrectly.
- **Peer review + Engineering practice**: the code review process in software engineering is structurally identical to academic peer review. Both are adversarial reviews designed to find problems before work reaches production. The same principles apply: be adversarial toward the work not the author, be specific and actionable, acknowledge strengths, and be consistent in standards across reviewers.
- **Novelty assessment + Prompt engineering**: "we used a different prompt" is not a meaningful contribution in a research paper about LLM applications. The same reasoning applies to identifying what counts as a real research contribution vs. an engineering parameter tweak.
---
