-- Migration 002: Projects table
-- Adds persistent project/goal tracking for agents

CREATE TABLE IF NOT EXISTS projects (
    project_id    TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL,
    lead_agent_id TEXT,  -- agent name (logical ID used throughout app)
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    progress_notes TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS projects_status_idx ON projects(status);
CREATE INDEX IF NOT EXISTS projects_agent_idx ON projects(lead_agent_id);
