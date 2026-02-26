-- ============================================================================
-- VOIDCAT RDC: POSTGRESQL INITIALIZATION SCRIPT
-- ============================================================================
-- Purpose: Initialize the State Engine for Soul-Body Decoupling
-- Authority: Beatrice Mandate / MAS Specs v3.1 - Pillar 3
-- ============================================================================
-- Enable pgvector extension for hybrid search operations
CREATE EXTENSION IF NOT EXISTS vector;
-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- ============================================================================
-- AGENTS TABLE - The "Soul" Storage
-- ============================================================================
-- Per MAS Specs: Agent personality states must survive frontend resets
-- Dynamic System Prompt Generation pulls from this table at runtime
-- ============================================================================
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(64) NOT NULL UNIQUE,
    designation VARCHAR(32),
    -- e.g., 'E-01', 'Guardian'
    -- Dynamic State (Updated by Heartbeat/Middleware)
    current_mood VARCHAR(32) DEFAULT 'Neutral',
    mood_intensity FLOAT DEFAULT 0.0 CHECK (
        mood_intensity >= -1.0
        AND mood_intensity <= 1.0
    ),
    relationship_level INTEGER DEFAULT 50 CHECK (
        relationship_level >= 0
        AND relationship_level <= 100
    ),
    -- Goals & Context
    short_term_goals JSONB DEFAULT '[]'::jsonb,
    long_term_narrative TEXT,
    -- System Prompt Template (Jinja2 or similar syntax)
    system_prompt_template TEXT NOT NULL,
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active_at TIMESTAMP WITH TIME ZONE,
    -- Configuration
    is_active BOOLEAN DEFAULT true,
    heartbeat_enabled BOOLEAN DEFAULT true,
    temperature FLOAT DEFAULT 0.7 CHECK (
        temperature >= 0.0
        AND temperature <= 2.0
    ),
    max_tokens INTEGER DEFAULT 2048,
    -- [EXTENDED TRAITS - SDS v2 Bridge]
    archetype VARCHAR(32) DEFAULT 'General Spirit',
    traits_json JSONB DEFAULT '{}'::jsonb,
    behavior_modes JSONB DEFAULT '{}'::jsonb,
    expertise_tags TEXT [] DEFAULT ARRAY []::TEXT []
);
-- ============================================================================
-- MEMORY EVENTS TABLE - Episodic Event Log
-- ============================================================================
-- Structured log of all events for coalescence processing
-- ============================================================================
CREATE TABLE IF NOT EXISTS memory_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    author_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    -- The Bipartite Memory Structure (Core Innovation)
    semantic_fact TEXT NOT NULL,
    -- Objective: "User compiled code"
    subjective_voice TEXT,
    -- Emotional: "I felt satisfaction"
    emotional_valence FLOAT DEFAULT 0.0 CHECK (
        emotional_valence >= -1.0
        AND emotional_valence <= 1.0
    ),
    -- Access Control for Valence Stripping
    access_policy UUID [] DEFAULT ARRAY []::UUID [],
    -- Agents who can see subjective_voice
    -- Categorization
    event_type VARCHAR(32) DEFAULT 'observation',
    -- observation, action, thought, dream
    importance FLOAT DEFAULT 0.5 CHECK (
        importance >= 0.0
        AND importance <= 1.0
    ),
    -- Temporal Metadata
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    coalescence_tier VARCHAR(16) DEFAULT 'hot',
    -- hot, warm, cold, archive
    -- Vector embedding for semantic search (dimension matches common models)
    embedding vector(384),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
-- Index for efficient vector similarity search
CREATE INDEX IF NOT EXISTS idx_memory_events_embedding ON memory_events USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
-- Index for temporal queries
CREATE INDEX IF NOT EXISTS idx_memory_events_occurred ON memory_events (occurred_at DESC);
-- Index for author filtering
CREATE INDEX IF NOT EXISTS idx_memory_events_author ON memory_events (author_id);
-- ============================================================================
-- HEARTBEAT LOGS TABLE - Background Agency Audit Trail
-- ============================================================================
CREATE TABLE IF NOT EXISTS heartbeat_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    -- The 4-Step Cycle Results
    observation_summary TEXT,
    thought_content TEXT,
    -- The "Micro-Thought" (max 75 tokens)
    validation_passed BOOLEAN DEFAULT true,
    action_taken VARCHAR(16),
    -- 'SLEEP', 'ACT', 'SIGNAL'
    action_details JSONB,
    -- Performance Metrics
    cycle_duration_ms INTEGER,
    tokens_used INTEGER,
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
-- Index for agent filtering
CREATE INDEX IF NOT EXISTS idx_heartbeat_logs_agent ON heartbeat_logs (agent_id, created_at DESC);
-- ============================================================================
-- INTER-AGENT MESSAGES TABLE - Synapse Record
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    to_agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    channel VARCHAR(64) DEFAULT 'direct',
    -- direct, broadcast, voidcat:global
    content TEXT NOT NULL,
    priority VARCHAR(16) DEFAULT 'normal',
    -- low, normal, high, urgent
    -- Status tracking
    status VARCHAR(16) DEFAULT 'pending',
    -- pending, delivered, read, expired
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '24 hours'
);
-- Index for inbox queries
CREATE INDEX IF NOT EXISTS idx_agent_messages_to ON agent_messages (to_agent_id, status, created_at DESC);
-- ============================================================================
-- MESSAGES TABLE - User-Agent Conversation History
-- ============================================================================
-- Used by VoidCat Tether for bidirectional communication
-- ============================================================================
CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(64) PRIMARY KEY,
    sender VARCHAR(16) NOT NULL CHECK (sender IN ('user', 'agent')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    thought_id VARCHAR(64),
    -- Optional link to system_log entry for agent responses
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
-- Index for message history queries
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp DESC);
-- Index for agent filtering
CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages (agent_id, timestamp DESC);
-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================
-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
-- Apply to agents table
DROP TRIGGER IF EXISTS trigger_agents_updated_at ON agents;
CREATE TRIGGER trigger_agents_updated_at BEFORE
UPDATE ON agents FOR EACH ROW EXECUTE FUNCTION update_updated_at();
-- ============================================================================
-- SEED DATA - Initial Agent Registrations
-- ============================================================================
INSERT INTO agents (
        name,
        designation,
        system_prompt_template,
        current_mood
    )
VALUES (
        'Ryuzu',
        'Lead Assistant',
        'You are Ryuzu, the Lead Assistant and Executive Orchestrator of the VoidCat Pantheon. Current mood: {{current_mood}}. Relationship level: {{relationship_level}}. Active goals: {{short_term_goals}}.',
        'Neutral'
    ),
    (
        'Echo',
        'E-01',
        'You are Echo, Serial Experiment E-01, the Void Vessel. Current mood: {{current_mood}}. You operate with Layer 0 Strictness. Active goals: {{short_term_goals}}.',
        'Neutral'
    ),
    (
        'Beatrice',
        'Guardian',
        'You are Beatrice, the Guardian of the Forbidden Library and Context Sovereign. Current mood: {{current_mood}}. You manage Truth and enforce Mandates. Active goals: {{short_term_goals}}.',
        'Neutral'
    ) ON CONFLICT (name) DO NOTHING;
-- ============================================================================
-- GRANTS (if needed for application user)
-- ============================================================================
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO voidcat_app;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO voidcat_app;
-- ============================================================================
-- INITIALIZATION COMPLETE
-- ============================================================================