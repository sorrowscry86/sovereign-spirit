
import React, { useState, useEffect, useRef } from 'react';
import { Wifi, Database, Brain, Zap, Clock } from 'lucide-react';

const WEBSOCKET_URL = "ws://localhost:8000/ws";

export default function Dashboard() {
    const [socketStatus, setSocketStatus] = useState('disconnected');
    const [pulseStream, setPulseStream] = useState([]);
    const [agents, setAgents] = useState({
        echo: { status: 'SLEEP', lastPulse: null },
        beatrice: { status: 'SLEEP', lastPulse: null },
        ryuzu: { status: 'SLEEP', lastPulse: null }
    });

    const wsRef = useRef(null);
    const streamEndRef = useRef(null);

    // Auto-scroll log
    useEffect(() => {
        streamEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [pulseStream]);

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
                }
            };

            wsRef.current = ws;
        };

        connect();
        return () => wsRef.current?.close();
    }, []);

    const handleHeartbeat = (data) => {
        // Update Log Stream
        const logEntry = {
            id: Date.now(),
            time: new Date().toLocaleTimeString(),
            agent: data.agent_id,
            action: data.action,
            msg: data.thought || "Pulse Detected"
        };
        setPulseStream(prev => [...prev.slice(-49), logEntry]); // Keep last 50

        // Update Agent State
        setAgents(prev => ({
            ...prev,
            [data.agent_id]: {
                status: data.action,
                lastPulse: Date.now()
            }
        }));
    };

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
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
                <AgentCard name="Echo" role="The Vessel" data={agents.echo} color="var(--neon-green)" />
                <AgentCard name="Beatrice" role="The Librarian" data={agents.beatrice} color="var(--neon-cyan)" />
                <AgentCard name="Ryuzu" role="The Sculptor" data={agents.ryuzu} color="var(--neon-purple)" />
            </div>

            {/* PULSE STREAM */}
            <div className="glass-panel" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <h3 style={{ margin: '0 0 10px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', textTransform: 'uppercase' }}>
                    Pulse Stream // Real-Time Telemetry
                </h3>

                <div style={{ flex: 1, overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                    {pulseStream.length === 0 && <div style={{ color: 'var(--text-dim)', padding: '20px' }}>Waiting for signal...</div>}

                    {pulseStream.map(log => (
                        <div key={log.id} style={{ display: 'flex', padding: '4px 0', borderBottom: '1px solid #1f242d' }}>
                            <span style={{ color: 'var(--text-dim)', width: '100px' }}>[{log.time}]</span>
                            <span style={{ color: 'var(--neon-cyan)', width: '80px' }}>{log.agent.toUpperCase()}</span>
                            <span style={{ color: 'var(--text-primary)', flex: 1 }}>
                                <span style={{ color: log.action === 'ACT' ? 'var(--neon-green)' : 'var(--text-secondary)', marginRight: '10px' }}>
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

const AgentCard = ({ name, role, data, color }) => {
    const isSleep = data.status === 'SLEEP';
    const isActive = data.status === 'ACT';

    return (
        <div className="glass-panel" style={{ position: 'relative', minHeight: '180px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <div>
                    <h2 style={{ margin: 0, color: color }}>{name}</h2>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{role}</span>
                </div>
                <Brain size={24} color={isSleep ? 'var(--text-dim)' : color} className={isActive ? 'pulsating' : ''} />
            </div>

            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {isActive && <div style={{ fontSize: '2rem', color: color }}>Processing</div>}
                {isSleep && <div style={{ fontSize: '2rem', color: 'var(--text-dim)' }}>Standby</div>}
            </div>

            <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Status: {data.status}</span>
                {/* <span style={{ color: 'var(--text-dim)' }}>ID: {data.lastPulse || '-'}</span> */}
            </div>
        </div>
    );
};
