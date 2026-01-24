import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, Settings, Activity } from 'lucide-react';
import Dashboard from './pages/Dashboard';

// Inject Google Fonts
const injectFonts = () => {
  const link = document.createElement('link');
  link.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Outfit:wght@600;700&display=swap';
  link.rel = 'stylesheet';
  document.head.appendChild(link);
};

// Placeholder for future modules
const Chat = () => <div className="glass-panel" style={{ margin: '2rem' }}><h2>Comm Link Offline</h2><p>Module under construction.</p></div>;
const Config = () => <div className="glass-panel" style={{ margin: '2rem' }}><h2>Configuration</h2><p>Restricted Access.</p></div>;

function AppShell() {
  useEffect(() => {
    injectFonts();
  }, []);

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      width: '100vw',
      backgroundColor: 'var(--void-bg)',
      color: 'var(--text-primary)',
      overflow: 'hidden'
    }}>
      {/* SIDEBAR */}
      <nav style={{
        width: '72px',
        borderRight: '1px solid var(--void-border)',
        backgroundColor: 'rgba(10, 15, 20, 0.8)',
        backdropFilter: 'blur(20px)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        paddingTop: '24px',
        zIndex: 100,
        boxShadow: '4px 0 24px rgba(0,0,0,0.5)'
      }}>
        {/* LOGO */}
        <div style={{
          marginBottom: '48px',
          color: 'var(--neon-cyan)',
          filter: 'drop-shadow(0 0 10px rgba(0, 229, 255, 0.4))'
        }}>
          <Activity size={32} />
        </div>

        {/* LINKS */}
        <NavItem to="/" icon={<LayoutDashboard size={24} />} title="Dashboard" />
        <NavItem to="/chat" icon={<MessageSquare size={24} />} title="Comm Link" />
        <NavItem to="/settings" icon={<Settings size={24} />} title="Settings" />
      </nav>

      {/* MAIN CONTENT AREA */}
      <main style={{
        flex: 1,
        overflow: 'hidden',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Glacial Cyan Ambient Aura */}
        <div style={{
          position: 'absolute',
          top: '-20%', right: '-10%',
          width: '60%', height: '60%',
          background: 'radial-gradient(circle at center, rgba(0, 229, 255, 0.08) 0%, transparent 60%)',
          pointerEvents: 'none',
          filter: 'blur(80px)',
          zIndex: 0
        }} />

        <div style={{
          position: 'absolute',
          bottom: '-10%', left: '-5%',
          width: '40%', height: '40%',
          background: 'radial-gradient(circle at center, rgba(157, 80, 187, 0.05) 0%, transparent 60%)',
          pointerEvents: 'none',
          filter: 'blur(60px)',
          zIndex: 0
        }} />

        <div style={{ flex: 1, overflowY: 'auto', position: 'relative', zIndex: 1 }}>
          <Outlet />
        </div>
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
