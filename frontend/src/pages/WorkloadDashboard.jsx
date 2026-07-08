import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Users, Clock, AlertCircle } from 'lucide-react';
import api from '../api/axios';

const WorkloadDashboard = () => {
  const [workload, setWorkload] = useState([]);
  const [loading, setLoading] = useState(true);

  // Using ID 1 since we seeded admin@aura.com as ID 1
  const investigatorId = 1; // updated for demo

  useEffect(() => {
    const fetchWorkload = async () => {
      try {
        const res = await api.get(`/investigators/${investigatorId}/workload`);
        setWorkload(res.data);
      } catch (err) {
        console.error("Failed to fetch workload", err);
      } finally {
        setLoading(false);
      }
    };
    fetchWorkload();
  }, []);

  const calculateSLA = (dueDateStr) => {
    if (!dueDateStr) return { text: "No SLA", type: "low" };
    const due = new Date(dueDateStr);
    const now = new Date();
    const diffHours = (due - now) / (1000 * 60 * 60);
    
    if (diffHours < 0) return { text: "Breached", type: "high" };
    if (diffHours < 24) return { text: `${Math.round(diffHours)}h remaining`, type: "medium" };
    return { text: `${Math.round(diffHours / 24)}d remaining`, type: "low" };
  };

  return (
    <div className="flex-col gap-6">
      <div className="flex items-center mb-6 gap-2">
        <Users color="var(--aura-accent)" size={28} />
        <h2 className="aura-h2" style={{ marginBottom: 0 }}>Investigator Workload</h2>
      </div>

      <div className="aura-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="flex justify-between items-center" style={{ padding: '16px 24px', borderBottom: '1px solid var(--aura-border)', background: 'rgba(0,0,0,0.2)' }}>
          <h3 style={{ fontWeight: 600 }}>Active Cases (Investigator #{investigatorId})</h3>
          <span className="aura-badge primary" style={{ backgroundColor: 'var(--aura-accent-glow)', color: 'var(--aura-accent)' }}>
            {workload.length} Cases Assigned
          </span>
        </div>
        <div>
          {loading ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--aura-text-muted)' }}>Loading cases...</div>
          ) : workload.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--aura-text-muted)' }}>No active cases.</div>
          ) : (
            workload.map((item) => {
              const claimId = item.id || item.claim_id;
              return (
              <div key={claimId} className="flex justify-between items-center" style={{ padding: '24px', borderBottom: '1px solid var(--aura-border)', transition: 'var(--aura-transition)' }}>
                <div>
                  <div className="flex items-center mb-2 gap-2">
                    <span style={{ fontSize: '18px', fontWeight: 'bold' }}>Claim #{claimId}</span>
                    <span className="aura-badge low" style={{ fontSize: '10px' }}>{(item.status || '').replace('_', ' ').toUpperCase()}</span>
                  </div>
                  <div className="aura-text-muted" style={{ fontSize: '14px' }}>
                    Patient: {item.patient_ref || 'N/A'} | Provider: {item.provider_ref || 'N/A'}
                  </div>
                </div>
                
                <div className="flex items-center gap-6">
                  <div style={{ textAlign: 'right' }}>
                    <div className="flex items-center justify-end aura-text-muted" style={{ fontSize: '12px', textTransform: 'uppercase', marginBottom: '4px', gap: '4px' }}>
                      <Clock size={14} /> SLA Status
                    </div>
                    {item.assignment ? (
                      <div className={`aura-badge ${calculateSLA(item.assignment.sla_due_at).type}`}>
                        {calculateSLA(item.assignment.sla_due_at).text}
                      </div>
                    ) : (
                      <div className="aura-text-muted" style={{ fontSize: '14px' }}>Unknown</div>
                    )}
                  </div>
                  
                  <Link to={`/claims/${claimId}`} className="aura-button">
                    Work Case
                  </Link>
                </div>
              </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

export default WorkloadDashboard;
