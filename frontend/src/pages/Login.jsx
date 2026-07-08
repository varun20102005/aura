import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const res = await api.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      
      localStorage.setItem('token', res.data.access_token);
      localStorage.setItem('userRole', res.data.role || 'Admin');
      
      navigate('/');
      window.location.reload();
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--aura-bg)' }}>
      <div className="aura-card" style={{ width: '100%', maxWidth: '400px', margin: '20px' }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <h1 className="aura-brand" style={{ fontSize: '32px', marginBottom: '8px', color: 'white' }}>AURA</h1>
          <p className="aura-text-muted">Sign in to access your workspace</p>
        </div>
        
        {error && (
          <div style={{ marginBottom: '24px', padding: '12px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5', borderRadius: 'var(--aura-radius-sm)', fontSize: '14px' }}>
            {error}
          </div>
        )}
        
        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--aura-text-muted)' }}>Email Address</label>
            <input 
              type="email" 
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              style={{ width: '100%', padding: '12px', borderRadius: 'var(--aura-radius-sm)', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--aura-border)', color: 'white', outline: 'none' }}
              placeholder="admin@aura.com"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--aura-text-muted)' }}>Password</label>
            <input 
              type="password" 
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              style={{ width: '100%', padding: '12px', borderRadius: 'var(--aura-radius-sm)', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--aura-border)', color: 'white', outline: 'none' }}
              placeholder="••••••••"
            />
          </div>
          <button 
            type="submit" 
            className="aura-button primary" 
            style={{ width: '100%', padding: '12px', marginTop: '8px', justifyContent: 'center' }}
            disabled={loading}
          >
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;
