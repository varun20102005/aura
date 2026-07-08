import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, FileText, CheckCircle, XCircle, User, Activity, DollarSign, Briefcase } from 'lucide-react';
import api from '../api/axios';

const ClaimUpload = () => {
  const [activeTab, setActiveTab] = useState('individual');

  // Individual Upload State
  const [patientRef, setPatientRef] = useState('');
  const [providerRef, setProviderRef] = useState('');
  const [procedureCode, setProcedureCode] = useState('');
  const [billedAmount, setBilledAmount] = useState('');
  const [singleDoc, setSingleDoc] = useState(null);
  
  // Bulk Upload State
  const [manifest, setManifest] = useState(null);
  const [documents, setDocuments] = useState([]);
  
  // Shared State
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState(null);

  // --- Individual Methods ---
  const onDropSingleDoc = useCallback(acceptedFiles => {
    if (acceptedFiles.length > 0) setSingleDoc(acceptedFiles[0]);
  }, []);

  const { getRootProps: getSingleDocProps, getInputProps: getSingleDocInput } = useDropzone({
    onDrop: onDropSingleDoc,
    accept: { 'application/pdf': ['.pdf'], 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'] },
    maxFiles: 1
  });

  const handleIndividualUpload = async (e) => {
    e.preventDefault();
    if (!singleDoc) {
      setResults({ errors: [{ row: 'System', error: 'Supporting document is required.' }] });
      return;
    }
    setUploading(true);
    setResults(null);
    const formData = new FormData();
    formData.append('patient_ref', patientRef);
    formData.append('provider_ref', providerRef);
    formData.append('procedure_code', procedureCode);
    formData.append('billed_amount', billedAmount);
    formData.append('file', singleDoc);

    try {
      const res = await api.post('/claims/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResults({ message: 'Claim uploaded successfully!', processed_count: 1 });
      // Reset form
      setPatientRef('');
      setProviderRef('');
      setProcedureCode('');
      setBilledAmount('');
      setSingleDoc(null);
    } catch (err) {
      console.error(err);
      let errorMsg = err.message;
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          errorMsg = err.response.data.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join(', ');
        } else {
          errorMsg = err.response.data.detail;
        }
      }
      setResults({ errors: [{ row: 'System', error: errorMsg }] });
    } finally {
      setUploading(false);
    }
  };

  // --- Bulk Methods ---
  const onDropManifest = useCallback(acceptedFiles => {
    if (acceptedFiles.length > 0) setManifest(acceptedFiles[0]);
  }, []);

  const onDropDocs = useCallback(acceptedFiles => {
    setDocuments(prev => [...prev, ...acceptedFiles]);
  }, []);

  const removeDoc = (name) => {
    setDocuments(docs => docs.filter(d => d.name !== name));
  };

  const { getRootProps: getManifestProps, getInputProps: getManifestInput } = useDropzone({
    onDrop: onDropManifest,
    accept: { 'text/csv': ['.csv'] },
    maxFiles: 1
  });

  const { getRootProps: getDocsProps, getInputProps: getDocsInput } = useDropzone({
    onDrop: onDropDocs,
    accept: { 'application/pdf': ['.pdf'], 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'] }
  });

  const handleBulkUpload = async () => {
    if (!manifest) return;
    if (documents.length === 0) {
      setResults({ errors: [{ row: 'System', error: 'At least one document must be uploaded.' }] });
      return;
    }
    setUploading(true);
    setResults(null);
    const formData = new FormData();
    formData.append('manifest', manifest);
    documents.forEach(doc => formData.append('documents', doc));

    try {
      const res = await api.post('/claims/bulk-upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResults(res.data);
      setManifest(null);
      setDocuments([]);
    } catch (err) {
      console.error(err);
      let errorMsg = err.message;
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          errorMsg = err.response.data.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join(', ');
        } else {
          errorMsg = err.response.data.detail;
        }
      }
      setResults({ errors: [{ row: 'System', error: errorMsg }] });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex-col gap-6" style={{ maxWidth: '1000px', margin: '0 auto', paddingBottom: '48px' }}>
      <h2 className="aura-h2" style={{ marginBottom: '8px' }}>Claim Upload</h2>
      
      {/* Tabs */}
      <div style={{ display: 'flex', gap: '16px', borderBottom: '1px solid var(--aura-border)', marginBottom: '24px', paddingBottom: '8px' }}>
        <button 
          onClick={() => { setActiveTab('individual'); setResults(null); }}
          style={{ background: 'none', border: 'none', color: activeTab === 'individual' ? 'var(--aura-accent)' : 'var(--aura-text-muted)', fontWeight: activeTab === 'individual' ? 600 : 400, padding: '8px 16px', cursor: 'pointer', borderBottom: activeTab === 'individual' ? '2px solid var(--aura-accent)' : '2px solid transparent', transition: 'var(--aura-transition)' }}
        >
          Individual Claim
        </button>
        <button 
          onClick={() => { setActiveTab('bulk'); setResults(null); }}
          style={{ background: 'none', border: 'none', color: activeTab === 'bulk' ? 'var(--aura-accent)' : 'var(--aura-text-muted)', fontWeight: activeTab === 'bulk' ? 600 : 400, padding: '8px 16px', cursor: 'pointer', borderBottom: activeTab === 'bulk' ? '2px solid var(--aura-accent)' : '2px solid transparent', transition: 'var(--aura-transition)' }}
        >
          Bulk Upload
        </button>
      </div>

      {activeTab === 'individual' && (
        <form onSubmit={handleIndividualUpload} className="aura-card" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <label style={{ fontSize: '14px', fontWeight: 500, color: 'var(--aura-text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}><User size={16} /> Patient Reference</label>
              <input type="text" required value={patientRef} onChange={e => setPatientRef(e.target.value)} style={{ padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--aura-border)', borderRadius: 'var(--aura-radius-sm)', color: 'var(--aura-text-primary)' }} placeholder="e.g. PAT-12345" />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <label style={{ fontSize: '14px', fontWeight: 500, color: 'var(--aura-text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}><Briefcase size={16} /> Provider Reference</label>
              <input type="text" required value={providerRef} onChange={e => setProviderRef(e.target.value)} style={{ padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--aura-border)', borderRadius: 'var(--aura-radius-sm)', color: 'var(--aura-text-primary)' }} placeholder="e.g. PRV-98765" />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <label style={{ fontSize: '14px', fontWeight: 500, color: 'var(--aura-text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}><Activity size={16} /> Procedure Code</label>
              <input type="text" required value={procedureCode} onChange={e => setProcedureCode(e.target.value)} style={{ padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--aura-border)', borderRadius: 'var(--aura-radius-sm)', color: 'var(--aura-text-primary)' }} placeholder="e.g. CPT-99213" />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <label style={{ fontSize: '14px', fontWeight: 500, color: 'var(--aura-text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}><DollarSign size={16} /> Billed Amount</label>
              <input type="number" required step="0.01" value={billedAmount} onChange={e => setBilledAmount(e.target.value)} style={{ padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--aura-border)', borderRadius: 'var(--aura-radius-sm)', color: 'var(--aura-text-primary)' }} placeholder="0.00" />
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
             <label style={{ fontSize: '14px', fontWeight: 500, color: 'var(--aura-text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}><FileText size={16} /> Supporting Document (PDF/Image)</label>
             <div {...getSingleDocProps()} style={{ border: '2px dashed var(--aura-border)', borderRadius: 'var(--aura-radius)', padding: '32px', textAlign: 'center', cursor: 'pointer', background: 'rgba(0,0,0,0.2)', transition: 'var(--aura-transition)' }}>
               <input {...getSingleDocInput()} />
               {singleDoc ? (
                 <div className="flex-col items-center">
                   <CheckCircle color="var(--aura-success)" size={32} style={{ marginBottom: '8px' }} />
                   <p style={{ fontWeight: 500 }}>{singleDoc.name}</p>
                   <p className="aura-text-muted" style={{ fontSize: '14px', marginTop: '4px' }}>{(singleDoc.size / 1024).toFixed(1)} KB</p>
                 </div>
               ) : (
                 <div className="flex-col items-center aura-text-muted">
                   <Upload size={32} style={{ marginBottom: '8px' }} />
                   <p>Drag & drop supporting document here</p>
                   <p style={{ fontSize: '14px', marginTop: '4px' }}>Only .pdf, .jpg, .png allowed</p>
                 </div>
               )}
             </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
            <button 
              type="submit"
              disabled={uploading}
              className="aura-button primary"
              style={{ opacity: uploading ? 0.5 : 1, cursor: uploading ? 'not-allowed' : 'pointer' }}
            >
              {uploading ? 'Uploading...' : 'Submit Claim'}
            </button>
          </div>
        </form>
      )}

      {activeTab === 'bulk' && (
        <>
          <div className="aura-dashboard-grid" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: '24px' }}>
            {/* Manifest Upload */}
            <div className="aura-card">
              <h3 style={{ fontSize: '18px', fontWeight: 500, marginBottom: '16px', display: 'flex', alignItems: 'center' }}>
                <FileText size={20} color="var(--aura-accent)" style={{ marginRight: '8px' }} /> 1. Upload CSV Manifest
              </h3>
              <div {...getManifestProps()} style={{ border: '2px dashed var(--aura-border)', borderRadius: 'var(--aura-radius)', padding: '32px', textAlign: 'center', cursor: 'pointer', background: 'rgba(0,0,0,0.2)', transition: 'var(--aura-transition)' }}>
                <input {...getManifestInput()} />
                {manifest ? (
                  <div className="flex-col items-center">
                    <CheckCircle color="var(--aura-success)" size={32} style={{ marginBottom: '8px' }} />
                    <p style={{ fontWeight: 500 }}>{manifest.name}</p>
                    <p className="aura-text-muted" style={{ fontSize: '14px', marginTop: '4px' }}>{(manifest.size / 1024).toFixed(1)} KB</p>
                  </div>
                ) : (
                  <div className="flex-col items-center aura-text-muted">
                    <Upload size={32} style={{ marginBottom: '8px' }} />
                    <p>Drag & drop manifest.csv here</p>
                    <p style={{ fontSize: '14px', marginTop: '4px' }}>Only .csv files allowed</p>
                  </div>
                )}
              </div>
            </div>

            {/* Documents Upload */}
            <div className="aura-card" style={{ display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 500, marginBottom: '16px', display: 'flex', alignItems: 'center' }}>
                <File size={20} color="var(--aura-accent)" style={{ marginRight: '8px' }} /> 2. Upload Documents
              </h3>
              <div {...getDocsProps()} style={{ border: '2px dashed var(--aura-border)', borderRadius: 'var(--aura-radius)', padding: '32px', textAlign: 'center', cursor: 'pointer', background: 'rgba(0,0,0,0.2)', transition: 'var(--aura-transition)', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                <input {...getDocsInput()} />
                <div className="flex-col items-center aura-text-muted">
                  <Upload size={32} style={{ marginBottom: '8px' }} />
                  <p>Drag & drop supporting PDFs/Images</p>
                  <p style={{ fontSize: '14px', marginTop: '4px' }}>Can select multiple files</p>
                </div>
              </div>
            </div>
          </div>

          {documents.length > 0 && (
            <div className="aura-card" style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '12px', fontWeight: 500, color: 'var(--aura-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>Queued Documents ({documents.length})</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {documents.map((doc, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--aura-border)', padding: '4px 12px', borderRadius: '4px', fontSize: '14px' }}>
                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '150px' }}>{doc.name}</span>
                    <button onClick={() => removeDoc(doc.name)} style={{ background: 'none', border: 'none', color: 'var(--aura-text-muted)', marginLeft: '8px', cursor: 'pointer' }}><XCircle size={14} /></button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '24px' }}>
            <button 
              onClick={handleBulkUpload} 
              disabled={!manifest || uploading}
              className="aura-button primary"
              style={{ opacity: (!manifest || uploading) ? 0.5 : 1, cursor: (!manifest || uploading) ? 'not-allowed' : 'pointer' }}
            >
              {uploading ? 'Processing Upload...' : 'Submit Batch'}
            </button>
          </div>
        </>
      )}

      {/* Results Panel */}
      {results && (
        <div className="aura-card" style={{ marginTop: '32px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 500, marginBottom: '16px' }}>Upload Results</h3>
          {results.message && (
            <div style={{ marginBottom: '16px', padding: '16px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#6ee7b7', borderRadius: 'var(--aura-radius-sm)' }}>
              <p style={{ fontWeight: 600 }}>{results.message}</p>
              {results.processed_count && <p style={{ fontSize: '14px', marginTop: '4px' }}>Successfully queued {results.processed_count} claim(s).</p>}
            </div>
          )}
          {results.errors && results.errors.length > 0 && (
            <div style={{ marginTop: '16px' }}>
              <h4 style={{ fontSize: '12px', fontWeight: 500, color: '#fca5a5', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Errors</h4>
              <div className="flex-col gap-2">
                {results.errors.map((err, i) => (
                  <div key={i} style={{ display: 'flex', padding: '12px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '4px', color: '#fca5a5', fontSize: '14px' }}>
                    <span style={{ fontFamily: 'var(--aura-mono)', background: 'rgba(0,0,0,0.2)', padding: '2px 8px', borderRadius: '4px', marginRight: '12px' }}>Row {err.row}</span>
                    <span>{err.error}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ClaimUpload;
