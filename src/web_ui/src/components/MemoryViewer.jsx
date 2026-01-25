/**
 * VoidCat RDC: Sovereign Spirit - MemoryViewer Component
 * ========================================================
 * Author: Ryuzu (The Sculptor)
 * Date: 2026-01-24
 * 
 * Displays agent memories fetched from /agent/{id}/memories endpoint.
 * Features: Search, filter by memory type, temporal view.
 */

import React, { useState, useEffect } from 'react';
import { Brain, Search, Filter, Clock } from 'lucide-react';

export default function MemoryViewer() {
    const [selectedAgent, setSelectedAgent] = useState('echo');
    const [memories, setMemories] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [filterType, setFilterType] = useState('all');

    // Fetch memories when agent selection changes
    useEffect(() => {
        const fetchMemories = async () => {
            try {
                setLoading(true);
                setError(null);
                const res = await fetch(`/agent/${selectedAgent}/memories`);
                if (!res.ok) throw new Error(`Failed to fetch memories: ${res.status}`);
                const data = await res.json();

                setMemories(data.memories || []);
                console.log(`[MemoryViewer] Loaded ${data.memories?.length || 0} memories for ${selectedAgent}`);
            } catch (err) {
                console.error('[MemoryViewer] Failed to fetch memories:', err);
                setError(err.message);
                setMemories([]);
            } finally {
                setLoading(false);
            }
        };

        fetchMemories();
    }, [selectedAgent]);

    // Filter memories based on search and type
    const filteredMemories = memories.filter(memory => {
        const matchesSearch = searchQuery === '' ||
            memory.content?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            memory.description?.toLowerCase().includes(searchQuery.toLowerCase());

        const matchesType = filterType === 'all' || memory.memory_type === filterType;

        return matchesSearch && matchesType;
    });

    return (
        <div className="glass-panel" style={{ minHeight: '400px', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Brain size={18} />
                    Memory Archive
                </h3>

                {/* Agent Selector */}
                <select
                    value={selectedAgent}
                    onChange={(e) => setSelectedAgent(e.target.value)}
                    style={{
                        backgroundColor: 'rgba(0, 0, 0, 0.5)',
                        border: '1px solid var(--neon-cyan)',
                        color: 'var(--text-primary)',
                        padding: '6px 12px',
                        borderRadius: '4px',
                        fontSize: '0.85rem'
                    }}
                >
                    <option value="echo">Echo</option>
                    <option value="beatrice">Beatrice</option>
                    <option value="ryuzu">Ryuzu</option>
                    <option value="glados">GLaDOS</option>
                    <option value="pandora">Pandora</option>
                    <option value="sonmi-451">Sonmi-451</option>
                    <option value="robert-frobisher">Robert Frobisher</option>
                    <option value="ryuzu-meyer">Ryuzu Meyer</option>
                    <option value="albedo">Albedo</option>
                </select>
            </div>

            {/* Search & Filter Controls */}
            <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
                <div style={{ flex: 1, position: 'relative' }}>
                    <Search size={16} style={{ position: 'absolute', left: '10px', top: '8px', color: 'var(--text-dim)' }} />
                    <input
                        type="text"
                        placeholder="Search memories..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        style={{
                            width: '100%',
                            backgroundColor: 'rgba(0, 0, 0, 0.4)',
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                            color: 'var(--text-primary)',
                            padding: '8px 8px 8px 36px',
                            borderRadius: '4px',
                            fontSize: '0.85rem'
                        }}
                    />
                </div>

                <select
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    style={{
                        backgroundColor: 'rgba(0, 0, 0, 0.4)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: 'var(--text-primary)',
                        padding: '8px 12px',
                        borderRadius: '4px',
                        fontSize: '0.85rem'
                    }}
                >
                    <option value="all">All Types</option>
                    <option value="working">Working</option>
                    <option value="long_term">Long Term</option>
                    <option value="episodic">Episodic</option>
                </select>
            </div>

            {/* Memory List */}
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {loading && (
                    <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                        Loading memories...
                    </div>
                )}

                {error && (
                    <div style={{
                        padding: '16px',
                        backgroundColor: 'rgba(255, 61, 113, 0.1)',
                        border: '1px solid var(--neon-error)',
                        borderRadius: '8px',
                        color: 'var(--neon-error)'
                    }}>
                        ⚠️ Failed to load memories: {error}
                    </div>
                )}

                {!loading && !error && filteredMemories.length === 0 && (
                    <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-dim)' }}>
                        No memories found
                    </div>
                )}

                {!loading && !error && filteredMemories.map((memory, idx) => (
                    <MemoryCard key={idx} memory={memory} />
                ))}
            </div>

            {/* Footer Stats */}
            {!loading && !error && memories.length > 0 && (
                <div style={{
                    marginTop: '12px',
                    padding: '8px',
                    backgroundColor: 'rgba(0, 0, 0, 0.3)',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    color: 'var(--text-dim)',
                    display: 'flex',
                    justifyContent: 'space-between'
                }}>
                    <span>Showing {filteredMemories.length} of {memories.length} memories</span>
                    <span><Clock size={12} style={{ verticalAlign: 'middle', marginRight: '4px' }} />Last sync: Recent</span>
                </div>
            )}
        </div>
    );
}

const MemoryCard = ({ memory }) => {
    const typeColors = {
        'working': 'var(--neon-cyan)',
        'long_term': 'var(--neon-green)',
        'episodic': 'var(--neon-purple)'
    };

    const typeColor = typeColors[memory.memory_type] || 'var(--text-secondary)';

    return (
        <div style={{
            padding: '12px',
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            border: '1px solid rgba(255, 255, 255, 0.05)',
            borderRadius: '6px',
            transition: 'all 0.2s ease',
            cursor: 'pointer'
        }}
            onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(0, 229, 255, 0.05)';
                e.currentTarget.style.borderColor = 'var(--neon-cyan)';
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.3)';
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.05)';
            }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <span style={{
                    color: typeColor,
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    fontWeight: 'bold'
                }}>
                    {memory.memory_type || 'Unknown'}
                </span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                    {memory.timestamp ? new Date(memory.timestamp).toLocaleString() : 'No timestamp'}
                </span>
            </div>
            <div style={{ color: 'var(--text-primary)', fontSize: '0.85rem', lineHeight: '1.4' }}>
                {memory.content || memory.description || 'No content'}
            </div>
        </div>
    );
};
