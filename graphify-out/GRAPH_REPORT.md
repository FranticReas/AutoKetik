# Graph Report - AutoKetik  (2026-10-29)

## Corpus Check
- Corpus is ~9,298 words - fits in a single context window. You may not need a graph.

## Summary
- 176 nodes · 384 edges · 16 communities (3 shown, 13 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 14 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Main GUI Application
- Typing Engine
- Document Parsing
- GUI Controls
- Command Line Interface
- Configuration
- Document Action Planning
- GUI Entry Point
- Google Docs Extraction
- GUI Components
- Typing Engine Core
- Product Features
- Keyboard Input Dependency
- Clipboard Dependency
- HTTP Dependency
- GUI Toolkit Dependency

## God Nodes (most connected - your core abstractions)
1. `AutoKetikApp` - 50 edges
2. `Typist` - 27 edges
3. `main()` - 19 edges
4. `GUITypist` - 13 edges
5. `DocParser` - 13 edges
6. `plan()` - 11 edges
7. `Config` - 10 edges
8. `SegmentedButton` - 10 edges
9. `StopTyping` - 9 edges
10. `parse_html()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `main()` --uses--> `StopTyping`  [INFERRED]
  autoketik/cli.py → autoketik/config.py
- `Typist` --uses--> `StopTyping`  [INFERRED]
  autoketik/engine.py → autoketik/config.py
- `AutoKetikApp` --uses--> `StopTyping`  [INFERRED]
  autoketik/gui.py → autoketik/config.py
- `Typist` --uses--> `Config`  [INFERRED]
  autoketik/engine.py → autoketik/config.py
- `AutoKetikApp` --uses--> `Config`  [INFERRED]
  autoketik/gui.py → autoketik/config.py

## Import Cycles
- None detected.

## Communities (16 total, 13 thin omitted)

### Community 2 - "Document Parsing"
Cohesion: 0.21
Nodes (5): Block, Run, DocParser, _line(), _pt()

### Community 8 - "Google Docs Extraction"
Cohesion: 0.33
Nodes (5): fetch_gdoc(), normalize(), parse_css(), parse_html(), parse_range()

### Community 11 - "Product Features"
Cohesion: 0.33
Nodes (6): Typing Into Active Window, AutoKetik, Public Google Docs Viewer Access, HTML Format Preservation, Preview Mode, Text Input Sources

## Knowledge Gaps
- **11 isolated node(s):** `Typing Into Active Window`, `HTML Format Preservation`, `Public Google Docs Viewer Access`, `Preview Mode`, `pynput Dependency` (+6 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 60 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AutoKetikApp` connect `Main GUI Application` to `Typing Engine`, `GUI Controls`, `Configuration`, `GUI Entry Point`, `Google Docs Extraction`, `GUI Components`, `Typing Engine Core`?**
  _High betweenness centrality (0.405) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `AutoKetikApp` (e.g. with `Config` and `StopTyping`) actually correct?**
  _`AutoKetikApp` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Typing Into Active Window`, `HTML Format Preservation`, `Public Google Docs Viewer Access` to the rest of the system?**
  _11 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Main GUI Application` be split into smaller, more focused modules?**
  _Cohesion score 0.08205128205128205 - nodes in this community are weakly interconnected._
- **Why does `Typist` connect `Typing Engine` to `Google Docs Extraction`, `Typing Engine Core`, `Command Line Interface`, `Configuration`?**
  _High betweenness centrality (0.196) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Typist` (e.g. with `Config` and `StopTyping`) actually correct?**
  _`Typist` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `Typing Engine` be split into smaller, more focused modules?**
  _Cohesion score 0.14583333333333334 - nodes in this community are weakly interconnected._