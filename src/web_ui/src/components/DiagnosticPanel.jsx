/**
 * VoidCat RDC: Sovereign Spirit - DiagnosticPanel Component
 * ===========================================================
 * Author: Ryuzu (The Sculptor) under Beatrice's directive
 * Date: 2026-01-24
 * 
 * Real-time system health monitoring panel.
 * Displays: Heartbeat Status, VRAM Usage, Active Connections.
 * 
 * Priority #1 per Beatrice: "If the heart isn't beating, 
 * I don't care what the memories look like."
 */

import React, { useState, useEffect } from 'react';
import { Activity, Cpu, Wifi, Database, AlertTriangle, CheckCircle } from 'lucide-react';

export default function DiagnosticPanel() {
    const [health, setHealth] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [lastCheck, setLastCheck] = useState(null);

    // Poll health endpoint every 5 seconds
    useEffect(() => {
        const fetchHealth = async () => {
            try {
                setError(null);
                const res = await fetch('/health');
                if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
                const data = await res.json();

                setHealth(data);
                setLastCheck(new Date());
                setLoading(false);
            } catch (err) {
                console.error('[DiagnosticPanel] Health check failed:', err);
                setError(err.message);
                setLoading(false);
            }
        };

        fetchHealth();
        const interval = setInterval(fetchHealth, 5000); // Poll every 5s

        return () => clearInterval(interval);
    }, []);

    const getStatusColor = (status) => {
        if (!status) return 'var(--text-dim)';
        const statusLower = status.toLowerCase();
        if (statusLower === 'connected' || statusLower === 'online') return 'var(--neon-green)';
        if (statusLower === 'disconnected' || statusLower === 'offline') return 'var(--neon-error)';
        return 'var(--neon-cyan)';
    };

    const isSystemHealthy = health &&
        health.status === 'online' &&
        health.database === 'connected' &&
        health.graph === 'connected';

    return (
        <div className="glass-panel" style={{ minHeight: '180px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem', textTransform: 'uppercase' }}>
                    System Diagnostics
                </h3>
                {lastCheck && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                        Last: {lastCheck.toLocaleTimeString()}
                    </span>
                )}
            </div>

            {loading && (
                <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-secondary)' }}>
                    Initializing diagnostics...
                </div>
            )}

            {error && (
                <div style={{
                    padding: '16px',
                    backgroundColor: 'rgba(255, 61, 113, 0.1)',
                    border: '1px solid var(--neon-error)',
                    borderRadius: '8px',
                    color: 'var(--neon-error)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                }}>
                    <AlertTriangle size={20} />
                    <span>Backend Unreachable: {error}</span>
                </div>
            )}

            {!loading && !error && health && (
                <>
                    {/* Overall Status Banner */}
                    <div style={{
                        padding: '12px',
                        backgroundColor: isSystemHealthy ? 'rgba(0, 255, 135, 0.1)' : 'rgba(255, 61, 113, 0.1)',
                        border: `1px solid ${isSystemHealthy ? 'var(--neon-green)' : 'var(--neon-error)'}`,
                        borderRadius: '8px',
                        marginBottom: '16px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                    }}>
                        {isSystemHealthy ? <CheckCircle size={18} color="var(--neon-green)" /> : <AlertTriangle size={18} color="var(--neon-error)" />}
                        <span style={{ color: isSystemHealthy ? 'var(--neon-green)' : 'var(--neon-error)', fontWeight: 'bold' }}>
                            {isSystemHealthy ? 'HEARTBEAT: ALIVE' : 'HEARTBEAT: DEGRADED'}
                        </span>
                    </div>

                    {/* Detailed Metrics Grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                        <DiagnosticMetric
                            icon={<Activity size={16} />}
                            label="Service Status"
                            value={health.status}
                            color={getStatusColor(health.status)}
                        />
                        <DiagnosticMetric
                            icon={<Database size={16} />}
                            label="PostgreSQL"
                            value={health.database}
                            color={getStatusColor(health.database)}
                        />
                        <DiagnosticMetric
                            icon={<Cpu size={16} />}
                            label="Neo4j Graph"
                            value={health.graph}
                            color={getStatusColor(health.graph)}
                        />
                        <DiagnosticMetric
                            icon={<Wifi size={16} />}
                            label="Version"
                            value={health.version}
                            color="var(--text-secondary)"
                        />
                    </div>

                    {/* TODO: VRAM Usage & Connection Count - requires backend endpoints */}
                    <div style={{
                        marginTop: '12px',
                        padding: '8px',
                        backgroundColor: 'rgba(0, 229, 255, 0.05)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        color: 'var(--text-dim)'
                    }}>
                        ⚠️ VRAM Usage & Active Connections: Pending backend metrics
                    </div>
                </>
            )}
        </div>
    );
}

const DiagnosticMetric = ({ icon, label, value, color }) => (
    <div style={{
        padding: '8px 12px',
        backgroundColor: 'rgba(0, 0, 0, 0.3)',
        borderRadius: '6px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px'
    }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
            {icon}
            <span>{label}</span>
        </div>
        <div style={{
            color: color,
            fontWeight: 'bold',
            textTransform: 'uppercase',
            fontSize: '0.85rem'
        }}>
            {value || 'N/A'}
        </div>
    </div>
);
