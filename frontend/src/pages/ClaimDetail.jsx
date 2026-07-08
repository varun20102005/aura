import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { AlertTriangle, CheckCircle, Activity, FileText, UserCheck, Stethoscope, Copy } from 'lucide-react';
import api from '../api/axios';
import { formatDate, formatStatus, formatProcedureLabel, formatCurrency } from '../utils/formatters';

const ClaimDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [riskAgg, setRiskAgg] = useState(null);
  const [providerRisk, setProviderRisk] = useState(null);
  const [procValidation, setProcValidation] = useState([]);
  const [similar, setSimilar] = useState([]);
  const [simMethod, setSimMethod] = useState('hybrid');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notFound, setNotFound] = useState(false);

  const [costBenchmark, setCostBenchmark] = useState(null);

  useEffect(() => {
    // Guard: if id is not a valid positive integer, redirect to claims list
    if (!id || isNaN(Number(id)) || Number(id) <= 0) {
      navigate('/claims', { replace: true });
      return;
    }

    let pollInterval;
    
    const fetchAll = async () => {
      try {
        const [cRes, rRes, pvRes, sRes] = await Promise.all([
          api.get(`/claims/${id}`),
          api.get(`/claims/${id}/risk-aggregate`),
          api.get(`/claims/${id}/procedure-validation`),
          api.get(`/claims/${id}/similar?method=${simMethod}`)
        ]);
        
        const claimData = cRes.data;
        setClaim(claimData);
        setRiskAgg(rRes.data);
        setProcValidation(pvRes.data);
        setSimilar(sRes.data);

        // Fetch cost benchmark and provider risk in parallel
        const dependentPromises = [];
        
        let cbPromise = Promise.resolve();
        if (claimData.status !== 'processing' && claimData.status !== 'pending_ocr' && claimData.procedure_code) {
          cbPromise = api.get(`/analytics/cost-benchmark?procedure_code=${claimData.procedure_code}&provider_id=${claimData.provider_ref || ''}&billed_amount=${claimData.billed_amount || 0}`)
            .then(res => setCostBenchmark(res.data))
            .catch(() => setCostBenchmark({ status: 'FAILED', message: 'Unable to reach benchmark service.' }));
        }
        dependentPromises.push(cbPromise);

        let prPromise = Promise.resolve();
        if (claimData.provider_ref) {
          prPromise = api.get(`/providers/${claimData.provider_ref}/risk-profile`)
            .then(res => setProviderRisk(res.data))
            .catch(err => {
              if (err.response && err.response.status === 404) {
                setProviderRisk({ status: 'INSUFFICIENT_HISTORY' });
              } else {
                setProviderRisk({ status: 'ERROR' });
              }
            });
        }
        dependentPromises.push(prPromise);

        await Promise.all(dependentPromises);

        // If processing, setup polling
        if (claimData.status === 'processing' || claimData.status === 'pending_ocr') {
          if (!pollInterval) {
            pollInterval = setInterval(fetchAll, 3000);
          }
        } else if (pollInterval) {
          clearInterval(pollInterval);
        }

      } catch (err) {
        console.error(err);
        if (err.response && err.response.status === 404) {
          setNotFound(true);
        } else {
          setError(err.message || 'An error occurred while loading the claim.');
        }
      } finally {
        setLoading(false);
      }
    };
    
    fetchAll();
    
    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [id, simMethod]);

  if (loading) return <div style={{ padding: '32px', textAlign: 'center', color: 'var(--aura-text-muted)' }}>Loading claim details...</div>;
  if (notFound) return <div style={{ padding: '32px', textAlign: 'center', color: 'var(--aura-danger)' }}>Claim not found</div>;
  if (error) return <div style={{ padding: '32px', textAlign: 'center', color: 'var(--aura-danger)' }}>{error}</div>;
  if (!claim || Object.keys(claim).length === 0) return <div style={{ padding: '32px', textAlign: 'center', color: 'var(--aura-danger)' }}>Claim data is invalid or empty.</div>;

  const riskData = riskAgg && riskAgg.components && riskAgg.weights ? [
    { name: 'Fraud', score: riskAgg.components.fraud_score ?? 0, weight: riskAgg.weights.fraud ?? 0, value: (riskAgg.components.fraud_score ?? 0) * (riskAgg.weights.fraud ?? 0) },
    { name: 'Anomaly', score: riskAgg.components.anomaly_score ?? 0, weight: riskAgg.weights.anomaly ?? 0, value: (riskAgg.components.anomaly_score ?? 0) * (riskAgg.weights.anomaly ?? 0) },
    { name: 'Duplicate', score: riskAgg.components.duplicate_score ?? 0, weight: riskAgg.weights.duplicate ?? 0, value: (riskAgg.components.duplicate_score ?? 0) * (riskAgg.weights.duplicate ?? 0) },
    { name: 'Graph', score: riskAgg.components.graph_score ?? 0, weight: riskAgg.weights.graph ?? 0, value: (riskAgg.components.graph_score ?? 0) * (riskAgg.weights.graph ?? 0) },
    { name: 'Cost', score: riskAgg.components.cost_score ?? 0, weight: riskAgg.weights.cost ?? 0, value: (riskAgg.components.cost_score ?? 0) * (riskAgg.weights.cost ?? 0) },
    { name: 'Provider', score: riskAgg.components.provider_score ?? 0, weight: riskAgg.weights.provider ?? 0, value: (riskAgg.components.provider_score ?? 0) * (riskAgg.weights.provider ?? 0) },
].sort((a, b) => b.value - a.value) : [];

  const handleAssignCase = async () => {
    try {
      // In a real app we'd open a modal to select an investigator. For now, assign to user 1 or a dummy
      await api.post(`/claims/${id}/assign`, { investigator_id: 1 });
      // Reload claim to reflect assignment
      window.location.reload();
    } catch (err) {
      console.error('Failed to assign case', err);
      alert('Failed to assign case. You may not have the required permissions.');
    }
  };

  return (
    <div className="flex-col gap-6" style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '48px' }}>
      {/* Header */}
      <div className="aura-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h2 className="aura-h2" style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
            <FileText color="var(--aura-accent)" style={{ marginRight: '12px' }} /> Claim #{claim.id}
          </h2>
          <div style={{ display: 'flex', gap: '16px', fontSize: '14px', color: 'var(--aura-text-muted)' }}>
            <span>Patient: <strong style={{ color: 'var(--aura-text-primary)' }}>{claim.patient_ref || 'Not Available'}</strong></span>
            <span>Provider: <strong style={{ color: 'var(--aura-text-primary)' }}>{claim.provider_ref || 'Not Available'}</strong></span>
            <span>Created: {formatDate(claim.created_at)}</span>
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
          <span className={`aura-badge ${claim.status === 'action_required' ? 'high' : claim.status === 'processing' ? 'medium' : 'low'}`} style={{ fontSize: '12px' }}>
            {formatStatus(claim.status)}
          </span>
          <button className="aura-button primary" onClick={handleAssignCase} style={{ marginTop: '16px' }}>
            Assign Case
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
        
        {/* Left Col: Aggregate & Validation */}
        <div className="flex-col gap-6">
          
          {/* Risk Aggregate Display */}
          <div className="aura-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 600, display: 'flex', alignItems: 'center' }}>
                <Activity color="var(--aura-accent)" size={20} style={{ marginRight: '8px' }} /> Risk Aggregate Engine
              </h3>
              {riskAgg && (
                <div className={`aura-badge ${riskAgg.risk_band === 'High' ? 'high' : riskAgg.risk_band === 'Medium' ? 'medium' : 'low'}`}>
                  {riskAgg.risk_band} Risk ({(riskAgg.aggregate_score * 100).toFixed(1)})
                </div>
              )}
            </div>
            
            {riskAgg ? (
              <div style={{ height: '250px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={riskData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                    <XAxis type="number" domain={[0, 1]} hide />
                    <YAxis dataKey="name" type="category" stroke="#94a3b8" width={80} tick={{fill: '#94a3b8', fontSize: 12}} />
                    <Tooltip 
                      cursor={{fill: 'rgba(255,255,255,0.05)'}} 
                      contentStyle={{ backgroundColor: 'var(--aura-surface)', borderColor: 'var(--aura-border)', color: 'var(--aura-text-primary)' }}
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div style={{ background: 'var(--aura-surface)', border: '1px solid var(--aura-border)', padding: '8px', borderRadius: '4px', fontSize: '12px' }}>
                              <strong style={{ display: 'block', marginBottom: '4px' }}>{data.name} Risk</strong>
                              <div>Score: {(data.score * 100).toFixed(1)}</div>
                              <div>Weight: {(data.weight * 100).toFixed(1)}%</div>
                              <div style={{ marginTop: '4px', paddingTop: '4px', borderTop: '1px solid var(--aura-border)', fontWeight: 'bold' }}>
                                Contribution: +{(data.value * 100).toFixed(1)}
                              </div>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                      {riskData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.value > 0.7 ? 'var(--aura-danger)' : entry.value > 0.4 ? 'var(--aura-warning)' : 'var(--aura-accent)'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="aura-text-muted" style={{ fontSize: '14px' }}>Aggregate score not yet computed.</p>
            )}
          </div>

          {/* Similarity Panel */}
          <div className="aura-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 600, display: 'flex', alignItems: 'center' }}>
                <Copy color="var(--aura-accent)" size={20} style={{ marginRight: '8px' }} /> Duplicate Detection
              </h3>
              <div style={{ display: 'flex', gap: '4px', background: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: '8px', border: '1px solid var(--aura-border)' }}>
                {['hybrid', 'fuzzy', 'semantic'].map(m => (
                  <button 
                    key={m}
                    onClick={() => setSimMethod(m)}
                    className="aura-button"
                    style={simMethod === m ? { background: 'var(--aura-accent)', color: 'white', borderColor: 'var(--aura-accent)', textTransform: 'capitalize', padding: '4px 8px', fontSize: '12px' } : { background: 'transparent', borderColor: 'transparent', textTransform: 'capitalize', padding: '4px 8px', fontSize: '12px' }}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>
            
            {similar.length > 0 ? (
              <div className="flex-col gap-4">
                {similar.slice(0,3).map((sim, idx) => (
                  <div key={sim.claim_id || idx} style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--aura-border)', borderRadius: 'var(--aura-radius-sm)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 500, color: 'var(--aura-text-primary)', marginBottom: '4px' }}>Claim #{sim.claim_id}</div>
                      <div className="aura-text-muted" style={{ fontSize: '12px' }}>Matches via {sim.method} engine</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '20px', fontWeight: 'bold', color: sim.score > 0.85 ? 'var(--aura-danger)' : 'var(--aura-warning)' }}>
                        {(sim.score * 100).toFixed(1)}%
                      </div>
                      <div className="aura-text-muted" style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Similarity</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '24px', color: 'var(--aura-text-muted)', border: '1px dashed var(--aura-border)', borderRadius: 'var(--aura-radius-sm)' }}>
                No similar claims found above threshold.
              </div>
            )}
          </div>
        </div>

        {/* Right Col: Cost, Provider, Procedure */}
        <div className="flex-col gap-6">
          
          {/* Provider Profile */}
          <div className="aura-card" style={{ flex: 1 }}>
            <h3 style={{ fontSize: '18px', fontWeight: 600, display: 'flex', alignItems: 'center', marginBottom: '24px' }}>
              <Stethoscope color="var(--aura-accent)" size={20} style={{ marginRight: '8px' }} /> Provider Profile
            </h3>
            {!claim.provider_ref ? (
              <div style={{ textAlign: 'center', color: 'var(--aura-text-muted)', padding: '24px' }}>
                No provider reference supplied.
              </div>
            ) : !providerRisk ? (
              <div style={{ textAlign: 'center', color: 'var(--aura-text-muted)', padding: '24px' }}>Loading provider profile...</div>
            ) : providerRisk.status === 'INSUFFICIENT_HISTORY' ? (
              <div style={{ textAlign: 'center', color: 'var(--aura-text-muted)', padding: '24px' }}>
                <p>Provider profile exists, but insufficient verified history is available for reliable risk estimation.</p>
              </div>
            ) : providerRisk.status === 'ERROR' ? (
              <div style={{ textAlign: 'center', color: 'var(--aura-danger)', padding: '24px' }}>
                Unable to load provider profile.
              </div>
            ) : (
              <div className="flex-col gap-4">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                  <span className="aura-text-muted" style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Risk Score</span>
                  <span style={{ fontSize: '24px', fontWeight: 'bold', color: providerRisk.rolling_risk_score > 0.7 ? 'var(--aura-danger)' : 'var(--aura-success)' }}>
                    {providerRisk.rolling_risk_score ? providerRisk.rolling_risk_score.toFixed(3) : '0.000'}
                  </span>
                </div>
                <div style={{ width: '100%', background: 'rgba(255,255,255,0.1)', borderRadius: '999px', height: '8px' }}>
                  <div style={{ background: 'var(--aura-accent)', height: '8px', borderRadius: '999px', width: `${(providerRisk.rolling_risk_score || 0) * 100}%` }}></div>
                </div>
                <div style={{ paddingTop: '16px', borderTop: '1px solid var(--aura-border)', display: 'flex', justifyContent: 'space-between', fontSize: '14px', color: 'var(--aura-text-muted)' }}>
                  <span>Verified Outcomes</span>
                  <strong>{providerRisk.verified_outcomes_count || 0}</strong>
                </div>
              </div>
            )}
          </div>

          {/* Procedure Validation Panel */}
          <div className="aura-card">
            <h3 style={{ fontSize: '18px', fontWeight: 600, display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
              <Stethoscope color="var(--aura-accent)" size={20} style={{ marginRight: '8px' }} /> Procedure Validation
            </h3>
            {procValidation.length > 0 ? (
              <div className="flex-col gap-3">
                {procValidation.map((flag, idx) => (
                  <div key={idx} style={{ display: 'flex', padding: '12px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: 'var(--aura-radius-sm)' }}>
                    <AlertTriangle color="#fca5a5" size={16} style={{ marginRight: '12px', flexShrink: 0, marginTop: '2px' }} />
                    <div>
                      <div style={{ fontSize: '14px', fontWeight: 600, color: '#fecaca' }}>{flag.flag_type}</div>
                      <div style={{ fontSize: '12px', color: '#fca5a5', opacity: 0.8, marginTop: '4px' }}>{flag.description}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', fontSize: '14px', padding: '16px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: 'var(--aura-radius-sm)', color: '#6ee7b7' }}>
                <CheckCircle size={16} style={{ marginRight: '8px' }} /> All procedure codes validated.
              </div>
            )}
          </div>

          {/* Cost Benchmark */}
          <div className="aura-card">
            <h3 style={{ fontSize: '18px', fontWeight: 600, display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
              <span style={{ color: 'var(--aura-accent)', marginRight: '8px' }}>$</span> Cost Benchmark
            </h3>
            {!costBenchmark ? (
              <div className="aura-text-muted" style={{ fontSize: '14px', fontStyle: 'italic' }}>
                Loading benchmark data…
              </div>
            ) : costBenchmark.status === 'UNAVAILABLE' ? (
              <div style={{ padding: '16px', background: 'rgba(255, 255, 255, 0.03)', border: '1px dashed var(--aura-border)', borderRadius: 'var(--aura-radius-sm)', textAlign: 'center' }}>
                <div style={{ fontSize: '14px', color: 'var(--aura-text-muted)', marginBottom: '8px' }}>
                  {costBenchmark.message || 'Benchmark data is not available for this claim.'}
                </div>
                {costBenchmark.reason_code && (
                  <span className="aura-badge low" style={{ fontSize: '11px', padding: '2px 8px', opacity: 0.7 }}>
                    {costBenchmark.reason_code.replace(/_/g, ' ')}
                  </span>
                )}
              </div>
            ) : costBenchmark.status === 'PROCESSING' ? (
              <div className="aura-text-muted" style={{ fontSize: '14px', fontStyle: 'italic', textAlign: 'center', padding: '16px' }}>
                Benchmark computation in progress…
              </div>
            ) : costBenchmark.status === 'FAILED' ? (
              <div style={{ padding: '16px', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--aura-danger)', borderRadius: 'var(--aura-radius-sm)', fontSize: '14px' }}>
                {costBenchmark.message || 'Benchmark analysis failed.'}
              </div>
            ) : (
              <div className="flex-col gap-4">
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--aura-border)', paddingBottom: '12px' }}>
                  <span className="aura-text-muted">Billed Amount</span>
                  <strong style={{ fontSize: '16px' }}>{formatCurrency(claim.billed_amount)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--aura-border)', paddingBottom: '12px' }}>
                  <span className="aura-text-muted">Benchmark Median</span>
                  <strong style={{ fontSize: '16px', color: claim.billed_amount > costBenchmark.p75 ? 'var(--aura-danger)' : claim.billed_amount < costBenchmark.p25 ? 'var(--aura-success)' : 'inherit' }}>
                    {formatCurrency(costBenchmark.median)}
                  </strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--aura-border)', paddingBottom: '12px' }}>
                  <span className="aura-text-muted">IQR Spread</span>
                  <span className="aura-text-muted" style={{ fontSize: '14px' }}>
                    {formatCurrency(costBenchmark.p25)} - {formatCurrency(costBenchmark.p75)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '8px' }}>
                  <span className="aura-text-muted">Confidence Level</span>
                  <span className={`aura-badge ${costBenchmark.tier_used === 'High' ? 'high' : costBenchmark.tier_used === 'Medium' ? 'medium' : 'low'}`} style={{ fontSize: '14px', padding: '4px 12px' }}>
                    {costBenchmark.tier_used} (N={costBenchmark.sample_size})
                  </span>
                </div>
              </div>
            )}
          </div>
          
        </div>
      </div>
    </div>
  );
};

export default ClaimDetail;
