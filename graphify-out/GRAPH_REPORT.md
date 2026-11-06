# Graph Report - AutoKetik  (2026-11-06)

## Corpus Check
- 29 files · ~20,452 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 289 nodes · 542 edges · 26 communities (15 shown, 11 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 20 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4a06cb57`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]

## God Nodes (most connected - your core abstractions)
1. `AutoKetikApp` - 52 edges
2. `Typist` - 28 edges
3. `main()` - 18 edges
4. `GUITypist` - 17 edges
5. `Config` - 13 edges
6. `SegmentedButton` - 13 edges
7. `DocParser` - 13 edges
8. `AutoKetik` - 13 edges
9. `StopTyping` - 12 edges
10. `What You Must Do When Invoked` - 12 edges

## Surprising Connections (you probably didn't know these)
- `GUITypist` --uses--> `StopTyping`  [INFERRED]
  autoketik/engine.py → autoketik/config.py
- `Typist` --uses--> `StopTyping`  [INFERRED]
  autoketik/engine.py → autoketik/config.py
- `AutoKetikApp` --uses--> `StopTyping`  [INFERRED]
  autoketik/gui.py → autoketik/config.py
- `SegmentedButton` --uses--> `StopTyping`  [INFERRED]
  autoketik/gui.py → autoketik/config.py
- `GUITypist` --uses--> `Config`  [INFERRED]
  autoketik/engine.py → autoketik/config.py

## Import Cycles
- 1-file cycle: `AutoKetik.py -> AutoKetik.py`

## Communities (26 total, 11 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (13): AutoKetikApp, _bold(), Shortcut set font bold (+ukuran opsional) ke widget., Tombol pilihan eksklusif bergaya segmented -- modern pill style., Helper: buat baris label + slider + nilai. Simpan widget sebagai attr self., Create numeric fields with a readable menu for constant or random mode., Set semua nilai sekaligus tanpa memicu _on_wpm_change (blockSignals)., SegmentedButton (+5 more)

### Community 1 - "Community 1"
Cohesion: 0.17
Nodes (8): GUITypist, 0..1. 1 = paling cepat, 0 = paling lambat. Halus (cosinus)., Variasi acak kecil antar kata (momentum), di atas gelombang WPM., Pilih sisa teks (beberapa kata) yang terus diketik sebelum sadar ada typo., Simulasi pengetikan ala manusia dengan kecepatan bergelombang,     jeda berpiki, Pertahankan teks setelah typo jika bagian yang sudah diketik cukup panjang., Subclass Typist dengan hook progress, status, dan animasi pengetikan real-time u, Typist

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (16): background, scripts, browser_specific_settings, gecko, content_scripts, description, id, strict_min_version (+8 more)

### Community 3 - "Community 3"
Cohesion: 0.39
Nodes (6): insert(), neighbors, rand(), run(), sleep(), typoAt()

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (46): argparse, main(), print_preview(), autoketik.cli - Antarmuka baris perintah (CLI) untuk AutoKetik., Block, Config, autoketik.config - Konfigurasi, struktur data dasar, dan konstanta keyboard., require_pynput() (+38 more)

### Community 6 - "Community 6"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 7 - "Community 7"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 8 - "Community 8"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 9 - "Community 9"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 10 - "Community 10"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (18): Typing Into Active Window, Alur penggunaan, AutoKetik, Catatan, Public Google Docs Viewer Access, HTML Format Preservation, Mengambil teks dari clipboard, Mengambil teks dari Google Docs (+10 more)

### Community 23 - "Community 23"
Cohesion: 0.40
Nodes (4): delayEl, statusEl, textEl, wpmEl

### Community 24 - "Community 24"
Cohesion: 0.83
Nodes (4): $(), ids, send(), status()

## Knowledge Gaps
- **85 isolated node(s):** `neighbors`, `manifest_version`, `name`, `version`, `description` (+80 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AutoKetikApp` connect `Community 0` to `Community 1`, `Community 5`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Why does `Typist` connect `Community 1` to `Community 5`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `GUITypist` connect `Community 1` to `Community 0`, `Community 5`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `AutoKetikApp` (e.g. with `Config` and `StopTyping`) actually correct?**
  _`AutoKetikApp` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Typist` (e.g. with `Config` and `StopTyping`) actually correct?**
  _`Typist` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `main()` (e.g. with `StopTyping` and `.run()`) actually correct?**
  _`main()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `GUITypist` (e.g. with `Config` and `StopTyping`) actually correct?**
  _`GUITypist` has 5 INFERRED edges - model-reasoned connections that need verification._