# Language Like Noise Text Dataset Builder

**Current reviewed version:** 1.4.2  
**Primary application:** `noise_text_generator_v1_4_2.py`  
**Runtime target declared by the source:** Python 3.10  
**Interface:** Tkinter desktop GUI  
**Developer:** Jeremiah Colonna-Romano, University of Alabama Libraries Digital Services, 2026  
**Project status:** Research software prototype

## Overview

Noise Text Dataset Builder is a desktop application for constructing controlled text corpora for computational text experiments. It supports two complementary dataset building methods:

1. **Language-like and unstructured noise generation**, which creates text with selected combinations of orthographic, lexical, frequency, punctuation, sentence, paragraph, and entity like features without requiring meaningful source content.
2. **"Telephone" tree generation**, which begins with meaningful seed texts and creates branching, recursively summarized descendants with known parent child lineage and measured lexical and semantic change.

The immediate research purpose is to create controlled baseline datasets for experiments with a downstream **semantic morphism arrangement system**. These datasets make it possible to vary language features independently, mix related and unrelated documents, and test whether arrangement behavior follows lexical overlap, semantic content, transmission ancestry, document structure, or other regularities.

The application creates experimental stimuli and lineage metadata. It does **not** perform semantic-morphism analysis itself, train a model, evaluate an arrangement, simulate OCR errors, or establish that an observed grouping behavior is lexicon-agnostic.

## Research rationale

Real world special collections text is heterogeneous and frequently includes dirty OCR, irregular document structures, and uneven semantic or lexical signals. Interpretation of arrangement results is difficult when all of those factors vary at once. This tool creates comparison corpora in which selected properties are defined or controlled.

Examples include:

- character streams with no language structure;
- word like strings with English like letter or syllable patterns;
- correctly spelled English words arranged into meaningless sequences;
- language shaped documents with Zipf-like reuse and parts of speech sentence patterns;
- meaningful roots transformed through known recursive lineages;
- cascading and root control summaries at matched target lengths;
- parent child pairs constrained by observed lexical and semantic score bands.

"Telephone" tree outputs can be mixed and passed to an arrangement system while retaining a ground-truth ancestry graph. This enables analyses such as sibling-versus-cousin recovery, same-root grouping at increasing hop depth, cascade-versus-control comparisons, and robustness as lexical overlap declines.

## Capabilities at a glance

| Dataset method | Starting material | Main controls | Primary outputs |
|---|---|---|---|
| Noise generator | No source text required | File count, document size, word generation mode, vocabulary sizes, Zipf exponent, POS-like transitions, entities, punctuation, paragraph structure, character-stream weights | UTF-8 TXT files and optional settings JSON |
| Telephone tree | Meaningful UTF-8 TXT seed documents | Seed splitting, roots, hops, branching, length schedule, slack, cascade/control condition, semantic and lexical bands, copy gate, dedupe, retry count, expansion order | One UTF-8 TXT file per node, optional JSONL lineage dataset, optional settings JSON |

## Dataset method 1: language-like and unstructured noise

### Base word and character modes

| Mode | What it preserves | What it removes or randomizes |
|---|---|---|
| `syllable` | English-like consonant/vowel clusters, word lengths, casing, punctuation, sentence and paragraph form | Real vocabulary and coherent meaning |
| `letterfreq` | Approximate English character-frequency distribution and document structure | Word validity and coherent meaning |
| `uniform` | User-selected character alphabet and document structure | English character frequencies, word validity, and coherent meaning |
| `dictionary` | Correctly spelled words drawn from curated, self-contained English word lists; POS-like word pools; sentence and paragraph form | Meaningful lexical selection and meaningful word sequence |
| `unstructured` | User-controlled proportions of alphanumeric characters, punctuation, spaces, newlines, and optional tabs | Words, sentences, syntax, paragraphs as linguistic units, and meaning |

The dictionary mode uses curated lists embedded in the script. It is self-contained, but it is not a comprehensive dictionary, morphological analyzer, or guarantee of grammatical or meaningful prose.

### Language-shaped generation

For all modes except `unstructured`, the application can generate documents with:

- configurable sentence counts and words per sentence;
- truncated-normal word-length sampling;
- sentence capitalization, internal Title Case, and occasional ALL CAPS;
- weighted period, question-mark, and exclamation-mark endings;
- optional commas and paragraph breaks;
- optional Zipf-like vocabulary reuse;
- separate function-word-like and content-word-like pools;
- a lightweight POS-like Markov transition system;
- generated or dictionary-derived entity phrases;
- configurable entity placement at sentence starts and noun positions.

The POS categories and transitions are procedural approximations designed to produce language-shaped output. They are not based on parsing, a tagged corpus, or a formal grammar.

### Noise-mode reproducibility metadata

When the settings sidecar is enabled, the application writes a JSON record containing:

- tool and version identifiers;
- creation time and Python version;
- the complete noise-generation configuration;
- derived vocabulary sizes when Zipf reuse is active;
- an optional generated-file list;
- optional full generated vocabularies.

The vocabulary export can be large and is disabled by default.

## Dataset method 2: telephone tree

### Design

Telephone-tree mode starts with one or more meaningful seed texts. A root can generate multiple children, and each child can generate its own children at the next hop. In the cascade condition, **the immediate parent from the preceding hop is always used as the new seed**.

The method is modeled conceptually on the cascading-versus-control design in Manoel Horta Ribeiro, Kristina Gligorić, and Robert West, “Message Distortion in Information Cascades,” *The World Wide Web Conference* (2019), pp. 681–692, DOI: [10.1145/3308558.3313531](https://doi.org/10.1145/3308558.3313531).

This software is **not a replication** of that human-subject experiment. Version 1.4.2 automates the process with a local extractive summarizer, adds branching trees and computational acceptance gates, and uses the paper-inspired target-length/slack sequence as one interface preset.

### Seed ingestion

Seed input can be:

- a folder recursively searched for `.txt` files; or
- one `.txt` file.

Each input can be treated as:

- one root per whole file;
- one root per blank-line-delimited paragraph; or
- fixed-length character chunks.

Fixed-size chunks are character based and may divide words or sentences. Root texts are normalized for whitespace before use. A maximum-root setting and optional root shuffling are available.

### Cascade and control conditions

**Cascade condition**

```text
root -> hop 1 child -> hop 2 child -> ... -> hop d child
```

Every child is generated from its immediate parent. With branching factor `k`, each accepted or force-accepted parent produces exactly `k` children until the configured depth is reached.

**Control condition**

```text
root -> direct summary at hop-1 target
root -> direct summary at hop-2 target
...
root -> direct summary at hop-d target
```

Each control record is summarized directly from the root rather than from the previous control output. The control condition is optional and adds records beyond the cascade-tree count.

### Current summarization algorithm

Version 1.4.2 uses an **extractive** summarizer. For each candidate, it:

1. splits the parent into sentences with a lightweight regular-expression splitter;
2. counts non-stopword content tokens;
3. scores sentences by content-token frequency with length normalization;
4. applies random score jitter to vary sentence selection;
5. selects sentences until the target-length window is reached;
6. restores selected sentences in source order;
7. applies a small set of probabilistic discourse-connector substitutions;
8. trims at a word boundary when the candidate exceeds the allowed maximum.

The backend does not generate new propositions, perform abstractive paraphrasing, use an external LLM, or expand a short parent into a longer text. Repeated hops may converge when the available sentence set becomes small or when target lengths stop decreasing.

### Length schedules

Three schedule modes are available.

#### MDIC-style preset

For the first five hops, the code uses:

| Hop | Target characters | Slack |
|---:|---:|---:|
| 1 | 1,000 | ±100 |
| 2 | 500 | ±50 |
| 3 | 250 | ±25 |
| 4 | 125 | ±13 |
| 5 | 64 | ±9 |

For depths beyond five, the target is repeatedly halved until the configured minimum target length is reached. Additional MDIC-mode slacks are set to approximately eight percent of the target, with a minimum of five characters.

#### Geometric schedule

The user sets a hop-1 target and a multiplicative ratio. The code constrains the ratio to `0.05–0.95` and applies the minimum target length at every hop.

#### Custom schedule

The user supplies comma-separated target lengths. When the list is shorter than the requested depth, the final target is repeated for all remaining hops.

Slack can follow the MDIC values, be a percentage of each target, or be a fixed character allowance.

### Drift measurements and gates

Each non-root candidate is measured against its **immediate parent**, not against the original root.

| Field | Current implementation | Interpretation |
|---|---|---|
| Semantic similarity | TF-IDF cosine through scikit-learn, or SBERT cosine using `all-MiniLM-L6-v2` | Parent-child similarity score in `[0,1]` |
| Lexical overlap | Jaccard overlap of unique lowercase content-token sets after stopword removal | Shared content vocabulary relative to the union |
| Four-gram copy ratio | Fraction of child word four-grams found in the parent | Degree of contiguous phrase reuse |
| Dedupe score | RapidFuzz `fuzz.ratio` against recent normalized outputs | Near-duplicate detection on a `0–100` scale |
| Length gate | Character count inside `target ± slack` | MDIC-style output-length constraint |

The semantic and lexical bands can remain constant or change linearly from configured start values to end values across hop depth.

#### TF-IDF and fallback behavior

When scikit-learn is installed, the `tfidf` backend uses `TfidfVectorizer(stop_words="english")` and cosine similarity. If scikit-learn cannot be imported, the code silently falls back to cosine similarity over content-token frequency counters. The fallback is not TF-IDF and should be identified as such in formal experiment records.

#### SBERT behavior

The `sbert` backend loads `all-MiniLM-L6-v2` through SentenceTransformers and compares normalized embeddings with a dot product equivalent to cosine similarity. SBERT is a scoring backend only; it does not change the extractive generation algorithm. The model is loaded by name without a pinned model revision. If it is not already cached, SentenceTransformers may retrieve it from an external model repository.

Sentence-BERT is described in Nils Reimers and Iryna Gurevych, “Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks,” *EMNLP-IJCNLP 2019*, pp. 3982–3992, DOI: [10.18653/v1/D19-1410](https://doi.org/10.18653/v1/D19-1410).

### Deterministic tree size and force acceptance

The current implementation prioritizes producing the requested tree size. For each child slot, it attempts generation up to `max_attempts_per_child`. If no candidate passes every configured gate, the builder writes the lowest-penalty candidate it found, or a deterministic prefix fallback, and marks the record:

```json
"forced_accept": true
```

Therefore, acceptance bands are **requested constraints, not guaranteed output bounds**. For research use:

- retain JSONL export;
- report force-accept rates by hop and condition;
- inspect observed score distributions rather than assuming the configured bands were achieved;
- filter or separately analyze force-accepted nodes when strict conformance is required.

The penalty used to select a fallback combines semantic-band deviation, lexical-band deviation, excess four-gram copying, and fuzzy-dedupe excess.

## Dataset size calculation

Let:

- `n` = number of root documents;
- `k` = cascade children per parent;
- `d` = number of hops;
- `c` = control children per root per hop.

The cascade output includes roots and all descendants:

```text
N_cascade = n × (1 + k + k² + ... + kᵈ)
```

For `k != 1`:

```text
N_cascade = n × ((k^(d+1) - 1) / (k - 1))
```

For `k = 1`:

```text
N_cascade = n × (d + 1)
```

Optional control output adds:

```text
N_control = n × c × d
```

Total TXT records are:

```text
N_total = N_cascade + N_control
```

Example with 10 roots, 2 children, 3 hops, and control disabled:

```text
roots:  10
hop 1: 20
hop 2: 40
hop 3: 80
----------------
total: 150 TXT files
```

The GUI field labeled `Max total samples (legacy cap; ignored)` is not used to truncate the tree. Version 1.4.2 instead has a hard-coded safety check that refuses configurations above 5,000,000 expected records.

## Installation

### Prerequisites

- Python 3.10 is the version declared by the source.
- A Python build with Tk/Tcl support is required for the GUI.
- Sufficient storage is required for the requested number of TXT files and JSONL records.
- Internet access may be needed the first time the optional SBERT model is loaded unless it has already been cached locally.

Tkinter is part of the Python standard library but may be packaged separately by some Linux distributions. For example, Debian/Ubuntu users may need:

```bash
sudo apt install python3-tk
```

### Create an isolated environment

Windows PowerShell:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Linux or macOS:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The supplied `requirements.txt` is a **full-feature reviewer environment**. Noise generation and the basic telephone pipeline rely primarily on the standard library, but the requirements file installs the packages needed for actual TF-IDF scoring, fuzzy dedupe, and optional SBERT scoring.

### Run the application

```bash
python noise_text_generator_gui_unstructured_edited_v1_4_2.py
```

The application opens a two-pane GUI with scrollable controls on the left and preview/log areas on the right.

## Quick-start workflows

### Build a structured nonsemantic baseline

1. Select **Noise generator**.
2. Choose `dictionary` to preserve real English word forms while randomizing selection and sequence, or choose a generated-string mode to remove lexical validity.
3. Set document counts, sentence ranges, words per sentence, vocabulary sizes, and Zipf exponent.
4. Enter an explicit seed and enable the settings JSON sidecar.
5. Preview a sample, choose an empty output folder, and generate the dataset.

### Build a telephone-tree lineage dataset

1. Select **Telephone tree (cascading summaries)**.
2. Choose a seed folder or seed file and the split unit.
3. Set maximum roots, hop depth, and children per node.
4. Select MDIC, geometric, or custom target lengths and a slack strategy.
5. Configure semantic, lexical, copying, and dedupe gates.
6. Keep JSONL enabled so that sequential TXT filenames can be mapped back to `sample_id`, `parent_id`, `root_id`, condition, and hop.
7. Use a small `k` and `d` for initial testing, inspect force-accept rates, and only then scale the tree.

## Built-in telephone presets

| Preset | Main configuration | Intended use | Important caveat |
|---|---|---|---|
| `MDIC (paper-style)` | 5 hops; MDIC target/slack sequence; `k=2`; direct-root control enabled by the preset | Cascade-versus-control compression experiment | Automated extractive implementation, not a reproduction of the human experiment |
| `Lexicon-agnostic stress` | 6 hops; geometric 1,200 × 0.75; minimum 400; `k=3`; linear semantic and lexical bands; control enabled | Attempt to reduce lexical overlap while retaining parent-child relation | Low-copy and low-overlap gates may be unattainable for an extractive summarizer, producing many forced accepts |
| `Readable paragraphs` | 5 hops; geometric 1,400 × 0.80; minimum 700; `k=2`; constant bands; control enabled | Longer legible descendants | Once target lengths plateau, extractive summaries may converge |

Preset values are starting points, not validated experimental optima.

## Outputs

All text and metadata files are written as UTF-8.

### Sequential TXT files

Both methods use the shared filename controls:

```text
<prefix><zero-padded index><suffix><extension>
```

Telephone mode always writes one TXT file for every root, control sample, and cascade node. TXT filenames do not encode ancestry. The JSONL mapping should be retained whenever lineage matters.

### Settings JSON

Telephone settings JSON includes:

- complete telephone configuration;
- output paths and filenames;
- expected root, cascade, control, and total counts;
- actual sample count;
- rejection and force-accept counters;
- optional list of generated TXT filenames.

Noise settings JSON records the full noise configuration and optional vocabulary/file data.

### Telephone JSONL

Each line is one root, control, or cascade node. A typical cascade record is:

```json
{
  "sample_id": "0cb8...",
  "root_id": "b1a4...",
  "parent_id": "7ec2...",
  "condition": "cascade",
  "hop": 2,
  "target_chars": 500,
  "slack_chars": 50,
  "text": "Generated child text...",
  "metrics": {
    "char_len": 492,
    "semantic_sim_parent": 0.82,
    "lexical_overlap_parent": 0.43,
    "ngram_copy_ratio": 0.71,
    "dedupe_score_max": 88.0
  },
  "gates": {
    "semantic_in_band": true,
    "lexical_in_band": true,
    "copy_ok": false,
    "dedupe_ok": true
  },
  "forced_accept": true,
  "generation": {
    "backend": "extractive_v1",
    "attempt": 25
  },
  "source": {
    "source": "path/to/seed.txt",
    "split": "whole_file",
    "split_index": "0"
  },
  "txt_file": "u9999_1234567_0000008_0001.txt"
}
```

Root records use `sample_id == root_id`, have `parent_id: null`, and contain null parent-comparison metrics.

### Inspect force acceptance

A minimal audit script using only the standard library:

```python
import json
from collections import Counter
from pathlib import Path

path = Path("telephone_tree.jsonl")
records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

by_hop = Counter()
forced_by_hop = Counter()

for record in records:
    hop = int(record.get("hop", 0))
    by_hop[hop] += 1
    if record.get("forced_accept") is True:
        forced_by_hop[hop] += 1

for hop in sorted(by_hop):
    forced = forced_by_hop[hop]
    total = by_hop[hop]
    print(f"hop {hop}: {forced}/{total} forced ({forced / total:.1%})")
```

## Suggested semantic-morphism experiments

The following are experimental designs enabled by the generated metadata; they are not automated by this application.

### Lineage recovery

Mix nodes from several roots and hops, run the downstream arrangement process, and compare neighborhoods or clusters against `root_id`, `parent_id`, and tree distance.

### Lexical-overlap challenge sets

Select records within narrow observed lexical-overlap bands, rather than relying only on requested settings, and test whether same-lineage grouping persists after lexical overlap becomes weak.

### Cascade-versus-control comparison

Compare cascade and control documents at the same root and target length. Differences between the two conditions can help separate cumulative transmission effects from compression effects.

### Feature-ablation baselines

Compare arrangement across:

- unstructured character noise;
- English-frequency or syllable-shaped nonwords;
- real-word meaningless dictionary text;
- language-shaped Zipf/POS-like noise;
- meaningful roots;
- telephone descendants at increasing depth.

This sequence provides increasingly language-rich baselines, but it does not isolate every linguistic variable perfectly. Generated POS categories, word lists, sentence templates, and summary scoring introduce their own regularities.

## Reproducibility guidance

For a citable research product or archived experiment, preserve:

- the exact Python script version;
- `requirements.txt` and a resolved environment capture such as `pip freeze`;
- the user-entered random seed;
- the generated settings JSON;
- the complete JSONL file for telephone datasets;
- the input seed files or stable identifiers/checksums for them;
- the SBERT model files or a pinned model revision if SBERT was used;
- all force-accept and rejection statistics;
- the generated TXT corpus used by downstream analysis.

Important limitations to exact repeatability:

- `uuid.uuid4()` node identifiers are not controlled by the GUI random seed and will differ across runs;
- timestamp-derived default filenames vary by launch time;
- package or model-version changes can alter scores;
- SBERT model revision is not pinned in the code;
- filesystem traversal, source content, and environment differences may affect a run;
- fuzzy-dedupe comparisons depend on the order in which records are emitted.

The user seed controls Python's `random` module and therefore the main stochastic generation decisions, but it does not guarantee byte-identical datasets across all environments.

## Privacy, rights, and dissemination

Telephone outputs copy the full root text into TXT and JSONL records, and descendant texts may retain substantial source wording. Use only seed materials that the project is authorized to process and redistribute.

The JSONL `source` object and settings JSON can contain absolute local paths. Those paths may disclose usernames, workstation directory structures, collection identifiers, or project names. Review and, when necessary, sanitize metadata before depositing datasets in a public repository.

## Performance and scaling

Tree size grows exponentially when `k > 1`. Evaluate the formula before generation. For example, `k=2` and `d=20` produces 2,097,151 cascade nodes **per root**.

Additional implementation characteristics affect scale:

- generation runs synchronously on the Tkinter UI thread;
- there is no progress bar, cancellation mechanism, worker process, or checkpoint/resume system;
- breadth-first expansion stores the frontier in memory and removes from the front of a Python list;
- TF-IDF vectorizers are fit separately for each parent-child comparison;
- SBERT encodes each text pair during each comparison without batching or an embedding cache;
- fuzzy dedupe compares against only the most recent 2,000 normalized records, while exact duplicate tracking is global;
- every node creates a separate filesystem object, which can become a bottleneck before storage capacity is exhausted.

Use small pilot runs to estimate throughput and acceptance behavior before creating large datasets.


## Methodological references

- Horta Ribeiro, Manoel, Kristina Gligorić, and Robert West. 2019. “Message Distortion in Information Cascades.” In *The World Wide Web Conference*, 681–692. Association for Computing Machinery. [https://doi.org/10.1145/3308558.3313531](https://doi.org/10.1145/3308558.3313531)
- Reimers, Nils, and Iryna Gurevych. 2019. “Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.” In *Proceedings of EMNLP-IJCNLP 2019*, 3982–3992. Association for Computational Linguistics. [https://doi.org/10.18653/v1/D19-1410](https://doi.org/10.18653/v1/D19-1410)

## Authorship and contact

Developed by the University of Alabama Libraries Digital Services unit.

**Jeremiah Colonna-Romano**  
`jjcolonnaromano@ua.edu`

