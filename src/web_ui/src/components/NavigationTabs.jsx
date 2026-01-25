/**
 * VoidCat RDC: Sovereign Spirit - NavigationTabs Component
 * =========================================================
 * Date: 2026-01-24
 * 
 * Tab navigation for switching between Dashboard, Memories, Tasks, Sync.
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Brain, Network, Zap } from 'lucide-react';

export default function NavigationTabs() {
    const location = useLocation();

    const tabs = [
        { path: '/', label: 'Dashboard', icon: LayoutDashboard },
        { path: '/memories', label: 'Memories', icon: Brain },
        { path: '/tasks', label: 'Tasks', icon: Network },
        { path: '/sync', label: 'Sync', icon: Zap },
    ];

    return (
        <nav style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            height: '60px',
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(10px)',
            borderBottom: '1px solid rgba(0, 229, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            padding: '0 2rem',
            gap: '2rem',
            zIndex: 1000
        }}>
            <div style={{
                fontSize: '1.2rem',
                fontWeight: 'bold',
                color: 'var(--neon-cyan)',
                marginRight: '2rem'
            }}>
                THE OBSERVATORIUM
            </div>

            {tabs.map(({ path, label, icon: Icon }) => {
                const isActive = location.pathname === path;
                return (
                    <Link
                        key={path}
                        to={path}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '8px 16px',
                            borderRadius: '6px',
                            textDecoration: 'none',
                            color: isActive ? 'var(--neon-cyan)' : 'var(--text-secondary)',
                            backgroundColor: isActive ? 'rgba(0, 229, 255, 0.1)' : 'transparent',
                            border: isActive ? '1px solid var(--neon-cyan)' : '1px solid transparent',
                            transition: 'all 0.2s ease',
                            fontSize: '0.9rem',
                            fontWeight: isActive ? 'bold' : 'normal'
                        }}
                        onMouseEnter={(e) => {
                            if (!isActive) {
                                e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
                                e.target.style.color = 'var(--text-primary)';
                            }
                        }}
                        onMouseLeave={(e) => {
                            if (!isActive) {
                                e.target.style.backgroundColor = 'transparent';
                                e.target.style.color = 'var(--text-secondary)';
                            }
                        }}
                    >
                        <Icon size={18} />
                        {label}
                    </Link>
                );
            })}
        </nav>
    );
}
