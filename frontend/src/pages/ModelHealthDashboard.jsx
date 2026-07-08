import React, { useState, useEffect } from 'react';
import axios from '../api/axios';
import { Activity, AlertTriangle, CheckCircle, Clock, UploadCloud, RotateCcw, List } from 'lucide-react';

const ModelHealthDashboard = () => {
  const [activeModels, setActiveModels] = useState([]);
  const [registry, setRegistry] = useState([]);
  const [activeTab, setActiveTab] = useState('health'); // 'health' or 'registry'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [healthRes, regRes] = await Promise.all([
          axios.get('/admin/models/evaluation-report'),
          axios.get('/admin/models')
        ]);
        setActiveModels(healthRes.data.models || []);
        setRegistry(regRes.data || []);
        setLoading(false);
      } catch (err) {
        setError(err.message || 'Failed to fetch model data');
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  const handlePromote = async (id) => {
    if (!window.confirm("Are you sure you want to promote this model?")) return;
    try {
      await axios.post(`/admin/models/${id}/promote`);
      alert("Model promoted successfully");
      window.location.reload();
    } catch (err) {
      alert("Failed to promote: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleRollback = async (id) => {
    if (!window.confirm("Are you sure you want to rollback to this model?")) return;
    try {
      await axios.post(`/admin/models/${id}/rollback`);
      alert("Model rolled back successfully");
      window.location.reload();
    } catch (err) {
      alert("Failed to rollback: " + (err.response?.data?.detail || err.message));
    }
  };

  if (loading) {
    return <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--aura-text-muted)' }}>Loading model telemetry...</div>;
  }

  if (error) {
    return (
      <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5', padding: '16px', borderRadius: 'var(--aura-radius-sm)' }}>
        <h3 style={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}><AlertTriangle size={20} /> Error Loading Telemetry</h3>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="flex-col gap-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="aura-h2" style={{ marginBottom: 0 }}>Model Management</h1>
          <p className="aura-text-muted" style={{ marginTop: '4px' }}>Telemetry and Registry for inference engines</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', background: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: '8px', border: '1px solid var(--aura-border)' }}>
          <button 
            onClick={() => setActiveTab('health')}
            className="aura-button"
            style={activeTab === 'health' ? { background: 'var(--aura-accent)', color: 'white', borderColor: 'var(--aura-accent)' } : { background: 'transparent', borderColor: 'transparent' }}
          >
            <Activity size={16} /> Live Health
          </button>
          <button 
            onClick={() => setActiveTab('registry')}
            className="aura-button"
            style={activeTab === 'registry' ? { background: 'var(--aura-accent)', color: 'white', borderColor: 'var(--aura-accent)' } : { background: 'transparent', borderColor: 'transparent' }}
          >
            <List size={16} /> Model Registry
          </button>
        </div>
      </div>

      {activeTab === 'health' && (
        <div className="aura-dashboard-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          {activeModels.map((model) => {
            const isDrifting = model.drift_status?.flagged;
            const isOperational = model.runtime_status === "OPERATIONAL";
            
            const runtimeStatusColor = isOperational ? 'var(--aura-success)' : 'var(--aura-danger)';
            const RuntimeIcon = isOperational ? CheckCircle : AlertTriangle;
            
            const driftStatusColor = isDrifting ? 'var(--aura-danger)' : model.drift_monitoring_status === "MONITORED" ? 'var(--aura-success)' : 'var(--aura-text-muted)';
            const DriftIcon = isDrifting ? AlertTriangle : CheckCircle;

            return (
              <div key={model.model_id} className="aura-card" style={{ padding: 0, overflow: 'hidden' }}>
                {/* Header */}
                <div style={{ borderBottom: '1px solid var(--aura-border)', padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', background: 'rgba(255,255,255,0.02)' }}>
                  <div>
                    <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: 'var(--aura-text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Activity color="var(--aura-accent)" size={20} />
                      {model.model_type.toUpperCase()}
                    </h2>
                    <div style={{ display: 'flex', gap: '6px', marginTop: '6px', alignItems: 'center' }}>
                      <span className="aura-badge" style={{ background: 'var(--aura-accent-glow)', color: 'var(--aura-accent)', border: '1px solid var(--aura-accent)', fontSize: '11px', padding: '2px 8px' }}>
                        Version {model.version}
                      </span>
                      <span className="aura-badge low" style={{ fontSize: '11px', padding: '2px 8px' }}>
                        {model.registry_status}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, color: runtimeStatusColor, background: 'rgba(0,0,0,0.2)', padding: '4px 12px', borderRadius: '999px', border: '1px solid var(--aura-border)', fontSize: '12px' }}>
                    <RuntimeIcon size={16} />
                    RUNTIME: {model.runtime_status}
                  </div>
                </div>

                {/* Metrics Body */}
                <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  
                  {/* Status Concepts Sub-Panel */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', background: 'rgba(255,255,255,0.01)', padding: '12px 16px', borderRadius: 'var(--aura-radius-sm)', border: '1px solid var(--aura-border)' }}>
                    <div>
                      <span style={{ color: 'var(--aura-text-muted)', fontSize: '12px' }}>Evaluation Status: </span>
                      <span className={`aura-badge ${model.evaluation_status === 'AVAILABLE' ? 'low' : 'medium'}`} style={{ fontSize: '10px', padding: '2px 6px' }}>
                        {model.evaluation_status}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: 'var(--aura-text-muted)', fontSize: '12px' }}>Drift Telemetry: </span>
                      <span className={`aura-badge ${model.drift_monitoring_status === 'MONITORED' ? 'low' : 'medium'}`} style={{ fontSize: '10px', padding: '2px 6px' }}>
                        {model.drift_monitoring_status}
                      </span>
                    </div>
                  </div>

                  {/* Evaluation Metrics */}
                  <div>
                    <h3 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--aura-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>Latest Evaluation Metrics</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                      {Object.entries(model.metrics || {}).map(([key, value]) => (
                        <div key={key} style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: 'var(--aura-radius-sm)', border: '1px solid var(--aura-border)' }}>
                          <div style={{ color: 'var(--aura-text-muted)', fontSize: '12px', textTransform: 'uppercase', marginBottom: '4px' }}>{key}</div>
                          <div style={{ color: 'var(--aura-text-primary)', fontSize: '18px', fontWeight: 'bold' }}>
                            {typeof value === 'number' ? value.toFixed(4) : value}
                          </div>
                        </div>
                      ))}
                      {(!model.metrics || Object.keys(model.metrics).length === 0) && (
                        <div style={{ color: 'var(--aura-text-muted)', fontStyle: 'italic', gridColumn: '1 / -1', padding: '8px 0' }}>
                          Evaluation metrics unavailable for this model architecture.
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Drift Status */}
                  <div>
                    <h3 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--aura-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>Drift Analysis (PSI)</h3>
                    <div style={{ padding: '16px', borderRadius: 'var(--aura-radius-sm)', border: isDrifting ? '1px solid rgba(239, 68, 68, 0.3)' : model.drift_monitoring_status === "MONITORED" ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--aura-border)', background: isDrifting ? 'rgba(239, 68, 68, 0.1)' : model.drift_monitoring_status === "MONITORED" ? 'rgba(16, 185, 129, 0.05)' : 'rgba(0,0,0,0.1)' }}>
                      {model.drift_monitoring_status === "MONITORED" && model.drift_status?.value !== null ? (
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <div style={{ color: 'var(--aura-text-primary)', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <DriftIcon size={14} color={driftStatusColor} /> Population Stability Index
                            </div>
                            <div style={{ fontSize: '24px', fontWeight: 'bold', color: driftStatusColor, marginTop: '4px' }}>
                              {model.drift_status.value.toFixed(4)}
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ color: 'var(--aura-text-muted)', fontSize: '12px', textTransform: 'uppercase' }}>Threshold</div>
                            <div style={{ color: 'var(--aura-text-primary)', fontFamily: 'var(--aura-mono)' }}>{model.drift_status.threshold.toFixed(2)}</div>
                            <div style={{ color: driftStatusColor, fontSize: '11px', fontWeight: 'bold', textTransform: 'uppercase', marginTop: '4px' }}>
                              {isDrifting ? 'DRIFT DETECTED' : 'NO DRIFT'}
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div style={{ color: 'var(--aura-text-muted)', fontStyle: 'italic' }}>Drift analysis unavailable. No drift checks recorded yet.</div>
                      )}
                    </div>
                  </div>

                  {/* Timestamps */}
                  <div style={{ borderTop: '1px solid var(--aura-border)', paddingTop: '16px', display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--aura-text-muted)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={14} />
                      Promoted: {model.promoted_at ? new Date(model.promoted_at).toLocaleString() : 'N/A'}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={14} />
                      Last Drift Check: {model.drift_status?.computed_at ? new Date(model.drift_status.computed_at).toLocaleString() : 'N/A'}
                    </div>
                  </div>

                </div>
              </div>
            );
          })}

        {activeModels.length === 0 && !loading && (
          <div style={{ gridColumn: '1 / -1', padding: '32px', textAlign: 'center', border: '1px dashed var(--aura-border)', borderRadius: 'var(--aura-radius)', color: 'var(--aura-text-muted)' }}>
            No active models found in the registry.
          </div>
        )}
      </div>
      )}

      {activeTab === 'registry' && (
        <div className="aura-table-container">
          <table className="aura-table">
            <thead>
              <tr>
                <th>Model Type</th>
                <th>Version</th>
                <th>Status</th>
                <th>Created</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {registry.map(model => (
                <tr key={model.id}>
                  <td><strong>{model.model_type}</strong></td>
                  <td style={{ fontFamily: 'var(--aura-mono)' }}>{model.version}</td>
                  <td>
                    <span className={`aura-badge ${model.status === 'active' ? 'low' : model.status === 'candidate' ? 'medium' : ''}`} style={model.status !== 'active' && model.status !== 'candidate' ? { background: 'rgba(255,255,255,0.1)', color: 'var(--aura-text-secondary)', border: '1px solid var(--aura-border)'} : {}}>
                      {model.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="aura-text-muted">
                    {new Date(model.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ textAlign: 'right', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                    {model.status === 'candidate' && (
                      <button onClick={() => handlePromote(model.id)} style={{ background: 'none', border: 'none', color: 'var(--aura-accent)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <UploadCloud size={16} /> Promote
                      </button>
                    )}
                    {model.status === 'retired' && (
                      <button onClick={() => handleRollback(model.id)} style={{ background: 'none', border: 'none', color: 'var(--aura-warning)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <RotateCcw size={16} /> Rollback
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ModelHealthDashboard;
