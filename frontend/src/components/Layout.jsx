import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import NotificationsPanel from './NotificationsPanel';

const Layout = ({ children }) => {
  const location = useLocation();
  const isActive = (path) => location.pathname === path ? "aura-nav-item active" : "aura-nav-item";

  return (
    <div className="aura-layout-wrapper">
      {/* Sidebar */}
      <aside className="aura-sidebar">
        <div className="aura-sidebar-header">
          <h1 className="aura-brand">AURA</h1>
        </div>
        <nav className="aura-nav">
          <Link to="/" className={isActive('/')}>
            Dashboard
          </Link>
          <Link to="/claims" className={isActive('/claims')}>
            Claims
          </Link>
          <Link to="/investigations" className={isActive('/investigations')}>
            Investigations
          </Link>
          <Link to="/admin/model-health" className={isActive('/admin/model-health')}>
            Model Health
          </Link>
          <Link to="/upload" className={isActive('/upload')}>
            Upload Claims
          </Link>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="aura-main-content">
        <header className="aura-header">
          <h2 className="aura-page-title">Workspace</h2>
          <div className="aura-header-actions">
            <NotificationsPanel />
            <div className="aura-avatar">
              U
            </div>
          </div>
        </header>
        <div className="aura-content-scroll">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
