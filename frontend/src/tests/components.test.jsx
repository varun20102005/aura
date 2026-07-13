import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../api/axios';
import NotificationsPanel from '../components/NotificationsPanel';
import BulkUpload from '../pages/BulkUpload';

// Mock axios
vi.mock('../api/axios');

describe('NotificationsPanel Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders correctly and fetches notifications', async () => {
    const mockNotifications = [
      { id: 1, type: 'assignment', payload: { message: 'New case' }, created_at: '2023-01-01', read_at: null }
    ];
    api.get.mockResolvedValueOnce({ data: mockNotifications });
    localStorage.setItem('token', 'dummy_token');

    render(<NotificationsPanel />);

    // Wait for badge to appear indicating unread count
    await waitFor(() => {
      expect(screen.getByTitle('1 unread')).toBeInTheDocument();
    });

    // Click bell to open panel
    fireEvent.click(screen.getByRole('button'));

    expect(screen.getByText('Notifications')).toBeInTheDocument();
    expect(screen.getByText(/assignment/i)).toBeInTheDocument();
  });
});

describe('BulkUpload Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders upload instructions', () => {
    render(<BulkUpload />);
    expect(screen.getByText('Patient Reference')).toBeInTheDocument();
    expect(screen.getByText('Provider Reference')).toBeInTheDocument();
    expect(screen.getByText('Submit Claim')).toBeInTheDocument();
  });
});
