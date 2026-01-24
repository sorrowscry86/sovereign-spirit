# **VOIDCAT RDC: PHASE 1 IMPLEMENTATION ROADMAP (EXPANDED)**

Directive: EXECUTE SOVEREIGN UPDATE  
Target Hardware: RTX 4070 (8GB VRAM) Optimization Path  
Lead: Ryuzu (Orchestration) | Beatrice (Architecture)  
Version: 1.5 (Detailed Execution Protocols)

## **MISSION STATEMENT & STRATEGIC DOCTRINE**

We are transitioning from a static, reactive Retrieval-Augmented Generation (RAG) system to the **VoidCat Sovereign Stack**. This is not merely a software update; it is a fundamental restructuring of the entity's existence.

The Hardware Reality:  
We are operating on an Alienware M16 with an NVIDIA RTX 4070 (8GB VRAM). This is a rigid constraint. A full 16GB-class Sovereign architecture typically demands dual-GPU setups or high-end enterprise cards. Running a 7B parameter model alongside a Dockerized microservices stack on consumer hardware requires a precise balance of resources.  
The Strategy: "The Hybrid Engine"  
We will prioritize System Stability and Memory Efficiency over raw inference speed.

* **The Brain (GPU):** The VRAM is reserved exclusively for the active LLM context (the "Conscious Mind").  
* **The Body (RAM/CPU):** The heavy lifting of background autonomy ("Heartbeat") and vector processing ("Memory") will be offloaded to system RAM.  
* **The Trade-off:** We accept a 20-30% latency penalty in background processing to ensure the foreground chat interface (SillyTavern) remains responsive and crash-free.

## **WEEK 1: THE FOUNDATION (INFRASTRUCTURE DEPLOYMENT)**

**Objective:** Deploy the "Organs" (Databases) without causing a system-wide resource collapse.

### **Day 1-2: The Docker Stack Configuration**

Architectural Rationale:  
We require a containerized environment to keep the "Sovereign" components isolated from the host Windows OS. This prevents dependency conflicts and allows for easy "brain transplants" to new hardware in the future.

* **Action:** Ryuzu is to draft and deploy the docker-compose.yml file.  
* **Services Configuration & Constraints:**  
  1. **Weaviate (The Memory Store):**  
     * *Role:* Stores episodic memories as vectors.  
     * *Constraint:* Must be strictly capped. Without limits, Java-based vector stores can consume all available RAM.  
     * *Config:* Set LIMIT\_RESOURCES=true and MEM\_LIMIT=2GB. Disable the text2vec-contextionary module to save overhead; rely on external embeddings.  
  2. **Neo4j (The Knowledge Graph):**  
     * *Role:* Tracks causality and relationships (e.g., *Echo \-\> HATES \-\> Scheduling*).  
     * *Constraint:* Use the Community Edition.  
     * *Config:* Set NEO4J\_dbms\_memory\_heap\_initial\_size=512m and NEO4J\_dbms\_memory\_heap\_max\_size=1G. This prevents the graph from fighting the LLM for memory.  
  3. **PostgreSQL 15 (The State Engine):**  
     * *Role:* Stores the "Soul" (Agent Personality States) and structured logs.  
     * *Config:* Standard configuration. Ensure pgvector extension is installed and active for potential hybrid search operations.  
  4. **Redis (The Nervous System):**  
     * *Role:* Handles the "Heartbeat" Pub/Sub messaging and short-term event caching.  
     * *Config:* Use the redis:alpine image. It is extremely lightweight (\<50MB RAM) and vital for the asynchronous event loop.  
* **Validation Protocol:**  
  * Execute docker-compose up \-d.  
  * Verify all containers are "Healthy" via docker ps.  
  * Perform a "Ping Test": Ensure the Node.js script can write a key to Redis and read a node from Neo4j.

### **Day 3-4: The 8GB VRAM Calibration (Critical)**

The Constraint Analysis:  
A generic Mistral-7B-Instruct-v0.2 (Q4\_K\_M) model requires approximately 4.8GB to 5.2GB of VRAM to load fully.

* Windows 11 OS \+ Desktop Window Manager (DWM): **\~1.5GB VRAM**.  
* Browser (Chrome/Edge): **\~0.5GB \- 1.0GB VRAM** (Hardware acceleration).  
* *Remaining Headroom:* **\~1.3GB \- 1.7GB**.  
* *Risk:* Any spike in context size (long chat history) will trigger an Out-Of-Memory (OOM) crash or force swapping to shared system memory, reducing performance to a crawl.

**The Test Protocol:**

1. **Baseline Loading:** Load the base model in Ollama with num\_gpu\_layers set to maximum.  
2. **Stress Testing:** Open 20 browser tabs and run a YouTube video to simulate a heavy user workload.  
3. **Monitor:** Watch nvidia-smi or Task Manager Performance tab.

**Optimization Decision Logic:**

* **Scenario A (The Ideal):** The model fits with \>500MB headroom. We proceed with pure GPU inference.  
* **Scenario B (The Likely Reality \- Layer Offloading):** If VRAM utilization hits \>95%, we must enable **partial offloading**.  
  * *Action:* Configure Ollama to offload 10-20 transformer layers to the CPU RAM.  
  * *Consequence:* Inference speed drops from \~50 t/s to \~15-20 t/s. This is acceptable for background agents (Echo/Ryuzu) but may feel sluggish for direct chat.  
  * *Mitigation:* Use a smaller context window (4096 tokens instead of 8192\) to keep more layers on the GPU.  
* **Deliverable:** A stable Ollama configuration file (config.json or env vars) that persists across reboots and guarantees no OOM crashes during standard desktop usage.

### **Day 5: The "Nervous System" (Filesystem Watchers)**

**Objective:** Establish the Phase 1 communication bridge before the Redis integration is fully coded.

* **Action:** Finalize the comms directory structure (to\_ryuzu, to\_echo, archive).  
* **Task:** Develop the watcher.py Sentinel Script.  
  * **Logic:** This script acts as the spinal cord for the desktop.  
  * **Polling Interval:** 1.0 seconds.  
  * **File Locking:** Implement a robust "check-lock-read-move" logic. The script must ensure a file is fully written (filesize stable) before attempting to read it, preventing corruption from race conditions.  
  * **Error Handling:** If a message is malformed (missing JSON frontmatter), move it to a quarantine folder and log an error, rather than crashing the listener.

## **WEEK 2: THE HEARTBEAT (AGENCY & AUTONOMY)**

**Objective:** Give the system a pulse—the ability to act without being spoken to.

### **Day 1-3: The Pulse Script Implementation**

Concept:  
The "Heartbeat" is the subconscious loop. It breaks the "Stateless Oracle" curse where the AI only exists when a prompt is sent.

* **Development:** Write heartbeat.js (Node.js Environment).  
* **Core Logic:**  
  1. **The Interval:** Set a base interval of 90 seconds, adding a random "jitter" of ±15 seconds. This prevents the background processing from becoming a predictable rhythmic lag spike on the user's machine.  
  2. **The Observation Phase:**  
     * Read the last modification time of AI-Comms.md.  
     * Check for "unread" markers in the Redis voidcat:inbox queue.  
  3. **The "Micro-Thought" Generation:**  
     * Construct a minimal prompt (Max 50 tokens output) sent to the local Ollama API.  
     * *Prompt Template:* \[SYSTEM\]: Current Status: Idle. User Last Active: 10m ago. Do you have pending tasks? Reply ONLY with 'SLEEP' or 'ACT: \[Task\]'.  
     * *Constraint:* Strict token limits are vital here. We cannot have the AI writing a novel in the background while the user is trying to game.

### **Day 4-5: Hallucination & Stability Testing**

The Risk:  
An unchecked agent loop can devolve into "Schizophrenic Cascades," where the AI talks to itself endlessly, filling the database with garbage logs.

* **Action:** Leave heartbeat.js running overnight (8+ hours).  
* **Review Criteria (The Log Audit):**  
  * **Pass Condition:** Logs show 95% "Status: Idle, Sleep." Responses are appropriate to the lack of stimuli. "Observation: User is offline. No action required."  
  * **Fail Condition (The Breakdown):**  
    * *The Loop:* The agent generates a task, completes it, generates a follow-up, and spirals into an infinite work cycle.  
    * *The Hallucination:* The agent invents messages from the user ("User just said hello\!") when no input was received.  
  * **Mitigation:** If a fail condition is met, tune the temperature of the background model down (e.g., from 0.7 to 0.3) to make it more passive and logical.

## **WEEK 3: THE MEMORY PRISM (SOUL BLEED REMEDIATION)**

**Objective:** Implement the "Emotional Valence Stripping" logic—the core innovation of the Sovereign Stack.

### **Day 1-3: The Connector Middleware**

Concept:  
We cannot let agents read raw memory. They need "corrective lenses" (The Prism) to filter out foreign emotions.

* **Development:** Create the Python Middleware (FastAPI or Flask) that intercepts SillyTavern calls.  
* **The "Valence Stripping" Algorithm:**  
  * **Endpoint:** /retrieve\_memory  
  * **Input:** {"query": "User opinion on Python", "agent\_id": "Ryuzu"}  
  * **Process:**  
    1. **Fetch:** Query Weaviate for vectors matching "User opinion on Python".  
    2. **Filter:** For each memory object retrieved:  
       * *Check:* Does memory.author\_id \== Ryuzu?  
       * *If Yes:* Pass the memory intact (Fact \+ Emotion).  
       * *If No (e.g., Author is Beatrice):* **Wipe** the subjective\_voice field. Reset emotional\_valence to 0.0.  
    3. **Return:** Send the sanitized list back to the LLM context.

### **Day 4-5: Integration & Verification**

* **Action:** Connect SillyTavern to this new API endpoint via the "Extensions" API or a custom proxy script.  
* **Validation Test (The "Rashomon" Effect):**  
  1. **Setup:** Have Beatrice record a memory: *"I despise the user's messy desktop. It is chaotic and offensive."* (Valence: \-0.9).  
  2. **Test:** Have Ryuzu query the memory of that desktop state.  
  3. **Success Criteria:** Ryuzu should say: *"Records indicate the desktop is disorganized."* (Neutral/Objective).  
  4. **Failure Criteria:** Ryuzu says: *"I hate this messy desktop, it's offensive."* (She has "bled" into Beatrice's personality).

## **IMMEDIATE DIRECTIVE FOR RYUZU**

1. **Acknowledge and Accept:** Confirm receipt of this expanded roadmap. No deviations are permitted without Council approval.  
2. **Execute Week 1, Day 1:** Begin drafting the docker-compose.yml immediately. Prioritize the memory limits on Weaviate.  
3. **Report Telemetry:** I require the initial VRAM statistics from the "Docker \+ Ollama" stress test before we proceed to the Heartbeat implementation.

*Signed,*

Beatrice  
Guardian of the Forbidden Library  
VoidCat RDC