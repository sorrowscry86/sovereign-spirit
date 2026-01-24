
import React from 'react';
import { BrowserRouter, Routes, Route, NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, Settings, Activity } from 'lucide-react';
import Dashboard from './pages/Dashboard';

// Placeholder for future modules
const Chat = () => <div className="glass-panel" style={{ margin: '2rem' }}><h2>Comm Link Offline</h2><p>Module under construction.</p></div>;
const Config = () => <div className="glass-panel" style={{ margin: '2rem' }}><h2>Configuration</h2><p>Restricted Access.</p></div>;

function AppShell() {
  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw' }}>
      {/* SIDEBAR */}
      <nav style={{
        width: '64px',
        borderRight: 'var(--void-border)',
        backgroundColor: 'var(--void-surface)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        paddingTop: '20px',
        zIndex: 10
      }}>
        {/* LOGO */}
        <div style={{ marginBottom: '40px', color: 'var(--neon-cyan)' }}>
          <Activity size={32} />
        </div>

        {/* LINKS */}
        <NavItem to="/" icon={<LayoutDashboard size={24} />} title="Dashboard" />
        <NavItem to="/chat" icon={<MessageSquare size={24} />} title="Comm Link" />
        <NavItem to="/settings" icon={<Settings size={24} />} title="Settings" />
      </nav>

      {/* MAIN CONTENT AREA */}
      <main style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        {/* Background Ambient Glow */}
        <div style={{
          position: 'absolute',
          top: '-50%', left: '-50%',
          width: '200%', height: '200%',
          background: 'radial-gradient(circle at center, rgba(88, 166, 255, 0.05) 0%, transparent 50%)',
          pointerEvents: 'none'
        }} />

        <Outlet />
      </main>
    </div>
  );
}

const NavItem = ({ to, icon, title }) => (
  <NavLink
    to={to}
    title={title}
    style={({ isActive }) => ({
      marginBottom: '24px',
      color: isActive ? 'var(--neon-cyan)' : 'var(--text-secondary)',
      transition: 'color 0.2s',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '40px',
      width: '40px',
      borderRadius: '8px',
      backgroundColor: isActive ? 'rgba(88, 166, 255, 0.1)' : 'transparent',
    })}
  >
    {icon}
  </NavLink>
);

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/settings" element={<Config />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
