import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, AlertTriangle } from 'lucide-react';
import api from '../api/axios';
import { formatDate, formatStatus, formatCurrency } from '../utils/formatters';

const ClaimsList = () => {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('');
  const [riskBand, setRiskBand] = useState('');

  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [total, setTotal] = useState(0);

  const fetchClaims = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (query) params.append('query', query);
      if (status) params.append('status', status);
      if (riskBand) params.append('risk_band', riskBand);
      params.append('skip', (page - 1) * pageSize);
      params.append('limit', pageSize);
      
      const endpoint = `/claims/search?${params.toString()}`;
      const res = await api.get(endpoint);
      setClaims(res.data.items || res.data);
      setTotal(res.data.total || (res.data.items ? res.data.items.length : res.data.length));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClaims();
  }, [page]);

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    fetchClaims();
  };

  return (
    <div className="flex-col gap-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="aura-h2" style={{ marginBottom: 0 }}>Claims Register</h2>
        <Link to="/upload" className="aura-button primary">
          Bulk Upload Claims
        </Link>
      </div>

      <div className="aura-card mb-6">
        <form onSubmit={handleSearch} className="flex flex-col gap-4">
          <div className="flex gap-4">
            <div className="aura-form-group" style={{ flex: 1, marginBottom: 0 }}>
              <label className="aura-form-label">Search Ref</label>
              <div style={{ position: 'relative' }}>
                <Search size={16} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--aura-text-muted)' }} />
                <input 
                  type="text" 
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="aura-input" 
                  style={{ paddingLeft: '36px' }}
                  placeholder="Patient or Provider Ref..."
                />
              </div>
            </div>
            
            <div className="aura-form-group" style={{ width: '200px', marginBottom: 0 }}>
              <label className="aura-form-label">Status</label>
              <select 
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="aura-input"
              >
                <option value="">All Statuses</option>
                <option value="uploaded">Uploaded</option>
                <option value="processing">Processing</option>
                <option value="action_required">Action Required</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>

            <div className="aura-form-group" style={{ width: '200px', marginBottom: 0 }}>
              <label className="aura-form-label">Risk Band</label>
              <select 
                value={riskBand}
                onChange={(e) => setRiskBand(e.target.value)}
                className="aura-input"
              >
                <option value="">All Risk Bands</option>
                <option value="High">High Risk</option>
                <option value="Medium">Medium Risk</option>
                <option value="Low">Low Risk</option>
              </select>
            </div>
            
            <div className="flex items-center" style={{ paddingTop: '28px' }}>
              <button type="submit" className="aura-button primary">
                Search
              </button>
            </div>
          </div>
        </form>
      </div>

      <div className="aura-card p-0" style={{ overflow: 'hidden' }}>
        <div className="table-responsive">
          <table className="aura-table">
            <thead>
              <tr>
                <th>Claim ID</th>
                <th>Patient Ref</th>
                <th>Provider Ref</th>
                <th>Procedure</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Date</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '32px', color: 'var(--aura-text-muted)' }}>
                    Loading claims...
                  </td>
                </tr>
              ) : claims.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '32px', color: 'var(--aura-text-muted)' }}>
                    No claims found matching criteria.
                  </td>
                </tr>
              ) : (
                claims.map(claim => (
                  <tr key={claim.id}>
                    <td style={{ fontWeight: 500, color: 'white' }}>{claim.id}</td>
                    <td>{claim.patient_ref}</td>
                    <td>{claim.provider_ref}</td>
                    <td><span className="aura-badge">{claim.procedure_code}</span></td>
                    <td>{formatCurrency(claim.billed_amount)}</td>
                    <td>
                      <span className={`aura-badge ${claim.status === 'action_required' ? 'high' : claim.status === 'processing' ? 'medium' : 'low'}`}>
                        {formatStatus(claim.status).toUpperCase()}
                      </span>
                    </td>
                    <td style={{ color: 'var(--aura-text-muted)' }}>{formatDate(claim.created_at)}</td>
                    <td>
                      <Link to={`/claims/${claim.id}`} className="aura-button" style={{ padding: '4px 12px', fontSize: '12px' }}>
                        View
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {!loading && total > 0 && (
          <div style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--aura-border)' }}>
            <span style={{ color: 'var(--aura-text-muted)', fontSize: '14px' }}>
              Showing {Math.min((page - 1) * pageSize + 1, total)} to {Math.min(page * pageSize, total)} of {total} claims
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                className="aura-button" 
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </button>
              <button 
                className="aura-button" 
                onClick={() => setPage(p => p + 1)}
                disabled={page * pageSize >= total}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ClaimsList;
