/**
 * Notification Panel - Refined Minimalist Design
 */

import { useState, useEffect } from 'react';
import { notificationAPI } from '../services/api';
import {
  Bell,
  CheckCheck,
  Info,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Inbox
} from 'lucide-react';

export default function NotificationPanel() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = async () => {
    try {
      const res = await notificationAPI.getNotifications();
      setNotifications(res.data);
    } catch (err) {
      console.error('Failed to fetch notifications');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  const markAsRead = async (id) => {
    await notificationAPI.markAsRead(id);
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    );
  };

  const markAllRead = async () => {
    await notificationAPI.markAllRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const typeIcons = {
    success: { icon: CheckCircle2, color: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-300' },
    warning: { icon: AlertTriangle, color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-300' },
    info: { icon: Info, color: 'text-slate-800', bg: 'bg-slate-50', border: 'border-slate-300' },
  };

  return (
    <div className="bg-white rounded-[2rem] border border-slate-300 overflow-hidden flex flex-col h-full max-h-[700px] animate-fade-in shadow-sm">
      {/* Header */}
      <div className="px-8 py-6 border-b border-slate-200 flex items-center justify-between bg-slate-50">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-slate-900 rounded-2xl flex items-center justify-center text-white border border-slate-950">
            <Bell className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-display font-bold text-slate-950">Inbox</h3>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-700 font-black">
              {unreadCount} UNREAD MESSAGES
            </p>
          </div>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={markAllRead}
            className="flex items-center gap-2 px-4 py-2 text-xs font-black text-slate-700 hover:text-slate-950 hover:bg-white rounded-xl transition-all border border-slate-300 uppercase tracking-widest bg-white"
          >
            <CheckCheck className="w-4 h-4" />
            Clear All
          </button>
        )}
      </div>

      {/* Notifications List */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-100 custom-scrollbar bg-white">
        {loading ? (
          <div className="p-12 text-center">
            <div className="w-8 h-8 border-2 border-slate-200 border-t-slate-900 rounded-full animate-spin mx-auto mb-4" />
            <p className="text-xs font-black text-slate-700 uppercase tracking-[0.3em]">Synchronizing</p>
          </div>
        ) : notifications.length === 0 ? (
          <div className="p-16 text-center bg-slate-50/20">
            <div className="w-20 h-20 bg-white rounded-[2.5rem] flex items-center justify-center mx-auto mb-6 text-slate-900 border border-slate-200 shadow-sm">
              <Inbox className="w-10 h-10" />
            </div>
            <h4 className="text-lg font-display font-bold text-slate-950">All clear</h4>
            <p className="text-slate-700 mt-2 font-bold uppercase tracking-widest text-xs">Your inbox is empty</p>
          </div>
        ) : (
          notifications.map((n) => {
            const config = typeIcons[n.type] || typeIcons.info;
            const Icon = config.icon;

            return (
              <div
                key={n.id}
                onClick={() => !n.is_read && markAsRead(n.id)}
                className={`px-8 py-6 cursor-pointer transition-all relative group ${!n.is_read ? 'bg-slate-50/50' : 'hover:bg-slate-50/30'
                  }`}
              >
                {!n.is_read && (
                  <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-slate-900" />
                )}

                <div className="flex items-start gap-5">
                  <div className={`w-10 h-10 ${config.bg} rounded-xl flex items-center justify-center flex-shrink-0 border ${config.border} shadow-sm`}>
                    <Icon className={`w-5 h-5 ${config.color}`} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className={`text-sm font-bold truncate ${!n.is_read ? 'text-slate-950' : 'text-slate-800'}`}>
                        {n.title}
                      </p>
                      <span className="text-xs font-black text-slate-600 flex items-center gap-1 uppercase tracking-tighter">
                        <Clock className="w-3 h-3" />
                        {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    <p className={`text-sm leading-relaxed ${!n.is_read ? 'text-slate-900 font-bold' : 'text-slate-700 font-medium'}`}>
                      {n.message}
                    </p>

                    <div className="flex items-center gap-3 mt-4">
                      <span className="text-xs font-black uppercase tracking-[0.2em] bg-white border border-slate-300 px-2.5 py-1 rounded text-slate-700 group-hover:border-slate-900 group-hover:text-slate-900 transition-colors shadow-sm">
                        {n.channel}
                      </span>
                      {!n.is_read && (
                        <button className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 hover:underline underline-offset-4 decoration-slate-300">
                          Mark as read
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div className="px-8 py-4 bg-slate-50 border-t border-slate-200">
        <p className="text-xs text-center text-slate-600 font-black uppercase tracking-[0.4em]">
          End of Notifications
        </p>
      </div>
    </div>
  );
}