import React, { useEffect, useState } from 'react';
import { Bell } from 'lucide-react';
import api from '../api/axios';

const NotificationsPanel = () => {
  const [notifications, setNotifications] = useState([]);
  const [isOpen, setIsOpen] = useState(false);

  const fetchNotifications = async () => {
    const token = localStorage.getItem('token');
    if (!token) return; // Prevents 401 Unauthorized errors when logged out
    try {
      const res = await api.get('/notifications');
      setNotifications(res.data);
    } catch (err) {
      console.error("Failed to fetch notifications", err);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const intv = setInterval(fetchNotifications, 30000);
    return () => clearInterval(intv);
  }, []);

  const unreadCount = notifications.filter(n => !n.read_at).length;

  const markAsRead = async (id) => {
    try {
      await api.post(`/notifications/${id}/read`);
      setNotifications(notifications.map(n => n.id === id ? { ...n, read_at: new Date().toISOString() } : n));
    } catch (err) {
      console.error("Failed to mark as read", err);
    }
  };

  return (
    <div className="aura-notification-panel">
      <button 
        onClick={() => setIsOpen(!isOpen)} 
        className="aura-notification-btn"
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span className="aura-notification-badge" title={`${unreadCount} unread`}></span>
        )}
      </button>

      {isOpen && (
        <div className="aura-dropdown">
          <div className="aura-dropdown-header">
            <h3>Notifications</h3>
          </div>
          <div className="aura-notification-list">
            {notifications.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--aura-text-muted)' }}>No notifications</div>
            ) : (
              notifications.map(notif => (
                <div 
                  key={notif.id} 
                  className={`aura-notification-item ${!notif.read_at ? 'unread' : ''}`}
                  onClick={() => !notif.read_at && markAsRead(notif.id)}
                >
                  <div className="flex justify-between items-center mb-4">
                    <span className="aura-badge" style={{ backgroundColor: 'var(--aura-accent-glow)', color: 'var(--aura-accent)' }}>{notif.type}</span>
                    <span style={{ fontSize: '12px', color: 'var(--aura-text-muted)' }}>{new Date(notif.created_at).toLocaleDateString()}</span>
                  </div>
                  <div style={{ fontSize: '13px' }}>
                    {JSON.stringify(notif.payload)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationsPanel;
