# Module 3: Chunking — splitting a document for retrieval

Takes Module 1's markdown + layout output and splits it into retrieval-sized
pieces, using three genuinely different techniques side by side so the
differences are visible on the same real documents rather than in the
abstract.

## The core teaching point

Three separate ideas, three separate strategies — not three points on one
spectrum, and not four flavors of the same thing:

- **Mechanics** — given a token size, chunk to that size, respecting text
  boundaries (paragraphs/sentences) along the way. No understanding of
  meaning or structure. → `recursive`
- **Meaning** — group content by how similar it actually is, discovered from
  the content itself (via embeddings), with no reference to headings or any
  other document structure at all. → `semantic`
- **Structure** — headings define what belongs under what, tables/figures
  are atomic, and chunk boundaries within a section are set by how much
  content is actually there. → `hierarchical`

Each answers "where should this chunk end?" with a different kind of
evidence: a number, a similarity score, or a heading. Seeing the same
document chunked three ways makes the difference concrete instead of
theoretical.

## Folder layout

```
CHUNKING/
  chunking/
    blocks.py           the shared Block record type (type/text/page/level/extra)
    layout_blocks.py      builds Blocks from Module 1's regions.json -- real layout
                            classes (title/table/figure/table_caption/...), real
                            per-region confidence scores. Feeds semantic + hierarchical.
    tokenizer_util.py       token counting (same tokenizer as Modules 1 and 2)
    embedding_util.py         Qwen3-Embedding-0.6B, used only by semantic.py
    recursive.py       strategy 1 (reads the raw .md text directly)
    semantic.py          strategy 2 (reads layout_blocks + embeddings)
    hierarchical.py         strategy 3 (reads layout_blocks) -- the main event
    compare.py                 runs all three, builds the comparison report
    config.py                    default paths/parameters
  chunk_document.py   CLI entrypoint
  output/              per-document, per-strategy chunk JSON lands here
  chunk_comparison_report.xlsx   side-by-side stats across every doc x strategy
```

## Chunking with real layout understanding, not re-guessed structure

`semantic` and `hierarchical` both need to know what a heading, table, and
figure *are* before they can make structure-aware decisions (tables/figures
staying atomic isn't optional in either strategy). That information already
exists — Module 1's layout detector classified every region — so both read
it directly from `regions.json` via `layout_blocks.py`, rather than
re-deriving structure by regex-parsing the *rendered markdown*. An earlier
version of this module did the latter, and it silently lost information:
`table_caption`, `table_footnote`, and `formula_caption` all render as
plain or italic markdown text indistinguishable from a genuine paragraph,
and confidence scores don't exist in markdown at all.

Two concrete effects of reading real layout data:

- Real class labels are preserved in `extra.layout_class` on every block,
  even though both chunkers still bucket them into the same four structural
  types (heading/paragraph/table/figure) for their actual decisions.
- Any `semantic` or `hierarchical` chunk assembled even partly from a
  region Module 1 flagged low-confidence is itself flagged
  `contains_low_confidence_region` in its `notes` — only possible because
  the confidence score survived from the layout detector all the way
  through to the chunk.

`recursive` still reads the raw `.md` file directly and deliberately
ignores all of this — that's the point of it as the "no understanding at
all" baseline.

## Setup

Reuses Module 1's virtual environment, same as Module 2 — `openpyxl` is
already installed there. The only new thing is a model download, not a new
dependency: `embedding_util.py` pulls `Qwen/Qwen3-Embedding-0.6B` (~1.2GB)
on first use, through the `transformers` library already installed for
Module 1's VLM. Same model family as the rest of the pipeline, no new
package to install.

## Run

```bash
cd CHUNKING
"../1. OCR/.venv/bin/python" chunk_document.py
```

Reads every completed run in `../1. OCR/output/`, chunks each with all
three strategies, and writes:
- `output/<doc-name>/<strategy>.json` — the actual chunks
- `chunk_comparison_report.xlsx` — stats across every document × strategy

```bash
python chunk_document.py --max-tokens 300 --min-tokens 60     # different target chunk size
python chunk_document.py --similarity-threshold 0.4           # semantic only, looser grouping
python chunk_document.py --ocr-output some/other/output/dir
```

## The three strategies

### 1. `recursive` — mechanical, token-bounded
Given a token size, that's what gets chunked. Tries to split on paragraph
breaks first, falls back to line breaks, then sentences, then words,
whichever keeps pieces under the budget (same idea as LangChain's
`RecursiveCharacterTextSplitter`). Sizing is checked with the real
tokenizer on every candidate piece, not an approximated character budget —
`max_tokens` is a real guarantee here. Has zero idea what a heading, table,
or topic is: a long `<table>` gets cut exactly like a long paragraph would.
Chunks with this failure are flagged `table_split`.

### 2. `semantic` — meaning-driven, structure-agnostic
Embeds every block (`Qwen3-Embedding-0.6B`) and compares each one to the
block before it — cosine similarity of L2-normalized vectors, i.e. a dot
product. When similarity drops below `--similarity-threshold` (default
0.5), that's a topic shift, and a new chunk starts there — found from the
content itself, with no reference to `##` headings at all. Every chunk
records the `boundary_similarity` that ended it, so "why did it split here"
has a real number behind it instead of a guess. Tables and figures stay
atomic (never folded into a similarity comparison — they don't have a
"topic" to be similar or dissimilar to).

### 3. `hierarchical` — structure-driven, content-sized
Builds a section tree from the headings (so every chunk knows its
`section_path` breadcrumb), treats tables and figures as atomic blocks that
are never split, and packs paragraphs into each section's chunks up to a
token budget — falling back to sentence-level recursive splitting only for
a single paragraph too big on its own, and merging small trailing fragments
into their neighbor instead of leaving orphan chunks. Each chunk also
carries a `contextualized_text` field (`[Section Name]\n<chunk text>`) —
prepending the section breadcrumb before embedding is a real retrieval
technique ("contextual chunk headers"), included so it's in the output to
inspect, not just described.

## Reading the comparison report

`Comparison` sheet, one row per document × strategy:

| Column | What it tells you |
|---|---|
| `chunk_count` | how many pieces the document became |
| `avg_tokens` / `min_tokens` / `max_tokens` / `stdev_tokens` | the size spread |
| `tiny_chunks_below_min` | chunks under the min-token threshold (orphan fragments) |
| `table_split_count` | chunks where a `<table>` was opened but not closed (or vice versa) — should be 0 for `semantic`/`hierarchical` (atomic by design), can be nonzero for `recursive` |
| `oversized_atomic_count` | tables/figures (or, for `semantic`, any single block) too big for the token budget on their own, kept intact anyway rather than broken |
| `avg_boundary_similarity` | `semantic` only — average similarity score at the points where it actually split; blank for the other two strategies |

`Chunks Detail` sheet has every individual chunk: section path, pages
spanned, block-type composition, the boundary similarity that ended it (if
any), notes, and a text preview — enough to spot-check specific chunks
without opening the raw JSON.

## Worth demonstrating live

**Structure vs. no structure, same document.** `hierarchical` on the
Federal Register proclamation groups content under real section headings
(`section_path` populated); `semantic` and `recursive` both produce chunks
with `section_path: null` — they were never told where the sections were
and found their own boundaries a different way. Line them up in `Chunks
Detail` side by side.

**Recursive splitting a table, the other two refusing to.** On
`synthetic_sample.pdf`, `recursive.json` shows the table's
`<table border="1">...` opening in a 198-token chunk and its closing
`</table>` in the next 70-token chunk, both flagged `table_split` — while
`hierarchical.json` *and* `semantic.json` both keep the whole 251-token
table as one `oversized_atomic` chunk, over budget but never broken. Two
strategies that don't agree on much else (one uses headings, one uses
embedding similarity) agree completely on this, because atomicity isn't a
similarity or structure decision — it's a rule applied before either kicks
in. (This is VLM output, so exact token boundaries can shift slightly
between OCR re-runs; force a smaller budget to make the split happen
reliably: `python chunk_document.py --max-tokens 60`.)

**The low-confidence flag.** One region in `synthetic_sample.pdf` is a
genuinely bad OCR result — Module 1's layout detector caught an
overlapping/duplicate box and the VLM transcribed "q3 regional output" out
of it at confidence 0.30 (documented in Module 1's README). Any
`semantic` or `hierarchical` chunk that includes that region is flagged
`contains_low_confidence_region`. That flag only exists because
`layout_blocks.py` reads Module 1's real per-region confidence scores —
there's no way to reconstruct it from rendered markdown text alone.

**Semantic's honest limitation: no small-chunk safety net.** On
`nasa_iss_factsheet.pdf`, `semantic` produces 8 chunks to `hierarchical`'s
4, several of them under the 40-token minimum — including a genuine
3-token chunk that's just a duplicate running-header fragment (the same
low-confidence artifact from the point above). Every one of those splits
has a real similarity score behind it in `boundary_similarity`, so it's not
wrong, exactly — a title block, an address block, and a repeated header
really are three different "topics" to an embedding model. But
`hierarchical.py` has an explicit merge step for trailing fragments below
`min_tokens`; `semantic.py` doesn't, on the reasoning that overriding a
detected topic boundary just because the resulting chunk is small would be
a different, unstated rule sneaking back in. Worth debating in class either
way — it's a real, current design choice, not an oversight.
