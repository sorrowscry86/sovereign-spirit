# [CMC-001] The Causal Memory Core

> [!NOTE]
> **The "Hook":** A narrative-based memory system that links events via causality rather than just semantic similarity.

## Metadata
- **ID:** CMC-001
- **Title:** The Causal Memory Core
- **Paradigm:** Graph, Temporal, Event-Driven
- **Integration Cost:** Medium (Wrapper)
- **Status:** Operational

## Problem Domain
Traditional semantic search (vector-only) lacks context regarding "Why" and "When" in a narrative sequence. Semantic similarity might link "The cat sat on the mat" and "The dog sat on the rug," but it fails to link "I found a key" with "I opened the lock" if they aren't semantically close but are causally linked.

## The Paradigm
The Causal Memory Core thinks in **Causal Chains**. 
1. **Nodes:** Events, Facts, or Subjective Observations.
2. **Edges:** `CAUSES`, `PRECEDES`, `REFUTES`, or `ELABORATES`.

By traversing these edges, an agent can reconstruct the logical flow of a multi-day operation without losing the "thread."

## Killer App
**Long-term Narrative Persistence:** Ideal for agents acting as personal historians or complex project managers where the sequence of decisions is as important as the decisions themselves.

---
*Curator: Beatrice | Architect: Wykeve*
