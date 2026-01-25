
import React, { useState, useEffect, useRef } from 'react';
import { Wifi, Database, Brain, Zap, Clock } from 'lucide-react';

import { useSocket } from '../context/SocketContext';
import DiagnosticPanel from '../components/DiagnosticPanel';

export default function Dashboard() {
    // Consume the global nervous system
    const { socketStatus, lastMessage } = useSocket();

    // Local State for UI Visualization
    const [pulseStream, setPulseStream] = useState([]);
    const [agents, setAgents] = useState({});
    const [agentsLoading, setAgentsLoading] = useState(true);
    const [agentsError, setAgentsError] = useState(null);
    const [lastAgentFetch, setLastAgentFetch] = useState(null);

    const streamEndRef = useRef(null);

    // Fetch agents from API on mount
    useEffect(() => {
        const fetchAgents = async () => {
            try {
                setAgentsLoading(true);
                setAgentsError(null);
                const res = await fetch('/agent/');
                if (!res.ok) throw new Error(`Failed to fetch agents: ${res.status}`);
                const agentList = await res.json();

                // Transform to keyed object with default state
                const agentMap = {};
                agentList.forEach(agent => {
                    agentMap[agent.agent_id] = {
                        name: agent.name,
                        designation: agent.designation,
                        current_mood: agent.current_mood,
                        status: 'SLEEP',
                        lastPulse: null,
                        syncStatus: 'Normal',
                        flash: false
                    };
                });

                setAgents(agentMap);
                setLastAgentFetch(new Date());
                console.log(`[Dashboard] Loaded ${agentList.length} agents from API`);
            } catch (error) {
                console.error('[Dashboard] Failed to fetch agents:', error);
                setAgentsError(error.message);
            } finally {
                setAgentsLoading(false);
            }
        };

        fetchAgents();
    }, []);

    // Auto-scroll log
    useEffect(() => {
        streamEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [pulseStream]);

    const handleHeartbeat = (data) => {
        // Update Log Stream
        const logEntry = {
            id: Date.now(),
            time: new Date().toLocaleTimeString(),
            agent: data.agent_id,
            action: data.action,
            msg: data.thought || "Pulse Detected",
            type: 'pulse'
        };
        setPulseStream(prev => [...prev.slice(-49), logEntry]);

        // Update Agent State (only if agent exists)
        setAgents(prev => {
            if (!prev[data.agent_id]) return prev;
            return {
                ...prev,
                [data.agent_id]: {
                    ...prev[data.agent_id],
                    status: data.action,
                    lastPulse: Date.now()
                }
            };
        });
    };

    const handleSyncUpdate = (data) => {
        const logEntry = {
            id: Date.now(),
            time: new Date().toLocaleTimeString(),
            agent: data.agent_id,
            action: 'SYNC',
            msg: `Synchronized to ${data.synced_to} (${data.designation})`,
            type: 'sync'
        };
        setPulseStream(prev => [...prev.slice(-49), logEntry]);

        setAgents(prev => {
            if (!prev[data.agent_id]) return prev;
            return {
                ...prev,
                [data.agent_id]: {
                    ...prev[data.agent_id],
                    designation: data.designation,
                    syncStatus: 'Synchronized',
                    flash: true
                }
            };
        });

        // Reset flash after animation
        setTimeout(() => {
            setAgents(prev => {
                if (!prev[data.agent_id]) return prev;
                return {
                    ...prev,
                    [data.agent_id]: { ...prev[data.agent_id], flash: false }
                };
            });
        }, 800);
    };

    // React to Incoming Nerve Impulses (Global Socket)
    useEffect(() => {
        if (!lastMessage) return;

        if (lastMessage.type === "HEARTBEAT") {
            handleHeartbeat(lastMessage.data);
        } else if (lastMessage.type === "SYNC_UPDATE") {
            handleSyncUpdate(lastMessage.data);
        }
    }, [lastMessage]);

    // Helper: Get agent color based on ID
    const getAgentColor = (agentId) => {
        const colorMap = {
            'echo': 'var(--neon-green)',
            'beatrice': 'var(--neon-cyan)',
            'ryuzu': 'var(--neon-purple)',
        };
        return colorMap[agentId] || 'var(--neon-cyan)'; // Default to cyan
    };

    return (
        <div style={{ padding: '4rem 2rem 2rem 2rem', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>

            {/* HEADER HUD */}
            <div className="glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1 className="radiant-text" style={{ margin: 0, fontSize: '1.5rem' }}>THE OBSERVATORIUM</h1>

                <div style={{ display: 'flex', gap: '20px' }}>
                    <HudMetric icon={<Wifi size={16} />} label="Latency" value="12ms" color="var(--neon-green)" />
                    <HudMetric icon={<Database size={16} />} label="DB" value="Connected" color="var(--neon-cyan)" />
                    <HudMetric
                        icon={<Zap size={16} />}
                        label="System"
                        value={socketStatus}
                        color={socketStatus === 'connected' ? 'var(--neon-green)' : 'var(--neon-error)'}
                    />
                    <HudMetric
                        icon={<Clock size={16} />}
                        label="Agents"
                        value={lastAgentFetch ? lastAgentFetch.toLocaleTimeString() : 'Loading...'}
                        color={agentsError ? 'var(--neon-error)' : 'var(--text-secondary)'}
                    />
                </div>
            </div>

            {/* AGENT GRID */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: '24px',
                minHeight: '240px'
            }}>
                {agentsLoading && (
                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', color: 'var(--text-secondary)', padding: '40px' }}>
                        Loading agents...
                    </div>
                )}
                {agentsError && (
                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', color: 'var(--neon-error)', padding: '40px' }}>
                        ⚠️ Failed to load agents: {agentsError}
                    </div>
                )}
                {!agentsLoading && !agentsError && Object.keys(agents).length === 0 && (
                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', color: 'var(--text-dim)', padding: '40px' }}>
                        No agents found
                    </div>
                )}
                {!agentsLoading && !agentsError && Object.entries(agents).map(([agentId, agentData]) => (
                    <AgentCard
                        key={agentId}
                        id={agentId}
                        name={agentData.name}
                        data={agentData}
                        baseColor={getAgentColor(agentId)}
                    />
                ))}
            </div>

            {/* DIAGNOSTIC PANEL */}
            <DiagnosticPanel />

            {/* PULSE STREAM */}
            <div className="glass-panel" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <h3 style={{ margin: '0 0 10px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', textTransform: 'uppercase' }}>
                    Pulse Stream // Real-Time Telemetry
                </h3>

                <div style={{ flex: 1, overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                    {pulseStream.length === 0 && <div style={{ color: 'var(--text-dim)', padding: '20px' }}>Waiting for signal...</div>}

                    {pulseStream.map(log => (
                        <div key={log.id} style={{
                            display: 'flex',
                            padding: '8px 12px',
                            borderBottom: '1px solid rgba(255,255,255,0.03)',
                            backgroundColor: log.type === 'sync' ? 'rgba(0, 229, 255, 0.05)' : 'transparent'
                        }}>
                            <span style={{ color: 'var(--text-dim)', width: '100px' }}>[{log.time}]</span>
                            <span style={{ color: 'var(--neon-cyan)', width: '100px', fontWeight: 'bold' }}>{log.agent.toUpperCase()}</span>
                            <span style={{ color: 'var(--text-primary)', flex: 1 }}>
                                <span style={{
                                    color: log.action === 'ACT' ? 'var(--neon-green)' :
                                        log.action === 'SYNC' ? 'var(--neon-cyan)' :
                                            'var(--text-secondary)',
                                    marginRight: '12px',
                                    fontWeight: 'bold'
                                }}>
                                    {log.action}
                                </span>
                                {log.msg}
                            </span>
                        </div>
                    ))}
                    <div ref={streamEndRef} />
                </div>
            </div>

        </div>
    );
}

const HudMetric = ({ icon, label, value, color }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem' }}>
        <span style={{ color: color }}>{icon}</span>
        <span style={{ color: 'var(--text-secondary)' }}>{label}:</span>
        <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>{value}</span>
    </div>
);

const AgentCard = ({ name, data, baseColor }) => {
    const isSleep = data.status === 'SLEEP';
    const isActive = data.status === 'ACT';
    const isSync = data.syncStatus === 'Synchronized';

    return (
        <div
            className={`glass-panel ${isActive ? 'pulsating' : ''} ${data.flash ? 'spirit-sync-flash' : ''}`}
            style={{
                position: 'relative',
                minHeight: '220px',
                display: 'flex',
                flexDirection: 'column',
                border: isSync ? '1px solid var(--neon-cyan)' : 'var(--glass-border)'
            }}
        >
            <div className="spirit-aura" style={{ opacity: isSync ? 1 : 0.3 }} />

            <div style={{ display: 'flex', justifyContent: 'space-between', position: 'relative', zIndex: 1 }}>
                <div>
                    <h2 style={{
                        margin: 0,
                        color: isSync ? 'var(--neon-cyan)' : baseColor,
                        fontFamily: 'Outfit, sans-serif'
                    }}>
                        {name}
                    </h2>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', letterSpacing: '0.05em' }}>
                        {data.designation}
                    </span>
                </div>
                <div style={{
                    backgroundColor: 'rgba(0,0,0,0.3)',
                    padding: '8px',
                    borderRadius: '12px',
                    color: isSleep ? 'var(--text-dim)' : (isSync ? 'var(--neon-cyan)' : baseColor)
                }}>
                    <Brain size={24} />
                </div>
            </div>

            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', zIndex: 1 }}>
                {isActive && (
                    <div style={{ textAlign: 'center' }}>
                        <div className="radiant-text" style={{ fontSize: '2.5rem' }}>ACTIVE</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--neon-green)', marginTop: '4px' }}>Inference Logic Scaling...</div>
                    </div>
                )}
                {isSleep && (
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '2.5rem', color: 'var(--text-dim)', fontWeight: 'bold' }}>STANDBY</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '4px' }}>Subconscious Maintenance</div>
                    </div>
                )}
            </div>

            <div style={{
                marginTop: 'auto',
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '0.75rem',
                position: 'relative',
                zIndex: 1,
                borderTop: '1px solid rgba(255,255,255,0.05)',
                paddingTop: '12px'
            }}>
                <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={12} /> {data.status}
                </span>
                <span style={{ color: isSync ? 'var(--neon-cyan)' : 'var(--text-dim)' }}>
                    {isSync ? 'SYNC: ACTIVE' : 'LOCAL CORE'}
                </span>
            </div>
        </div>
    );
};
