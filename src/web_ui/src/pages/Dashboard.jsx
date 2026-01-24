
import React, { useState, useEffect, useRef } from 'react';
import { Wifi, Database, Brain, Zap, Clock } from 'lucide-react';

const WEBSOCKET_URL = "ws://localhost:8000/ws";

export default function Dashboard() {
    const [socketStatus, setSocketStatus] = useState('disconnected');
    const [pulseStream, setPulseStream] = useState([]);
    const [agents, setAgents] = useState({
        echo: { status: 'SLEEP', designation: 'The Vessel', lastPulse: null, syncStatus: 'Normal' },
        beatrice: { status: 'SLEEP', designation: 'The Librarian', lastPulse: null, syncStatus: 'Normal' },
        ryuzu: { status: 'SLEEP', designation: 'The Sculptor', lastPulse: null, syncStatus: 'Normal' }
    });

    const wsRef = useRef(null);
    const streamEndRef = useRef(null);

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

        // Update Agent State
        setAgents(prev => ({
            ...prev,
            [data.agent_id]: {
                ...prev[data.agent_id],
                status: data.action,
                lastPulse: Date.now()
            }
        }));
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

        setAgents(prev => ({
            ...prev,
            [data.agent_id]: {
                ...prev[data.agent_id],
                designation: data.designation,
                syncStatus: 'Synchronized',
                flash: true
            }
        }));

        // Reset flash after animation
        setTimeout(() => {
            setAgents(prev => ({
                ...prev,
                [data.agent_id]: { ...prev[data.agent_id], flash: false }
            }));
        }, 800);
    };

    // WebSocket Connection
    useEffect(() => {
        const connect = () => {
            console.log("Connecting to Nervous System...");
            const ws = new WebSocket(WEBSOCKET_URL);

            ws.onopen = () => setSocketStatus('connected');
            ws.onclose = () => {
                setSocketStatus('disconnected');
                setTimeout(connect, 3000); // Auto-reconnect
            };

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.type === "HEARTBEAT") {
                    handleHeartbeat(msg.data);
                } else if (msg.type === "SYNC_UPDATE") {
                    handleSyncUpdate(msg.data);
                }
            };

            wsRef.current = ws;
        };

        connect();
        return () => wsRef.current?.close();
    }, []);

    return (
        <div style={{ padding: '2rem', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>

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
                </div>
            </div>

            {/* AGENT GRID */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: '24px'
            }}>
                <AgentCard id="echo" name="Echo" data={agents.echo} baseColor="var(--neon-green)" />
                <AgentCard id="beatrice" name="Beatrice" data={agents.beatrice} baseColor="var(--neon-cyan)" />
                <AgentCard id="ryuzu" name="Ryuzu" data={agents.ryuzu} baseColor="var(--neon-purple)" />
            </div>

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
