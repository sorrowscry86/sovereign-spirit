import React, { useState, useEffect } from 'react';
import { Activity, RefreshCw, Layers, Shield, Eye, Brain, Cpu, Cloud, Save } from 'lucide-react';

export default function Config() {
    const [agents] = useState(['echo', 'ryuzu', 'beatrice', 'sonmi', 'pandora', 'frobisher']);
    const [selectedAgent, setSelectedAgent] = useState('echo');
    const [actionLog, setActionLog] = useState([]);
    const [loading, setLoading] = useState(false);

    // For manual sync
    const [targetSpirit, setTargetSpirit] = useState('');

    // Bifrost Protocol - Inference routing
    const [inferenceMode, setInferenceMode] = useState('AUTO');
    const [currentRoute, setCurrentRoute] = useState('LOCAL');
    const [routeLoading, setRouteLoading] = useState(false);

    // LLM Provider Config
    const [llmConfig, setLlmConfig] = useState(null);
    const [configSaving, setConfigSaving] = useState(false);

    const logAction = (msg, type = 'info') => {
        setActionLog(prev => [{ id: Date.now(), msg, type }, ...prev]);
    };

    const triggerCycle = async () => {
        setLoading(true);
        try {
            logAction(`Initiating manual cycle for ${selectedAgent}...`, 'pending');
            const res = await fetch(`http://localhost:8000/agent/${selectedAgent}/cycle`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ force: true })
            });
            const data = await res.json();
            if (res.ok) {
                logAction(`Cycle Complete: ${data.action} - ${data.details}`, 'success');
            } else {
                logAction(`Cycle Failed: ${data.detail}`, 'error');
            }
        } catch (err) {
            logAction(`Error: ${err.message}`, 'error');
        } finally {
            setLoading(false);
        }
    };

    const triggerSync = async (spirit) => {
        if (!spirit) return;
        setLoading(true);
        try {
            logAction(`Attempting Spirit Sync: ${selectedAgent} -> ${spirit}...`, 'pending');
            const res = await fetch(`http://localhost:8000/agent/${selectedAgent}/sync`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_spirit: spirit })
            });
            const data = await res.json();
            if (res.ok) {
                logAction(`Sync Successful: Manifesting ${data.synced_to}`, 'success');
            } else {
                logAction(`Sync Failed: ${data.detail}`, 'error');
            }
        } catch (err) {
            logAction(`Error: ${err.message}`, 'error');
        } finally {
            setLoading(false);
        }
    };

    // Fetch current inference config and LLM providers on mount
    useEffect(() => {
        const fetchConfigs = async () => {
            try {
                // Fetch inference routing state
                const infRes = await fetch('/config/inference');
                if (infRes.ok) {
                    const data = await infRes.json();
                    setInferenceMode(data.mode || 'AUTO');
                    setCurrentRoute(data.current_route || 'LOCAL');
                }

                // Fetch detailed LLM provider config
                const llmRes = await fetch('/config/llm');
                if (llmRes.ok) {
                    const data = await llmRes.json();
                    setLlmConfig(data);
                }
            } catch (err) {
                console.error('[Config] Failed to fetch configs:', err);
            }
        };
        fetchConfigs();
    }, []);

    // Save LLM Config
    const saveLlmConfig = async () => {
        setConfigSaving(true);
        try {
            const res = await fetch('/config/llm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(llmConfig)
            });
            if (res.ok) {
                logAction('LLM Model configuration saved successfully', 'success');
            } else {
                const errData = await res.json();
                logAction(`Failed to save LLM config: ${errData.detail || 'Unknown error'}`, 'error');
            }
        } catch (err) {
            logAction(`Error saving LLM config: ${err.message}`, 'error');
        } finally {
            setConfigSaving(false);
        }
    };

    const updateProviderField = (providerId, field, value) => {
        setLlmConfig(prev => ({
            ...prev,
            providers: {
                ...prev.providers,
                [providerId]: {
                    ...prev.providers[providerId],
                    [field]: value
                }
            }
        }));
    };

    // Update inference mode
    const updateInferenceMode = async (mode) => {
        setRouteLoading(true);
        try {
            const res = await fetch('/config/inference', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode })
            });
            if (res.ok) {
                setInferenceMode(mode);
                logAction(`Inference mode set to: ${mode}`, 'success');

                // Refresh current route status
                const statusRes = await fetch('/config/inference');
                if (statusRes.ok) {
                    const data = await statusRes.json();
                    setCurrentRoute(data.current_route || 'LOCAL');
                }
            } else {
                logAction('Failed to update inference mode', 'error');
            }
        } catch (err) {
            logAction(`Error updating inference mode: ${err.message}`, 'error');
        } finally {
            setRouteLoading(false);
        }
    };

    return (
        <div style={{ padding: '2rem', height: '100%', overflowY: 'auto' }}>
            <h1 className="radiant-text" style={{ marginBottom: '2rem' }}>SYSTEM CONFIGURATION</h1>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>

                {/* CONTROL PANEL */}
                <div className="glass-panel" style={{ padding: '24px' }}>
                    <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <Activity size={20} color="var(--neon-green)" />
                            Manual Override
                        </div>
                        {/* Brain Icon Indicator */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }} title={`Currently routing to: ${currentRoute}`}>
                            <Brain
                                size={18}
                                color={currentRoute === 'CLOUD' ? 'var(--neon-cyan)' : 'var(--neon-green)'}
                                style={{ opacity: routeLoading ? 0.5 : 1 }}
                            />
                            <span style={{ color: currentRoute === 'CLOUD' ? 'var(--neon-cyan)' : 'var(--neon-green)' }}>
                                {currentRoute}
                            </span>
                        </div>
                    </h3>

                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '8px', fontSize: '0.9rem' }}>Target Agent Body</label>
                        <select
                            value={selectedAgent}
                            onChange={(e) => setSelectedAgent(e.target.value)}
                            style={{
                                width: '100%',
                                background: 'rgba(0,0,0,0.3)',
                                border: '1px solid var(--void-border)',
                                color: 'var(--text-primary)',
                                padding: '10px',
                                borderRadius: '8px',
                                fontSize: '1rem'
                            }}
                        >
                            {agents.map(a => <option key={a} value={a}>{a.toUpperCase()}</option>)}
                        </select>
                    </div>

                    {/* Bifrost Protocol - Inference Source */}
                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '8px', fontSize: '0.9rem' }}>
                            Inference Source
                            <span style={{ marginLeft: '8px', fontSize: '0.75rem', color: 'var(--text-dim)' }}>(Bifrost Protocol)</span>
                        </label>
                        <select
                            value={inferenceMode}
                            onChange={(e) => updateInferenceMode(e.target.value)}
                            disabled={routeLoading}
                            style={{
                                width: '100%',
                                background: 'rgba(0,0,0,0.3)',
                                border: `1px solid ${inferenceMode === 'AUTO' ? 'var(--neon-cyan)' : inferenceMode === 'LOCAL' ? 'var(--neon-green)' : 'var(--neon-error)'}`,
                                color: inferenceMode === 'AUTO' ? 'var(--neon-cyan)' : inferenceMode === 'LOCAL' ? 'var(--neon-green)' : 'var(--neon-error)',
                                padding: '10px',
                                borderRadius: '8px',
                                fontSize: '0.95rem',
                                cursor: routeLoading ? 'not-allowed' : 'pointer',
                                opacity: routeLoading ? 0.6 : 1
                            }}
                        >
                            <option value="AUTO">🔵 AUTO (Hybrid) - Recommended</option>
                            <option value="LOCAL">🟢 LOCAL ONLY - 100% Privacy</option>
                            <option value="CLOUD">🔴 CLOUD ONLY - High Intelligence</option>
                        </select>
                        <p style={{
                            margin: '8px 0 0 0',
                            fontSize: '0.75rem',
                            color: 'var(--text-dim)',
                            lineHeight: '1.4'
                        }}>
                            {inferenceMode === 'AUTO' && '⚡ Routes simple tasks locally, complex reasoning to cloud'}
                            {inferenceMode === 'LOCAL' && '🔒 All inference stays on your machine (8GB VRAM limit)'}
                            {inferenceMode === 'CLOUD' && '⚠️ All requests sent to cloud API (costs credits)'}
                        </p>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '24px' }}>
                        <ActionButton
                            icon={<RefreshCw size={16} />}
                            label="FORCE PULSE"
                            onClick={triggerCycle}
                            disabled={loading}
                            color="var(--neon-green)"
                        />
                        <ActionButton
                            icon={<Eye size={16} />}
                            label="VIEW STATE"
                            onClick={() => window.open(`http://localhost:8000/agent/${selectedAgent}/state`, '_blank')}
                            color="var(--neon-cyan)"
                        />
                    </div>

                    <h4 style={{ color: 'var(--text-secondary)', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '16px', marginTop: '0' }}>
                        Spirit Sync Protocol
                    </h4>
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <select
                            value={targetSpirit}
                            onChange={(e) => setTargetSpirit(e.target.value)}
                            style={{
                                flex: 1,
                                background: 'rgba(0,0,0,0.3)',
                                border: '1px solid var(--void-border)',
                                color: 'var(--neon-purple)',
                                padding: '8px',
                                borderRadius: '8px'
                            }}
                        >
                            <option value="">Select Spirit to Channel...</option>
                            <option value="ryuzu">Ryuzu (Sculptor)</option>
                            <option value="roland">Roland (Strategist)</option>
                            <option value="albedo">Albedo (Architect)</option>
                            <option value="echo">Echo (Neutral)</option>
                        </select>
                        <ActionButton
                            icon={<Layers size={16} />}
                            label="SYNC"
                            onClick={() => triggerSync(targetSpirit)}
                            disabled={loading || !targetSpirit}
                            color="var(--neon-purple)"
                        />
                    </div>
                </div>

                {/* BIFROST MODEL ARCHITECT */}
                <div className="glass-panel" style={{ padding: '24px', gridColumn: '1 / -1' }}>
                    <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--neon-purple)' }}>
                        <Cpu size={20} />
                        Bifrost Model Architect
                    </h3>

                    {!llmConfig ? (
                        <div style={{ color: 'var(--text-dim)', padding: '20px', textAlign: 'center' }}>
                            Decrypting configuration stream...
                        </div>
                    ) : (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '24px' }}>
                            {/* LOCAL SECTOR */}
                            <div style={{ padding: '16px', borderRadius: '12px', border: '1px solid rgba(0, 255, 133, 0.1)', background: 'rgba(0,0,0,0.2)' }}>
                                <h4 style={{ margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--neon-green)' }}>
                                    <Cpu size={16} /> LOCAL CORE
                                </h4>

                                {['ollama_local', 'lm_studio'].map(pid => llmConfig.providers[pid] && (
                                    <div key={pid} style={{ marginBottom: '16px', padding: '12px', borderRadius: '8px', background: llmConfig.active_provider === pid ? 'rgba(0,255,133,0.05)' : 'transparent', border: llmConfig.active_provider === pid ? '1px solid var(--neon-green)' : '1px solid transparent' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                            <span style={{ fontWeight: '600', fontSize: '0.9rem' }}>{pid.replace('_', ' ').toUpperCase()}</span>
                                            {llmConfig.active_provider === pid && <span style={{ fontSize: '0.7rem', color: 'var(--neon-green)' }}>[ACTIVE]</span>}
                                        </div>
                                        <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr', gap: '8px', alignItems: 'center' }}>
                                            <label style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Model:</label>
                                            <input
                                                value={llmConfig.providers[pid].model}
                                                onChange={(e) => updateProviderField(pid, 'model', e.target.value)}
                                                style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--void-border)', color: 'white', padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem' }}
                                            />
                                            <label style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Endpoint:</label>
                                            <input
                                                value={llmConfig.providers[pid].endpoint}
                                                onChange={(e) => updateProviderField(pid, 'endpoint', e.target.value)}
                                                style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--void-border)', color: 'white', padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem' }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* CLOUD SECTOR */}
                            <div style={{ padding: '16px', borderRadius: '12px', border: '1px solid rgba(0, 217, 255, 0.1)', background: 'rgba(0,0,0,0.2)' }}>
                                <h4 style={{ margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--neon-cyan)' }}>
                                    <Cloud size={16} /> CLOUD BRIDGE
                                </h4>

                                {['openrouter', 'openai'].map(pid => llmConfig.providers[pid] && (
                                    <div key={pid} style={{ marginBottom: '16px', padding: '12px', borderRadius: '8px', background: llmConfig.active_provider === pid ? 'rgba(0,217,255,0.05)' : 'transparent', border: llmConfig.active_provider === pid ? '1px solid var(--neon-cyan)' : '1px solid transparent' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                            <span style={{ fontWeight: '600', fontSize: '0.9rem' }}>{pid.toUpperCase()}</span>
                                            {llmConfig.active_provider === pid && <span style={{ fontSize: '0.7rem', color: 'var(--neon-cyan)' }}>[ACTIVE]</span>}
                                        </div>
                                        <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr', gap: '8px', alignItems: 'center' }}>
                                            <label style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Model:</label>
                                            <input
                                                value={llmConfig.providers[pid].model}
                                                onChange={(e) => updateProviderField(pid, 'model', e.target.value)}
                                                style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--void-border)', color: 'white', padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem' }}
                                            />
                                            <label style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>API Key:</label>
                                            <input
                                                type="password"
                                                value={llmConfig.providers[pid].api_key || ''}
                                                onChange={(e) => updateProviderField(pid, 'api_key', e.target.value)}
                                                placeholder={llmConfig.providers[pid].api_key === '********' ? '********' : 'Enter API Key...'}
                                                style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--void-border)', color: 'white', padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem' }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end' }}>
                        <ActionButton
                            icon={<Save size={16} />}
                            label={configSaving ? "TRANSMITTING..." : "SAVE ARCHITECTURE"}
                            onClick={saveLlmConfig}
                            disabled={configSaving || !llmConfig}
                            color="var(--neon-purple)"
                        />
                    </div>
                </div>

                {/* SECURITY PANEL */}
                <div className="glass-panel" style={{ padding: '24px' }}>
                    <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Shield size={20} color="var(--neon-error)" />
                        Wards & Limits
                    </h3>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
                        <p><strong>API Rate Limiting:</strong> ACTIVE (60/min)</p>
                        <p><strong>Valence Stripping:</strong> ACTIVE (Level 3)</p>
                        <p><strong>Auth Mode:</strong> PUBLIC (Dev Mode)</p>
                        <div style={{ marginTop: '20px', padding: '12px', background: 'rgba(255, 100, 100, 0.1)', borderRadius: '8px', borderLeft: '3px solid var(--neon-error)' }}>
                            Env: DEVELOPMENT<br />
                            Port: 8000 (Middleware) / 8090 (Vector)
                        </div>
                    </div>
                </div>

                {/* ACTION LOG */}
                <div className="glass-panel" style={{ gridColumn: '1 / -1', maxHeight: '300px', overflowY: 'auto', padding: '20px' }}>
                    <h3 style={{ marginTop: 0, fontSize: '0.9rem', color: 'var(--text-dim)' }}>SYSTEM OPERATIONS LOG</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                        {actionLog.length === 0 && <span style={{ color: 'var(--text-dim)' }}>No recent admin actions.</span>}
                        {actionLog.map(log => (
                            <div key={log.id} style={{
                                color: log.type === 'error' ? 'var(--neon-error)' : log.type === 'success' ? 'var(--neon-green)' : 'var(--text-primary)'
                            }}>
                                &gt; {log.msg}
                            </div>
                        ))}
                    </div>
                </div>

            </div>
        </div>
    );
}

const ActionButton = ({ icon, label, onClick, disabled, color }) => (
    <button
        onClick={onClick}
        disabled={disabled}
        style={{
            background: disabled ? 'rgba(255,255,255,0.05)' : `rgba(0,0,0,0.3)`,
            border: `1px solid ${disabled ? 'transparent' : color}`,
            color: disabled ? 'gray' : color,
            padding: '10px',
            borderRadius: '8px',
            cursor: disabled ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
            fontWeight: '600',
            transition: 'all 0.2s'
        }}
    >
        {icon} {label}
    </button>
);
