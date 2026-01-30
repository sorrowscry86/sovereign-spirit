import React, { useState, useEffect, useRef } from 'react';
import { Send, MessageSquare, User, Bot } from 'lucide-react';

const API_BASE = "http://localhost:8000";

export default function Chat() {
    const [messages, setMessages] = useState([
        {
            id: 1,
            sender: 'system',
            content: 'Comm Link Established. Select an agent to begin communication.',
            timestamp: new Date()
        }
    ]);
    const [inputMessage, setInputMessage] = useState('');
    const [selectedAgent, setSelectedAgent] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const agents = [
        { id: 'echo', name: 'Echo', designation: 'The Vessel' },
        { id: 'beatrice', name: 'Beatrice', designation: 'The Librarian' },
        { id: 'ryuzu', name: 'Ryuzu', designation: 'The Sculptor' }
    ];

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = async () => {
        if (!inputMessage.trim() || !selectedAgent) return;

        const message = {
            id: Date.now(),
            sender: 'user',
            content: inputMessage,
            timestamp: new Date(),
            agent: selectedAgent
        };

        setMessages(prev => [...prev, message]);
        setInputMessage('');
        setIsLoading(true);

        try {
            const response = await fetch(`${API_BASE}/agent/${selectedAgent}/stimuli`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: inputMessage,
                    source: 'web_ui'
                })
            });

            if (response.ok) {
                // Message sent successfully
                // In a real implementation, responses would come via WebSocket or polling
                setMessages(prev => [...prev, {
                    id: Date.now() + 1,
                    sender: 'system',
                    content: `Message delivered to ${selectedAgent.toUpperCase()}. Awaiting response...`,
                    timestamp: new Date()
                }]);
            } else {
                throw new Error('Failed to send message');
            }
        } catch (error) {
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                sender: 'system',
                content: `Error: Failed to send message to ${selectedAgent.toUpperCase()}.`,
                timestamp: new Date()
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <div style={{ padding: '2rem', height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div className="glass-panel" style={{ marginBottom: '20px' }}>
                <h1 className="radiant-text" style={{ margin: 0, fontSize: '1.5rem' }}>COMM LINK // DIRECT INTERFACE</h1>
                <p style={{ margin: '8px 0 0 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                    Establish direct communication with Sovereign agents
                </p>
            </div>

            {/* Agent Selector */}
            <div className="glass-panel" style={{ marginBottom: '20px' }}>
                <h3 style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                    SELECT AGENT
                </h3>
                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                    {agents.map(agent => (
                        <button
                            key={agent.id}
                            onClick={() => setSelectedAgent(agent.id)}
                            style={{
                                padding: '12px 16px',
                                border: selectedAgent === agent.id ? '1px solid var(--neon-cyan)' : '1px solid var(--void-border)',
                                backgroundColor: selectedAgent === agent.id ? 'rgba(0, 229, 255, 0.1)' : 'rgba(10, 15, 20, 0.5)',
                                color: selectedAgent === agent.id ? 'var(--neon-cyan)' : 'var(--text-primary)',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                fontSize: '0.9rem'
                            }}
                        >
                            <div style={{ fontWeight: 'bold' }}>{agent.name}</div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{agent.designation}</div>
                        </button>
                    ))}
                </div>
            </div>

            {/* Messages Area */}
            <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', marginBottom: '20px' }}>
                <div style={{ padding: '16px', borderBottom: '1px solid var(--void-border)' }}>
                    <h3 style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                        COMMUNICATION LOG
                    </h3>
                </div>

                <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
                    {messages.map(message => (
                        <div key={message.id} style={{
                            display: 'flex',
                            marginBottom: '16px',
                            alignItems: message.sender === 'user' ? 'flex-end' : 'flex-start'
                        }}>
                            <div style={{
                                maxWidth: '70%',
                                padding: '12px 16px',
                                borderRadius: '12px',
                                backgroundColor: message.sender === 'user'
                                    ? 'var(--neon-cyan)'
                                    : message.sender === 'system'
                                        ? 'rgba(157, 80, 187, 0.2)'
                                        : 'rgba(10, 15, 20, 0.8)',
                                color: message.sender === 'user' ? 'rgba(10, 15, 20, 0.9)' : 'var(--text-primary)',
                                border: message.sender === 'system' ? '1px solid var(--neon-purple)' : 'none'
                            }}>
                                {message.sender !== 'user' && (
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px',
                                        marginBottom: '8px',
                                        fontSize: '0.8rem',
                                        color: 'var(--text-secondary)'
                                    }}>
                                        {message.sender === 'system' ? <MessageSquare size={14} /> : <Bot size={14} />}
                                        <span>{message.sender === 'system' ? 'SYSTEM' : message.agent?.toUpperCase()}</span>
                                    </div>
                                )}
                                <div>{message.content}</div>
                                <div style={{
                                    fontSize: '0.7rem',
                                    color: message.sender === 'user' ? 'rgba(10, 15, 20, 0.6)' : 'var(--text-dim)',
                                    marginTop: '4px',
                                    textAlign: 'right'
                                }}>
                                    {message.timestamp.toLocaleTimeString()}
                                </div>
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input Area */}
            <div className="glass-panel" style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={selectedAgent ? `Message ${selectedAgent.toUpperCase()}...` : "Select an agent first"}
                    disabled={!selectedAgent || isLoading}
                    style={{
                        flex: 1,
                        padding: '12px 16px',
                        backgroundColor: 'rgba(10, 15, 20, 0.5)',
                        border: '1px solid var(--void-border)',
                        borderRadius: '8px',
                        color: 'var(--text-primary)',
                        fontSize: '1rem',
                        outline: 'none'
                    }}
                />
                <button
                    onClick={sendMessage}
                    disabled={!inputMessage.trim() || !selectedAgent || isLoading}
                    style={{
                        padding: '12px 16px',
                        backgroundColor: 'var(--neon-cyan)',
                        border: 'none',
                        borderRadius: '8px',
                        color: 'rgba(10, 15, 20, 0.9)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontWeight: 'bold',
                        opacity: (!inputMessage.trim() || !selectedAgent || isLoading) ? 0.5 : 1
                    }}
                >
                    <Send size={16} />
                    {isLoading ? 'SENDING...' : 'SEND'}
                </button>
            </div>
        </div>
    );
}
