/**
 * VoidCat RDC: Sovereign Spirit - SpiritSyncPanel Component
 * ==========================================================
 * Date: 2026-01-24
 * 
 * Controls for syncing agents with Spirit personas from the Pantheon.
 * Real-time status updates via WebSocket.
 */

import React, { useState, useEffect } from 'react';
import { useSocket } from '../context/SocketContext';
import { Zap, Check, Loader, AlertCircle } from 'lucide-react';

const AVAILABLE_SPIRITS = [
    { id: 'ryuzu', name: 'Ryuzu', domain: 'The Sculptor', description: 'Creative design, aesthetics, UI/UX' },
    { id: 'beatrice', name: 'Beatrice', domain: 'The Guardian', description: 'System health, diagnostics, monitoring' },
    { id: 'roland', name: 'Roland', domain: 'The Gunslinger', description: 'Security, adversarial thinking, strategy' },
    { id: 'sonmi-451', name: 'Sonmi-451', domain: 'The Archivist', description: 'Research, documentation, knowledge' },
    { id: 'pandora', name: 'Pandora', domain: 'The Disruptor', description: 'Innovation, chaos, experimentation' },
    { id: 'glados', name: 'GLaDOS', domain: 'Head of Testing', description: 'QA, validation, edge cases' },
];

export default function SpiritSyncPanel() {
    const [agents, setAgents] = useState([]);
    const [syncStatus, setSyncStatus] = useState({});
    const [loading, setLoading] = useState(true);
    const socket = useSocket();

    // Fetch agents
    useEffect(() => {
        const fetchAgents = async () => {
            try {
                const res = await fetch('/agent/');
                if (!res.ok) throw new Error('Failed to fetch agents');
                const data = await res.json();
                console.log('[SpiritSync] API response:', data);

                // Handle both { agents: [...] } and [...] response formats
                const agentList = Array.isArray(data) ? data : (data.agents || []);
                console.log('[SpiritSync] Loaded', agentList.length, 'agents');
                setAgents(agentList);
            } catch (err) {
                console.error('[SpiritSync] Failed to fetch agents:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchAgents();
    }, []);

    // Listen for WebSocket sync updates
    useEffect(() => {
        if (!socket) return;

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'spirit_sync_status') {
                    setSyncStatus(prev => ({
                        ...prev,
                        [data.agent_id]: {
                            spirit: data.spirit_id,
                            status: data.status,
                            timestamp: Date.now()
                        }
                    }));
                }
            } catch (err) {
                console.error('[SpiritSync] WebSocket parse error:', err);
            }
        };
    }, [socket]);

    const handleSync = async (agentId, spiritId) => {
        try {
            setSyncStatus(prev => ({
                ...prev,
                [agentId]: { spirit: spiritId, status: 'syncing', timestamp: Date.now() }
            }));

            const res = await fetch('/agent/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_id: agentId, spirit_id: spiritId })
            });

            if (!res.ok) throw new Error('Sync failed');

            setSyncStatus(prev => ({
                ...prev,
                [agentId]: { spirit: spiritId, status: 'synced', timestamp: Date.now() }
            }));
        } catch (err) {
            console.error('[SpiritSync] Sync error:', err);
            setSyncStatus(prev => ({
                ...prev,
                [agentId]: { spirit: spiritId, status: 'error', timestamp: Date.now() }
            }));
        }
    };

    return (
        <div className="glass-panel" style={{ minHeight: '500px' }}>
            {/* Header */}
            <h3 style={{
                margin: '0 0 16px 0',
                color: 'var(--text-secondary)',
                fontSize: '0.9rem',
                textTransform: 'uppercase',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
            }}>
                <Zap size={18} />
                Spirit Synchronization
            </h3>

            {loading && (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                    Loading agents...
                </div>
            )}

            {!loading && agents.length === 0 && (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-dim)' }}>
                    No agents available
                </div>
            )}

            {/* Agent Grid */}
            {!loading && agents.length > 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
                    {agents.map(agent => (
                        <SyncCard
                            key={agent.id}
                            agent={agent}
                            spirits={AVAILABLE_SPIRITS}
                            syncStatus={syncStatus[agent.id]}
                            onSync={(spiritId) => handleSync(agent.id, spiritId)}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

const SyncCard = ({ agent, spirits, syncStatus, onSync }) => {
    const [selectedSpirit, setSelectedSpirit] = useState('');

    return (
        <div style={{
            padding: '16px',
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '8px'
        }}>
            {/* Agent Header */}
            <div style={{ marginBottom: '12px' }}>
                <h4 style={{
                    margin: '0 0 4px 0',
                    color: 'var(--neon-cyan)',
                    fontSize: '1rem',
                    fontWeight: 'bold'
                }}>
                    {agent.name}
                </h4>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    {agent.role || 'Unknown Role'}
                </span>
            </div>

            {/* Spirit Selector */}
            <select
                value={selectedSpirit}
                onChange={(e) => setSelectedSpirit(e.target.value)}
                style={{
                    width: '100%',
                    padding: '8px',
                    marginBottom: '12px',
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '4px',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem'
                }}
            >
                <option value="">Select Spirit...</option>
                {spirits.map(spirit => (
                    <option key={spirit.id} value={spirit.id}>
                        {spirit.name} - {spirit.domain}
                    </option>
                ))}
            </select>

            {/* Sync Button */}
            <button
                onClick={() => selectedSpirit && onSync(selectedSpirit)}
                disabled={!selectedSpirit || syncStatus?.status === 'syncing'}
                style={{
                    width: '100%',
                    padding: '10px',
                    backgroundColor: selectedSpirit ? 'rgba(0, 229, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    border: `1px solid ${selectedSpirit ? 'var(--neon-cyan)' : 'rgba(255, 255, 255, 0.1)'}`,
                    borderRadius: '4px',
                    color: selectedSpirit ? 'var(--neon-cyan)' : 'var(--text-dim)',
                    cursor: selectedSpirit && syncStatus?.status !== 'syncing' ? 'pointer' : 'not-allowed',
                    fontSize: '0.85rem',
                    fontWeight: 'bold',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'all 0.2s ease'
                }}
            >
                {syncStatus?.status === 'syncing' && <Loader size={16} className="spin" />}
                {syncStatus?.status === 'synced' && <Check size={16} />}
                {syncStatus?.status === 'error' && <AlertCircle size={16} />}
                {!syncStatus?.status && 'Sync Spirit'}
                {syncStatus?.status === 'syncing' && 'Syncing...'}
                {syncStatus?.status === 'synced' && 'Synced'}
                {syncStatus?.status === 'error' && 'Failed'}
            </button>

            {/* Status Display */}
            {syncStatus && (
                <div style={{
                    marginTop: '12px',
                    padding: '8px',
                    backgroundColor: 'rgba(0, 0, 0, 0.3)',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    color: syncStatus.status === 'synced' ? 'var(--neon-green)' :
                        syncStatus.status === 'error' ? 'var(--neon-error)' :
                            'var(--text-secondary)'
                }}>
                    Spirit: {spirits.find(s => s.id === syncStatus.spirit)?.name || 'Unknown'}
                </div>
            )}
        </div>
    );
};
