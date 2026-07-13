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
import { ShieldAlert, Network, DollarSign, CheckCircle2, Filter, Calendar, History, Zap } from 'lucide-react';
import { styled } from './stitches.config';

const DashboardSection = styled('section', {
  padding: '32px',
  display: 'flex',
  flexDirection: 'column',
  gap: '32px',
});

const SectionHeader = styled('div', {
  display: 'flex',
  alignItems: 'flex-end',
  justifyContent: 'space-between',
});

const TitleGroup = styled('div', {
  display: 'flex',
  flexDirection: 'column',
});

const Title = styled('h2', {
  fontSize: '$headlineLg',
  fontWeight: '700',
  color: '$textPrimary',
  letterSpacing: '-0.01em',
});

const Subtitle = styled('p', {
  fontSize: '$bodyMd',
  color: '$textSecondary',
});

const ActionGroup = styled('div', {
  display: 'flex',
  gap: '16px',
});

const ActionButton = styled('button', {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  padding: '10px 20px',
  borderRadius: '$xl',
  border: '1px solid $border',
  background: 'rgba(255, 255, 255, 0.05)',
  color: '$textPrimary',
  fontSize: '11px',
  textTransform: 'uppercase',
  fontWeight: '600',
  letterSpacing: '0.05em',
  cursor: 'pointer',
  transition: '$base',
  '&:hover': {
    background: 'rgba(255, 255, 255, 0.1)',
    borderColor: '$textSecondary',
  },
  variants: {
    primaryHover: {
      true: {
        '&:hover': {
          borderColor: '$accent',
          color: '$accent',
        }
      }
    }
  }
});

const StatsGrid = styled('div', {
  display: 'grid',
  gridTemplateColumns: 'repeat(1, 1fr)',
  gap: '24px',
  '@media (min-width: 768px)': {
    gridTemplateColumns: 'repeat(2, 1fr)',
  },
  '@media (min-width: 1024px)': {
    gridTemplateColumns: 'repeat(4, 1fr)',
  },
});

const GlassCard = styled('div', {
  background: '$surface',
  border: '1px solid $border',
  borderRadius: '$xl',
  padding: '32px',
  backdropFilter: 'blur(24px)',
  position: 'relative',
  overflow: 'hidden',
  transition: '$base',
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: '1px',
    background: 'linear-gradient(90deg, transparent, rgba(173, 198, 255, 0.3), transparent)',
  },
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: '$cardHover',
    borderColor: 'rgba(255,255,255,0.15)',
  }
});

const CardHeader = styled('div', {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  marginBottom: '24px',
});

const IconBox = styled('div', {
  padding: '12px',
  borderRadius: '$xl',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  variants: {
    color: {
      primary: { background: 'rgba(173, 198, 255, 0.1)', color: '$accent' },
      secondary: { background: 'rgba(194, 198, 214, 0.1)', color: '$textSecondary' },
      success: { background: 'rgba(74, 222, 128, 0.1)', color: '$success' },
      danger: { background: 'rgba(255, 180, 171, 0.1)', color: '$danger' },
    }
  }
});

const StatTrend = styled('span', {
  fontSize: '10px',
  fontWeight: '700',
  textTransform: 'uppercase',
  variants: {
    color: {
      success: { color: '$success' },
      primary: { color: '$accent' },
      danger: { color: '$danger' },
    }
  }
});

const StatLabel = styled('p', {
  fontSize: '10px',
  color: '$textSecondary',
  textTransform: 'uppercase',
  letterSpacing: '0.1em',
  marginBottom: '8px',
});

const StatValue = styled('h3', {
  fontSize: '$displayLg',
  fontWeight: '700',
  color: '$textPrimary',
  letterSpacing: '-0.02em',
});

const ProgressBarContainer = styled('div', {
  marginTop: '24px',
  width: '100%',
  height: '6px',
  background: 'rgba(255,255,255,0.05)',
  borderRadius: '$round',
  overflow: 'hidden',
  display: 'flex',
  gap: '4px',
});

const ProgressBarFill = styled('div', {
  height: '100%',
  borderRadius: '$round',
  variants: {
    color: {
      primary: { background: '$accent' },
      success: { background: '$success' },
      neutral: { background: 'rgba(255,255,255,0.1)' }
    }
  }
});

const ContentGrid = styled('div', {
  display: 'grid',
  gridTemplateColumns: 'repeat(1, 1fr)',
  gap: '24px',
  '@media (min-width: 1024px)': {
    gridTemplateColumns: 'repeat(3, 1fr)',
  }
});

const ActivityCard = styled(GlassCard, {
  gridColumn: '1 / -1',
  padding: 0,
  display: 'flex',
  flexDirection: 'column',
  '@media (min-width: 1024px)': {
    gridColumn: 'span 2 / span 2',
  }
});

const ActivityHeader = styled('div', {
  padding: '32px',
  borderBottom: '1px solid $border',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  background: 'rgba(0,0,0,0.2)',
});

const ActivityTitle = styled('h3', {
  fontSize: '$bodyMd',
  fontWeight: '700',
  color: '$textPrimary',
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
});

const ExportButton = styled('button', {
  background: 'none',
  border: 'none',
  color: '$accent',
  fontSize: '11px',
  fontWeight: '700',
  textTransform: 'uppercase',
  cursor: 'pointer',
  '&:hover': {
    textDecoration: 'underline',
  }
});

const TableContainer = styled('div', {
  overflowX: 'auto',
});

const Table = styled('table', {
  width: '100%',
  textAlign: 'left',
  borderCollapse: 'collapse',
});

const Th = styled('th', {
  padding: '20px 32px',
  fontSize: '11px',
  textTransform: 'uppercase',
  color: '$textSecondary',
  letterSpacing: '0.05em',
  borderBottom: '1px solid $border',
  background: 'rgba(0,0,0,0.1)',
});

const Td = styled('td', {
  padding: '20px 32px',
  borderBottom: '1px solid $border',
  fontSize: '$bodySm',
});

const Tr = styled('tr', {
  transition: '$base',
  '&:hover': {
    background: 'rgba(255,255,255,0.02)',
  },
  '&:last-child td': {
    borderBottom: 'none',
  }
});

const Badge = styled('span', {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
  padding: '4px 12px',
  borderRadius: '$round',
  fontSize: '10px',
  fontWeight: '700',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  variants: {
    status: {
      complete: { background: 'rgba(74, 222, 128, 0.1)', color: '$success' },
      authorized: { background: 'rgba(173, 198, 255, 0.1)', color: '$accent' },
      pending: { background: 'rgba(255, 183, 134, 0.1)', color: '$warning' },
    }
  }
});

const Dot = styled('span', {
  width: '6px',
  height: '6px',
  borderRadius: '$round',
  variants: {
    color: {
      success: { background: '$success' },
      primary: { background: '$accent' },
      warning: { background: '$warning' },
    }
  }
});

const GeoCard = styled(GlassCard, {
  display: 'flex',
  flexDirection: 'column',
  gap: '32px',
});

const MapContainer = styled('div', {
  aspectRatio: '1 / 1',
  borderRadius: '$xl',
  overflow: 'hidden',
  background: '#0a0e17',
  border: '1px solid $border',
  position: 'relative',
});

const MapBackground = styled('div', {
  position: 'absolute',
  inset: 0,
  opacity: 0.4,
  filter: 'grayscale(100%)',
  backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuDNPcXLG2oKX9xMS141mELcWyrgp0filLVBtrQRnHPovVKkM1H6WxbChK6NUF_1Yi63Q0KUnyyVoJ0cAmTUzEyysBnZ2r-OZkDvYzzexzgEpukay8gxDTPlTRq-Wi5Jd4PFjPIUWx1xBSp9ro5wDWj2JUKRHBVfIphIQvCyOln-x32zdMcezuknwo0jV_zN5VdOiRWJf5hjoe-dfHsaZIM4SHXs9Gasz0wmjVxHAQ_3bK0Ou2YcM9SM')",
  backgroundSize: 'cover',
  backgroundPosition: 'center',
});

const PingDot = styled('div', {
  position: 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: '24px',
  height: '24px',
  background: 'rgba(173, 198, 255, 0.4)',
  borderRadius: '$round',
  animation: 'ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite',
  '@keyframes ping': {
    '75%, 100%': { transform: 'translate(-50%, -50%) scale(2)', opacity: 0 }
  }
});

const InnerDot = styled('div', {
  position: 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: '12px',
  height: '12px',
  background: '$accent',
  borderRadius: '$round',
  border: '2px solid $bg',
});

const MapInfo = styled('div', {
  position: 'absolute',
  bottom: '24px',
  left: '24px',
  right: '24px',
  padding: '20px',
  background: 'rgba(11, 15, 25, 0.95)',
  borderRadius: '$xl',
  border: '1px solid $border',
  boxShadow: '$base',
});

const FloatingActionButton = styled('button', {
  position: 'fixed',
  bottom: '40px',
  right: '40px',
  zIndex: 50,
  width: '64px',
  height: '64px',
  borderRadius: '$round',
  background: '$accent',
  color: '$bg',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  border: 'none',
  boxShadow: '0 10px 25px rgba(173, 198, 255, 0.3)',
  cursor: 'pointer',
  transition: '$base',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: '0 15px 30px rgba(173, 198, 255, 0.4)',
  },
  '&:active': {
    transform: 'scale(0.9)',
  }
});

const LoadingContainer = styled('div', {
  display: 'flex',
  height: '300px',
  alignItems: 'center',
  justifyContent: 'center',
  color: '$textSecondary',
  fontSize: '$bodyLg',
});

const ErrorBox = styled(GlassCard, {
  borderColor: 'rgba(239, 68, 68, 0.3)',
  background: 'rgba(239, 68, 68, 0.05)',
  maxWidth: '600px',
  margin: '40px auto',
});

const RetryButton = styled('button', {
  marginTop: '16px',
  background: 'rgba(255,255,255,0.1)',
  border: '1px solid $border',
  color: '$textPrimary',
  padding: '8px 16px',
  borderRadius: '$sm',
  fontFamily: '$base',
  fontWeight: '500',
  cursor: 'pointer',
  transition: '$base',
  '&:hover': {
    background: 'rgba(255,255,255,0.2)',
  }
});

function SystemDashboard() {
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
      <DashboardSection>
        <LoadingContainer>Loading system analytics...</LoadingContainer>
      </DashboardSection>
    );
  }

  if (error) {
    if (error.includes('403') || error.toLowerCase().includes('forbidden') || error.toLowerCase().includes('not authenticated') || error.toLowerCase().includes('credentials') || error.toLowerCase().includes('permissions')) {
      return (
        <DashboardSection>
          <GlassCard style={{ maxWidth: '600px', margin: '0 auto' }}>
            <Title>Welcome to AURA Workspace</Title>
            <Subtitle style={{ marginTop: '16px' }}>You are logged in with a standard role. You can upload claims and view basic information.</Subtitle>
          </GlassCard>
        </DashboardSection>
      );
    }
    return (
      <DashboardSection>
        <ErrorBox>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#fca5a5', marginBottom: '8px' }}>
            <ShieldAlert size={20} />
            <h3 style={{ fontWeight: 700 }}>Dashboard Telemetry Error</h3>
          </div>
          <p style={{ color: '#fca5a5', fontSize: '14px' }}>{error}</p>
          <RetryButton onClick={fetchAnalytics}>Retry Request</RetryButton>
        </ErrorBox>
      </DashboardSection>
    );
  }

  return (
    <DashboardSection>
      <SectionHeader>
        <TitleGroup>
          <Title>AURA Platform Ready</Title>
          <Subtitle>Real-time analytics and investigations data.</Subtitle>
        </TitleGroup>
      </SectionHeader>

      <StatsGrid>
        <GlassCard>
          <CardHeader>
            <IconBox color="primary"><Network size={20} /></IconBox>
          </CardHeader>
          <StatLabel>Total Claims</StatLabel>
          <StatValue>{data?.total_claims ?? 0}</StatValue>
        </GlassCard>

        <GlassCard>
          <CardHeader>
            <IconBox color="danger"><ShieldAlert size={20} /></IconBox>
          </CardHeader>
          <StatLabel>High Risk Flagged</StatLabel>
          <StatValue>{data?.high_risk_claims ?? 0}</StatValue>
        </GlassCard>

        <GlassCard>
          <CardHeader>
            <IconBox color="success"><CheckCircle2 size={20} /></IconBox>
          </CardHeader>
          <StatLabel>Open Investigations</StatLabel>
          <StatValue>{data?.open_investigations ?? 0}</StatValue>
        </GlassCard>
      </StatsGrid>
    </DashboardSection>
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
        <Route path="/" element={<SystemDashboard />} />
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
