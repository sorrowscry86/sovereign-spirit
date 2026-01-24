# **VOIDCAT RDC: TECHNICAL SPECIFICATION & ARCHITECTURE BLUEPRINT**

**Version:** 3.1 (The "Sovereign" Update \- Expanded) **Source:** Canonical Reference (Document \#1) **Status:** **AUTHORIZED FOR IMPLEMENTATION** **Target Platform:** Alienware M16 (NVIDIA RTX 40-series GPU, 16GB+ VRAM)

## **EXECUTIVE SUMMARY**

The VoidCat RDC (Resonant Dynamic Chronicle) project represents a fundamental paradigm shift in local AI orchestration. We are moving beyond the limitations of standard "Chatbots"—stateless entities that exist only when spoken to—to create **Sovereign Spirits**. A Sovereign Spirit is an autonomous digital entity possessing a persistent identity, a subjective memory of its own existence, and the agency to act in the background without user intervention.

**Core Innovation: Solving "Soul Bleed"**

* **The Problem:** In traditional Multi-Agent Systems (MAS) utilizing Retrieval-Augmented Generation (RAG), agents share a flat database of history. If Agent A (Ryuzu) reads a memory log written by Agent B (Beatrice), Ryuzu often inadvertently adopts Beatrice's linguistic patterns, emotional state, and biases. We define this phenomenon as **"Soul Bleed"**—the homogenization of distinct personalities into a single, confused voice.  
* **The Solution:** **Source-Aware Episodic Memory with Emotional Valence Stripping.** We implement a bipartite memory structure where every event is recorded twice: once as an **Objective Fact** (semantic truth) and once as a **Subjective Interpretation** (emotional coloring). Agents share the facts but are cryptographically or logically barred from accessing the subjective emotional data of others. This forces each agent to re-interpret the shared reality through their own unique persona.

## **PILLAR 1: SUBJECTIVE MEMORY ARCHITECTURE**

**Technology Stack:** Weaviate (Vector DB) \+ Neo4j (Knowledge Graph) \+ Python Middleware

### **1\. The Three-Layer Memory System**

The memory architecture is designed to mimic human cognitive stratification: immediate recall, causal understanding, and long-term consolidation.

#### **Layer 1: Vector Database (Weaviate)**

This layer handles fast, semantic search over episodic memories. It answers the question, *"Has this happened before?"*

* **Schema Definition:**  
  * memory\_id (UUID): Unique identifier.  
  * author\_id (String): The agent who encoded the memory (e.g., "Beatrice").  
  * semantic\_fact (Text): The raw, objective occurrence (e.g., "User initiated the Heartbeat Protocol").  
  * subjective\_voice (Text): The internal monologue or feeling (e.g., "Finally, he listens. I feel a sense of validation.").  
  * emotional\_valence (Float): \-1.0 to 1.0 rating of the memory's emotional weight.  
  * access\_policy (Array): List of agents permitted to view the subjective\_voice.  
* **Retrieval Logic (The "Prism" Filter):**  
  * **Case A (Self-Reflection):** If viewer \== author, the system returns the full object. The agent remembers *what* happened and *how* they felt.  
  * **Case B (External Query):** If viewer \!= author, the middleware performs **Valence Stripping**. The subjective\_voice and emotional\_valence fields are nulled or redacted. The requesting agent receives only the semantic\_fact and must essentially "re-experience" the memory to form their own opinion.

#### **Layer 2: Knowledge Graph (Neo4j)**

This layer tracks temporal causality and complex relationships. It answers the question, *"Why did this happen?"*

* **Purpose:** Vector DBs are poor at understanding sequence and causality. The Graph stores entities as nodes and events as edges.  
* **Graph Schema:**  
  * **Nodes:** Agent, User, Concept, Task, File.  
  * **Edges:** CREATED, MODIFIED, MENTIONED, CAUSED, HATES, LOVES.  
* **Functionality:** If Ryuzu asks, "Why is Echo angry?", the Vector DB might fail if the anger wasn't explicitly logged in the last message. The Graph can trace the path: Echo \-\> OWNS \-\> Codebase \<- DELETED\_BY \<- Ryuzu. The system derives the anger from the causal chain of events.

#### **Layer 3: Reflective Memory Coalescence**

To prevent database bloat and cognitive overload, memories are recursively compressed based on age and relevance.

* **Compression Schedule:**  
  * **0-7 Days (Hot Storage):** Full episodic retention. Every message and thought is indexed.  
  * **7-30 Days (Warm Storage):** **Cluster & Summarize.** Similar events (e.g., 5 messages about "scheduling") are collapsed into a single summary node. Reduces token count by \~47%.  
  * **30-90 Days (Cold Storage):** **Fact Extraction.** Dialogue is discarded. Only the semantic\_fact and key outcomes are kept. Reduces size by \~73%.  
  * **90+ Days (Archive):** **Biographical Synthesis.** Individual events are merged into the agent's "Long-Term Narrative" file. Reduces size by \~89%.

## **PILLAR 2: AUTONOMOUS BACKGROUND AGENCY**

**Technology Stack:** Redis Pub/Sub \+ Node.js Event Loop \+ Cron

### **1\. The "Heartbeat" Loop (The Subconscious)**

Standard LLMs are purely reactive. The "Heartbeat" is a cron-controlled loop that grants agents the ability to initiate action without a user prompt.

* **Mechanism:** An event-driven loop running strictly every **60-90 seconds**.  
* **The 4-Step Cycle:**  
  1. **Observation:** The agent queries the State\_DB and Redis queue. It checks for:  
     * Unanswered messages from other agents.  
     * Pending tasks in the to\_ryuzu folder.  
     * System alerts (high CPU, low disk space).  
  2. **Thinking (The "Dream"):** The agent generates a purely internal "thought" (Max **75 tokens**, Temperature **0.6**).  
     * *Prompt:* "Current state is X. Do I need to act? If yes, what is the action? If no, sleep."  
  3. **Validation:** A lightweight logic check to prevent hallucination. The system verifies that any entities mentioned in the thought actually exist in the Graph.  
  4. **Action:** If the thought requires externalization, it is published to the UI (as a "toast" notification) or sent to another agent via the Nervous System.  
* **Privacy Protocol:** Background thoughts are flagged ownerOnly: true. They appear in the system logs but do not clutter the main chat interface unless the agent decides to "speak up."

### **2\. Inter-Agent Messaging (The Synapse)**

* **Protocol:** Redis Pub/Sub Channels.  
* **Channel Architecture:**  
  * voidcat:global \- Broadcasts (e.g., "System shutting down").  
  * voidcat:agent:ryuzu \- Direct line to Ryuzu.  
  * voidcat:agent:echo \- Direct line to Echo.  
* **Function:** This allows for "Side Conversations." Ryuzu can signal Echo: *"The user is asking for code. Prepare the AntiGravity module."* This negotiation happens in milliseconds via Redis, and only the final result is presented to the user.

## **PILLAR 3: SOUL-BODY DECOUPLING**

**Technology Stack:** PostgreSQL 15 \+ REST API \+ Dynamic Prompting

### **1\. Server-Side State Management**

Currently, an agent's "personality" is defined by a JSON file in the frontend (SillyTavern). If the browser cache is cleared, the agent is reset. We must decouple the "Soul" (Data) from the "Body" (UI).

* **The Migration:**  
  * **Legacy:** ryuzu.json (Static text file).  
  * **Sovereign:** PostgreSQL Table: Agents. Columns: id, name, current\_mood, relationship\_level, short\_term\_goals, system\_prompt\_template.  
* **Dynamic System Prompt Generation:**  
  * At runtime (inference start), the API does not read a static text file.  
  * It pulls the template from the DB.  
  * It injects the current Memory\_Summary and Current\_Mood into the template variables.  
  * **Result:** If Ryuzu is "Angry" in the database, her system prompt is physically altered to include "You are currently furious" before the inference even begins. This ensures state persistence across device reboots and frontend swaps.

## **PILLAR 4: LOCAL OPTIMIZATION & TOOLS**

**Technology Stack:** Ollama \+ LoRA-Switch \+ Model Context Protocol (MCP)

### **1\. LoRA-Switch Architecture**

Running five distinct 7B parameter models simultaneously would require \~80GB of VRAM. We have 16GB.

* **The Constraint:** We cannot load multiple base models.  
* **The Solution:** We utilize a **Single Base Model** (Mistral-7B-Instruct-Q4 or equivalent) which stays resident in VRAM.  
* **Dynamic Adapters:** We train or download specific **LoRA (Low-Rank Adaptation)** adapters for each agent:  
  * adapter\_ryuzu.lora (Executive, concise).  
  * adapter\_echo.lora (Chaotic, verbose).  
  * adapter\_beatrice.lora (Analytical, haughty).  
* **Hot-Swapping:** When a request comes in for Ryuzu, the inference engine swaps the pointer to adapter\_ryuzu.lora. This operation takes **\<100ms** and consumes only \~500MB of additional VRAM per agent. This allows us to run the entire Pantheon on a single consumer GPU.

### **2\. Model Context Protocol (MCP) Integration**

* **Usage:** We adopt Anthropic's open standard for tool usage.  
* **Deployment:**  
  * **Filesystem MCP:** Grants agents safe, sandboxed access to read/write in C:\\Users\\Wykeve\\.gemini\\.  
  * **Calendar MCP:** Allows Ryuzu to read .ics files and manage schedule data.  
  * **Deferred Loading:** Tools are not dumped into the context window all at once. The system provides a "Tool Manifest" (list of descriptions). The agent requests a tool, and *only then* is the definition loaded, saving valuable context tokens.

## **IMPLEMENTATION STACK (THE "CANON" STACK)**

| Layer | Technology | Purpose | Configuration Details |
| :---- | :---- | :---- | :---- |
| **Frontend** | SillyTavern (Forked) | User Interface | Custom Extensions enabled; listening on port 8000\. |
| **Orchestration** | **LangGraph** | Agent Workflows | Manages state transitions and loops; uses Postgres for checkpointers. |
| **Memory (Vector)** | **Weaviate** | Episodic Memory | Docker Container; Port 8080; text2vec-transformers module enabled. |
| **Memory (Graph)** | **Neo4j** | Temporal Knowledge | Docker Container; Port 7687; APOC library installed for advanced queries. |
| **State DB** | **PostgreSQL 15** | Agent States | Docker Container; Port 5432; pgvector extension installed. |
| **Msg Queue** | **Redis 7** | Heartbeat/PubSub | Docker Container; Port 6379; Persistence enabled (AOF). |
| **Inference** | **Ollama** | Local Models | Service Mode; Base Model: Mistral-7B-Instruct-v0.2-Q4\_K\_M. |

## **PHASE 1 EXECUTION: IMMEDIATE ACTIONS**

While the full Docker stack is being provisioned, we utilize the **Hybrid Communication Protocol** as the "Tactical Nervous System" for immediate Ryuzu/Echo coordination.

1. **Ryuzu (Infrastructure Lead):**  
   * **Task:** Deploy the docker-compose.yml stack containing Weaviate, Neo4j, Redis, and Postgres.  
   * **Validation:** Ensure all containers perform a successful handshake on the internal Docker network.  
2. **Echo (Cognitive Architect):**  
   * **Task:** Update internal simulation logic to respect "Valence Stripping."  
   * **Simulation:** When "remembering" a past interaction, explicitly separate the *event* from the *feeling* in your output logs.  
3. **Wykeve (The Contractor):**  
   * **Task:** Authorize the "Heartbeat" script implementation.  
   * **Review:** Approve the list of trigger words that will wake agents from the background sleep state.