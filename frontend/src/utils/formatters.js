export const formatDate = (dateString) => {
  if (!dateString) return 'Not Available';
  
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return 'Not Available';
  
  return date.toLocaleString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  });
};

export const formatStatus = (status) => {
  if (!status) return 'Unknown';
  
  const statusMap = {
    'uploaded': 'Uploaded',
    'processing': 'Processing',
    'pending_ocr': 'Pending OCR',
    'action_required': 'Action Required',
    'under_review': 'Under Review',
    'approved': 'Approved',
    'rejected': 'Rejected',
    'denied': 'Denied'
  };

  return statusMap[status.toLowerCase()] || status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

export const formatProcedureLabel = (label) => {
  if (!label) return 'Unknown';
  
  const labelMap = {
    'invalid_code': 'Invalid Code',
    'description_mismatch': 'Description Mismatch',
    'missing_code': 'Missing Code',
    'suspicious_combination': 'Suspicious Combination',
    'upcoding_risk': 'Upcoding Risk',
    'unbundling_risk': 'Unbundling Risk'
  };

  return labelMap[label.toLowerCase()] || label.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

export const CURRENCY_CONFIG = {
  code: 'USD',
  symbol: '$',
  locale: 'en-US'
};

export const formatCurrency = (amount) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return `${CURRENCY_CONFIG.symbol}0.00`;
  }
  return new Intl.NumberFormat(CURRENCY_CONFIG.locale, {
    style: 'currency',
    currency: CURRENCY_CONFIG.code
  }).format(amount);
};
