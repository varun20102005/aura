import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import Layout from './components/Layout';
import ModelHealthDashboard from './pages/ModelHealthDashboard';
import ClaimsList from './pages/ClaimsList';
import ClaimDetail from './pages/ClaimDetail';
import BulkUpload from './pages/BulkUpload';
import WorkloadDashboard from './pages/WorkloadDashboard';
import Login from './pages/Login';
import api from './api/axios';
import { ShieldAlert, FolderOpen, FileText } from 'lucide-react';

function PlaceholderDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/dashboard/analytics');
      setData(res.data);
      setError(null);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Failed to load dashboard analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', height: '300px', alignItems: 'center', justifyContent: 'center', color: 'var(--aura-text-muted)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
          <div>Loading system analytics...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5', padding: '24px', borderRadius: 'var(--aura-radius)', maxWidth: '600px', margin: '40px auto' }}>
        <h3 style={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          <ShieldAlert size={20} /> Dashboard Telemetry Error
        </h3>
        <p style={{ fontSize: '14px', marginBottom: '16px' }}>{error}</p>
        <button onClick={fetchAnalytics} className="aura-button" style={{ background: 'rgba(255,255,255,0.1)' }}>
          Retry Request
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="aura-dashboard-grid">
        <div className="aura-card aura-stat-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 className="aura-stat-label">Total Claims</h3>
            <p className="aura-stat-value">{data?.total_claims ?? 0}</p>
          </div>
          <FileText size={40} color="var(--aura-accent)" style={{ opacity: 0.8 }} />
        </div>
        <div className="aura-card aura-stat-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 className="aura-stat-label">High Risk Flagged</h3>
            <p className="aura-stat-value danger">{data?.high_risk_claims ?? 0}</p>
          </div>
          <ShieldAlert size={40} color="var(--aura-danger)" style={{ opacity: 0.8 }} />
        </div>
        <div className="aura-card aura-stat-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 className="aura-stat-label">Open Investigations</h3>
            <p className="aura-stat-value warning">{data?.open_investigations ?? 0}</p>
          </div>
          <FolderOpen size={40} color="var(--aura-warning)" style={{ opacity: 0.8 }} />
        </div>
      </div>
      <div className="aura-card mt-8 flex flex-col items-center">
        <h2 className="aura-h2">AURA Platform Ready</h2>
        <p className="aura-text-muted">The core UI scaffolding and API routes are successfully deployed.</p>
      </div>
    </div>
  );
}

function AppContent() {
  const location = useLocation();
  const isLoginPage = location.pathname === '/login';

  if (isLoginPage) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
      </Routes>
    );
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<PlaceholderDashboard />} />
        <Route path="/claims" element={<ClaimsList />} />
        <Route path="/claims/:id" element={<ClaimDetail />} />
        <Route path="/upload" element={<BulkUpload />} />
        <Route path="/investigations" element={<WorkloadDashboard />} />
        <Route path="/admin/model-health" element={<ModelHealthDashboard />} />
      </Routes>
    </Layout>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
