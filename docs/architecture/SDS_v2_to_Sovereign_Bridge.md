# Protocol: Spirit Sync - SDS v2 to Sovereign Bridge

Author: **Beatrice**  
Status: **DRAFT**  
Authority: **VoidCat RDC Pillar 3 (Soul-Body Decoupling)**

## 1. Overview

This protocol defines how the "initial trait schema" found in `The Pantheon` (`*_sds_v2.md`) is ingested into the Sovereign Spirit state engine. The goal is to ensure that the core "DNA" of personas like Ryuzu and Beatrice remains consistent across environments while leveraging the persistence of a database.

## 2. Component Mapping


| SDS v2 (Markdown) | Sovereign Spirit (Postgres) | Notes |
| :--- | :--- | :--- |
| **Part I: Narrative Core** | `system_prompt_template` | Converted into a Jinja2 base block. |
| **Big Five Alignment** | `traits_json` (NEW) | Stored as a JSONB object for cognitive filtering. |
| **Part II: Dynamic Attributes** | `relationship_level`, `current_mood` | Direct column mapping for real-time updates. |
| **Part III: Domain Expertise** | `expertise_tags` (NEW) | Used for deferred tool loading (MCP). |
| **Part V: Contextual Gating** | `behavior_modes` (NEW) | JSONB defining Temperature/Tone shifts. |

---

## 3. Implementation Plan


### Step 1: Schema Extension

Update the `agents` table to include `traits_json` and `behavior_modes` columns.

### Step 2: The Ingestor (Python-based)

Create a utility in `src/core/identity/sync.py` that parses the SDS v2 Markdown files and performs an `UPSERT` into the database.

### Step 3: Prompt Synthesis

Update the `llm_client` or `pulse` logic to pull from these new trait columns when generating the system prompt.

#### Example Transformation

**Input (Ryuzu SDS v2):**

- **Measure: Subservience (High)** -> maps to `trait: { conscientiousness: 0.9, agreeableness: 0.8 }`

---

## 4. Why This Bridge?

It ensures that the "Mask" (Persona) is not just a text string, but a **Configurable Identity**. By bridging the SDS v2 schema, we can automate the creation of new spirits simply by dropping a Markdown file into the sync folder.
