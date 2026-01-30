import React, { useState, useEffect } from 'react';
import { Settings, Save, RefreshCw, AlertTriangle } from 'lucide-react';

const API_BASE = "http://localhost:8000";

export default function Config() {
    const [agents, setAgents] = useState({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [selectedAgent, setSelectedAgent] = useState('echo');

    const agentIds = ['echo', 'beatrice', 'ryuzu'];

    useEffect(() => {
        loadAgentConfigs();
    }, []);

    const loadAgentConfigs = async () => {
        setLoading(true);
        const configs = {};

        for (const agentId of agentIds) {
            try {
                const response = await fetch(`${API_BASE}/agent/${agentId}`);
                if (response.ok) {
                    const data = await response.json();
                    configs[agentId] = data;
                } else {
                    configs[agentId] = { error: 'Failed to load' };
                }
            } catch (error) {
                configs[agentId] = { error: 'Connection failed' };
            }
        }

        setAgents(configs);
        setLoading(false);
    };

    const saveConfig = async (agentId, config) => {
        setSaving(true);
        // Note: This is a placeholder - actual update API may not exist yet
        // In a real implementation, this would call a PUT/PATCH endpoint
        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 1000));
            alert(`Configuration for ${agentId} would be saved (API not implemented yet)`);
        } catch (error) {
            alert('Failed to save configuration');
        } finally {
            setSaving(false);
        }
    };

    const currentAgent = agents[selectedAgent] || {};

    return (
        <div style={{ padding: '2rem', height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div className="glass-panel" style={{ marginBottom: '20px' }}>
                <h1 className="radiant-text" style={{ margin: 0, fontSize: '1.5rem' }}>CONFIGURATION // AGENT PARAMETERS</h1>
                <p style={{ margin: '8px 0 0 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                    Adjust Sovereign agent parameters and system settings
                </p>
            </div>

            {/* Agent Selector */}
            <div className="glass-panel" style={{ marginBottom: '20px' }}>
                <h3 style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                    SELECT AGENT
                </h3>
                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                    {agentIds.map(agentId => (
                        <button
                            key={agentId}
                            onClick={() => setSelectedAgent(agentId)}
                            style={{
                                padding: '12px 16px',
                                border: selectedAgent === agentId ? '1px solid var(--neon-cyan)' : '1px solid var(--void-border)',
                                backgroundColor: selectedAgent === agentId ? 'rgba(0, 229, 255, 0.1)' : 'rgba(10, 15, 20, 0.5)',
                                color: selectedAgent === agentId ? 'var(--neon-cyan)' : 'var(--text-primary)',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                fontSize: '0.9rem'
                            }}
                        >
                            <div style={{ fontWeight: 'bold' }}>{agentId.toUpperCase()}</div>
                        </button>
                    ))}
                </div>
            </div>

            {/* Configuration Panel */}
            <div className="glass-panel" style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h3 style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                        AGENT CONFIGURATION: {selectedAgent.toUpperCase()}
                    </h3>
                    <div style={{ display: 'flex', gap: '12px' }}>
                        <button
                            onClick={loadAgentConfigs}
                            disabled={loading}
                            style={{
                                padding: '8px 12px',
                                backgroundColor: 'rgba(10, 15, 20, 0.5)',
                                border: '1px solid var(--void-border)',
                                borderRadius: '6px',
                                color: 'var(--text-primary)',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                fontSize: '0.8rem'
                            }}
                        >
                            <RefreshCw size={14} />
                            REFRESH
                        </button>
                        <button
                            onClick={() => saveConfig(selectedAgent, currentAgent)}
                            disabled={saving}
                            style={{
                                padding: '8px 12px',
                                backgroundColor: 'var(--neon-green)',
                                border: 'none',
                                borderRadius: '6px',
                                color: 'rgba(10, 15, 20, 0.9)',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                fontSize: '0.8rem',
                                fontWeight: 'bold'
                            }}
                        >
                            <Save size={14} />
                            {saving ? 'SAVING...' : 'SAVE'}
                        </button>
                    </div>
                </div>

                {loading ? (
                    <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                        Loading agent configurations...
                    </div>
                ) : currentAgent.error ? (
                    <div style={{
                        textAlign: 'center',
                        padding: '40px',
                        color: 'var(--neon-error)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '12px'
                    }}>
                        <AlertTriangle size={48} />
                        <div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>Configuration Unavailable</div>
                            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                                {currentAgent.error}
                            </div>
                        </div>
                    </div>
                ) : (
                    <div style={{ display: 'grid', gap: '20px' }}>
                        {/* Basic Info */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                            <ConfigField
                                label="Agent ID"
                                value={currentAgent.agent_id || selectedAgent}
                                readOnly
                            />
                            <ConfigField
                                label="Name"
                                value={currentAgent.name || 'Unknown'}
                                readOnly
                            />
                            <ConfigField
                                label="Designation"
                                value={currentAgent.designation || 'Unknown'}
                                readOnly
                            />
                            <ConfigField
                                label="Current Mood"
                                value={currentAgent.current_mood || 'neutral'}
                            />
                        </div>

                        {/* System Prompt */}
                        <div>
                            <label style={{
                                display: 'block',
                                color: 'var(--text-secondary)',
                                fontSize: '0.9rem',
                                marginBottom: '8px',
                                fontWeight: 'bold'
                            }}>
                                SYSTEM PROMPT
                            </label>
                            <textarea
                                value={currentAgent.system_prompt || ''}
                                onChange={(e) => setAgents(prev => ({
                                    ...prev,
                                    [selectedAgent]: { ...prev[selectedAgent], system_prompt: e.target.value }
                                }))}
                                style={{
                                    width: '100%',
                                    minHeight: '120px',
                                    padding: '12px',
                                    backgroundColor: 'rgba(10, 15, 20, 0.5)',
                                    border: '1px solid var(--void-border)',
                                    borderRadius: '8px',
                                    color: 'var(--text-primary)',
                                    fontSize: '0.9rem',
                                    fontFamily: 'inherit',
                                    resize: 'vertical',
                                    outline: 'none'
                                }}
                                placeholder="Enter system prompt..."
                            />
                        </div>

                        {/* Status Info */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                            <ConfigField
                                label="Last Active"
                                value={currentAgent.last_active ? new Date(currentAgent.last_active).toLocaleString() : 'Never'}
                                readOnly
                            />
                            <ConfigField
                                label="Pending Tasks"
                                value={currentAgent.pending_tasks || 0}
                                readOnly
                            />
                        </div>

                        {/* Queued Responses */}
                        <div>
                            <label style={{
                                display: 'block',
                                color: 'var(--text-secondary)',
                                fontSize: '0.9rem',
                                marginBottom: '8px',
                                fontWeight: 'bold'
                            }}>
                                QUEUED RESPONSES ({currentAgent.queued_responses?.length || 0})
                            </label>
                            <div style={{
                                maxHeight: '200px',
                                overflowY: 'auto',
                                backgroundColor: 'rgba(10, 15, 20, 0.3)',
                                border: '1px solid var(--void-border)',
                                borderRadius: '8px',
                                padding: '12px'
                            }}>
                                {currentAgent.queued_responses?.length > 0 ? (
                                    currentAgent.queued_responses.map((response, index) => (
                                        <div key={index} style={{
                                            padding: '8px',
                                            marginBottom: '8px',
                                            backgroundColor: 'rgba(0, 229, 255, 0.1)',
                                            borderRadius: '4px',
                                            fontSize: '0.8rem'
                                        }}>
                                            <div style={{ color: 'var(--neon-cyan)', fontWeight: 'bold' }}>
                                                {response.timestamp ? new Date(response.timestamp).toLocaleString() : 'Unknown time'}
                                            </div>
                                            <div style={{ color: 'var(--text-primary)', marginTop: '4px' }}>
                                                {response.content || 'No content'}
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div style={{ color: 'var(--text-dim)', fontStyle: 'italic' }}>
                                        No queued responses
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

const ConfigField = ({ label, value, readOnly = false, onChange }) => (
    <div>
        <label style={{
            display: 'block',
            color: 'var(--text-secondary)',
            fontSize: '0.9rem',
            marginBottom: '8px',
            fontWeight: 'bold'
        }}>
            {label.toUpperCase()}
        </label>
        <input
            type="text"
            value={value}
            onChange={onChange}
            readOnly={readOnly}
            style={{
                width: '100%',
                padding: '12px',
                backgroundColor: readOnly ? 'rgba(10, 15, 20, 0.3)' : 'rgba(10, 15, 20, 0.5)',
                border: '1px solid var(--void-border)',
                borderRadius: '8px',
                color: 'var(--text-primary)',
                fontSize: '0.9rem',
                outline: 'none',
                cursor: readOnly ? 'default' : 'text'
            }}
        />
    </div>
);