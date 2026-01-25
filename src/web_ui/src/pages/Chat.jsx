import React, { useState, useEffect, useRef } from 'react';
import { Send, Terminal, Cpu, MessageSquare } from 'lucide-react';
import { useSocket } from '../context/SocketContext';

export default function Chat() {
    const { socketStatus, lastMessage } = useSocket();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [targetAgent, setTargetAgent] = useState('echo');
    const [sending, setSending] = useState(false);

    const scrollRef = useRef(null);

    // Auto-scroll
    useEffect(() => {
        scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Listen for echoes from the void
    useEffect(() => {
        if (lastMessage) {
            // If the heartbeat contains a "thought", treat it as a system log/message
            if (lastMessage.type === 'HEARTBEAT' && lastMessage.data.thought) {
                addMessage({
                    source: lastMessage.data.agent_id,
                    content: `[${lastMessage.data.action}] ${lastMessage.data.thought}`,
                    type: 'system',
                    timestamp: new Date().toLocaleTimeString()
                });
            }
        }
    }, [lastMessage]);

    const addMessage = (msg) => {
        setMessages(prev => [...prev.slice(-99), { id: Date.now(), ...msg }]);
    };

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const payload = {
            message: input,
            source: "admin_ui"
        };

        setSending(true);
        try {
            // Log local user message
            addMessage({
                source: 'user',
                content: input,
                type: 'user',
                timestamp: new Date().toLocaleTimeString()
            });

            // Fire the stimuli
            const res = await fetch(`http://localhost:8000/agent/${targetAgent}/stimuli`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error("Stimuli Rejected");

            setInput('');
        } catch (err) {
            addMessage({
                source: 'system',
                content: `Error: ${err.message}`,
                type: 'error',
                timestamp: new Date().toLocaleTimeString()
            });
        } finally {
            setSending(false);
        }
    };

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: '2rem', gap: '20px' }}>
            {/* HEADER */}
            <div className="glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1 className="radiant-text" style={{ margin: 0, fontSize: '1.5rem' }}>DIRECT LINK REPOSITORY</h1>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Target:</span>
                    <select
                        value={targetAgent}
                        onChange={(e) => setTargetAgent(e.target.value)}
                        style={{
                            background: 'rgba(0,0,0,0.5)',
                            border: '1px solid var(--void-border)',
                            color: 'var(--neon-cyan)',
                            padding: '5px 10px',
                            borderRadius: '5px',
                            fontFamily: 'monospace'
                        }}
                    >
                        <option value="echo">ECHO (The Vessel)</option>
                        <option value="ryuzu">RYUZU (The Sculptor)</option>
                        <option value="beatrice">BEATRICE (The Librarian)</option>
                        <option value="sonmi">SONMI (The Arbiter)</option>
                    </select>
                </div>
            </div>

            {/* CHAT WINDOW */}
            <div className="glass-panel" style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', padding: '20px' }}>
                {messages.length === 0 && (
                    <div style={{ textAlign: 'center', color: 'var(--text-dim)', marginTop: '20%' }}>
                        <Terminal size={48} style={{ opacity: 0.2, marginBottom: '20px' }} />
                        <p>No active neural pathways...</p>
                    </div>
                )}

                {messages.map(msg => (
                    <div key={msg.id} style={{
                        alignSelf: msg.type === 'user' ? 'flex-end' : 'flex-start',
                        maxWidth: '70%',
                        backgroundColor: msg.type === 'user' ? 'rgba(0, 229, 255, 0.1)' : 'rgba(255, 255, 255, 0.05)',
                        border: msg.type === 'user' ? '1px solid rgba(0, 229, 255, 0.3)' : '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '12px',
                        padding: '12px 16px',
                        color: msg.type === 'error' ? 'var(--neon-error)' : 'var(--text-primary)'
                    }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '4px', display: 'flex', justifyContent: 'space-between', minWidth: '120px' }}>
                            <span style={{ fontWeight: 'bold', color: msg.type === 'user' ? 'var(--neon-cyan)' : 'var(--neon-purple)' }}>
                                {msg.source.toUpperCase()}
                            </span>
                            <span>{msg.timestamp}</span>
                        </div>
                        <div style={{ lineHeight: '1.5', fontSize: '0.95rem' }}>{msg.content}</div>
                    </div>
                ))}
                <div ref={scrollRef} />
            </div>

            {/* INPUT AREA */}
            <form onSubmit={handleSend} className="glass-panel" style={{ display: 'flex', gap: '10px', padding: '15px' }}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={`Transmit stimuli to ${targetAgent.toUpperCase()}...`}
                    style={{
                        flex: 1,
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-primary)',
                        fontSize: '1rem',
                        outline: 'none',
                        fontFamily: 'Inter, sans-serif'
                    }}
                />
                <button
                    type="submit"
                    disabled={sending}
                    style={{
                        background: sending ? 'gray' : 'var(--neon-cyan)',
                        border: 'none',
                        borderRadius: '8px',
                        padding: '0 20px',
                        color: 'black',
                        fontWeight: 'bold',
                        cursor: sending ? 'not-allowed' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                    }}
                >
                    {sending ? <Cpu size={18} className="spin" /> : <Send size={18} />}
                    TRANSMIT
                </button>
            </form>
        </div>
    );
}
