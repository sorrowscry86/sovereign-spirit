
import React, { useState, useEffect } from 'react';
import { Play, Square, Wand2 } from 'lucide-react';

/**
 * DemoController
 * A hidden/overlay component that allows the user to simulate activity
 * for investor demonstrations.
 */
export default function DemoController({ onInjectEvent }) {
    const [isActive, setIsActive] = useState(false);
    const [scenario, setScenario] = useState('idle');

    useEffect(() => {
        let interval;
        if (isActive) {
            interval = setInterval(() => {
                // Generate fake events based on scenario
                const agents = ['ryuzu', 'echo', 'beatrice', 'roland'];
                const actions = ['ACT', 'SLEEP', 'THOUGHT'];
                const thoughts = [
                    "Analyzing market trends...",
                    "Optimizing memory vectors...",
                    "Detecting anomaly in Sector 7...",
                    "Sovereignty integrity check complete.",
                    "User intent predicted with 98% confidence."
                ];

                const randomAgent = agents[Math.floor(Math.random() * agents.length)];
                const randomAction = actions[Math.floor(Math.random() * actions.length)];
                const randomThought = thoughts[Math.floor(Math.random() * thoughts.length)];

                onInjectEvent({
                    type: 'HEARTBEAT',
                    data: {
                        agent_id: randomAgent,
                        action: randomAction,
                        thought: randomThought,
                        timestamp: new Date().toISOString()
                    }
                });

            }, 3000); // Fast pulse for demo (every 3s)
        }
        return () => clearInterval(interval);
    }, [isActive, onInjectEvent]);

    if (!isActive) {
        return (
            <button
                onClick={() => setIsActive(true)}
                title="Activate Demo Mode"
                style={{
                    position: 'fixed',
                    bottom: '20px',
                    right: '20px',
                    background: 'rgba(0,0,0,0.5)',
                    border: '1px solid var(--neon-cyan)',
                    color: 'var(--neon-cyan)',
                    borderRadius: '50%',
                    width: '40px',
                    height: '40px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    zIndex: 9999,
                    opacity: 0.3
                }}
            >
                <Wand2 size={20} />
            </button>
        );
    }

    return (
        <div style={{
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            background: 'rgba(10, 15, 20, 0.95)',
            border: '1px solid var(--neon-cyan)',
            borderRadius: '12px',
            padding: '16px',
            zIndex: 9999,
            width: '240px',
            boxShadow: '0 0 20px rgba(0, 229, 255, 0.2)'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <span style={{ color: 'var(--neon-cyan)', fontWeight: 'bold' }}>DEMO MODE</span>
                <button
                    onClick={() => setIsActive(false)}
                    style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
                >
                    ✕
                </button>
            </div>

            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                Simulating high-frequency heartbeat events for presentation purposes.
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
                <button
                    style={{
                        flex: 1,
                        background: 'rgba(0, 229, 255, 0.1)',
                        border: '1px solid var(--neon-cyan)',
                        color: 'var(--neon-cyan)',
                        padding: '8px',
                        borderRadius: '4px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '4px'
                    }}
                >
                    <Play size={14} /> Running
                </button>
            </div>
        </div>
    );
}
