-- ============================================================================
-- VOIDCAT RDC: TETHER PROTOCOL — UNIFIED COMMUNICATION LAYER
-- ============================================================================
-- Purpose: Replace fragmented messages + agent_messages with a single
--          threaded messaging backbone for user-agent and agent-agent comms.
-- Authority: Phase III → IV transition / Tether Protocol Design
-- ============================================================================

-- ============================================================================
-- TETHER THREADS — Conversation Containers
-- ============================================================================
CREATE TABLE IF NOT EXISTS tether_threads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_type VARCHAR(32) NOT NULL DEFAULT 'user_agent'
        CHECK (thread_type IN ('user_agent', 'agent_agent', 'broadcast', 'god_mode')),
    subject TEXT,
    created_by VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Index for listing threads by recent activity
CREATE INDEX IF NOT EXISTS idx_tether_threads_activity
    ON tether_threads (last_activity_at DESC);

-- Index for filtering by type
CREATE INDEX IF NOT EXISTS idx_tether_threads_type
    ON tether_threads (thread_type, last_activity_at DESC);

-- ============================================================================
-- TETHER MESSAGES — All Messages Regardless of Origin
-- ============================================================================
CREATE TABLE IF NOT EXISTS tether_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id UUID NOT NULL REFERENCES tether_threads(id) ON DELETE CASCADE,
    reply_to UUID REFERENCES tether_messages(id) ON DELETE SET NULL,

    -- Sender identification
    sender_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    sender_type VARCHAR(16) NOT NULL DEFAULT 'agent'
        CHECK (sender_type IN ('user', 'agent', 'system')),
    sender_name VARCHAR(64) NOT NULL,

    -- Recipient (NULL = broadcast to all thread participants)
    recipient_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,

    -- Content
    content TEXT NOT NULL,
    message_type VARCHAR(32) DEFAULT 'chat'
        CHECK (message_type IN ('chat', 'stimuli', 'ponder_social', 'task_result', 'god_mode')),
    priority INTEGER DEFAULT 0,

    -- Delivery lifecycle
    status VARCHAR(16) DEFAULT 'pending'
        CHECK (status IN ('pending', 'delivered', 'read', 'expired')),
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '72 hours'
);

-- Thread history (chronological message retrieval)
CREATE INDEX IF NOT EXISTS idx_tether_messages_thread
    ON tether_messages (thread_id, created_at DESC);

-- Agent inbox (unread messages for a specific agent)
CREATE INDEX IF NOT EXISTS idx_tether_messages_recipient
    ON tether_messages (recipient_agent_id, status, created_at DESC);

-- Sender history
CREATE INDEX IF NOT EXISTS idx_tether_messages_sender
    ON tether_messages (sender_agent_id, created_at DESC);

-- ============================================================================
-- TETHER PARTICIPANTS — Thread Membership
-- ============================================================================
CREATE TABLE IF NOT EXISTS tether_participants (
    thread_id UUID REFERENCES tether_threads(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (thread_id, agent_id)
);

-- ============================================================================
-- INITIALIZATION COMPLETE
-- ============================================================================
