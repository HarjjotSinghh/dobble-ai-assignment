/**
 * Patient Dashboard - Chat interface for booking appointments.
 *
 * The patient interacts with the AI assistant via natural language
 * to check doctor availability and book appointments.
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { appointmentAPI } from '../services/api';
import ChatInterface from '../components/ChatInterface';
import NotificationPanel from '../components/NotificationPanel';

export default function PatientDashboard() {
  const { user, logout } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [activeTab, setActiveTab] = useState('chat');

  useEffect(() => {
    appointmentAPI.getMyAppointments()
      .then((res) => setAppointments(res.data))
      .catch(() => {});
  }, []);

  const statusColors = {
    scheduled: 'bg-blue-100 text-blue-700',
    completed: 'bg-emerald-100 text-emerald-700',
    cancelled: 'bg-red-100 text-red-700',
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top Bar */}
      <header className="bg-white border-b border-slate-200 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-900">MediAssist AI</h1>
              <p className="text-xs text-slate-500">Patient Portal</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-600">
              Welcome, <strong>{user?.name}</strong>
            </span>
            <span className="bg-blue-100 text-blue-700 text-xs px-2 py-1 rounded-full font-medium">
              Patient
            </span>
            <button
              onClick={logout}
              className="text-sm text-slate-500 hover:text-slate-700"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="max-w-7xl mx-auto px-6 mt-4">
        <div className="flex gap-1 bg-slate-100 p-1 rounded-xl w-fit">
          {['chat', 'appointments', 'notifications'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-4">
        {activeTab === 'chat' && (
          <div className="h-[calc(100vh-180px)]">
            <ChatInterface role="patient" />
          </div>
        )}

        {activeTab === 'appointments' && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h3 className="font-semibold text-slate-900">My Appointments</h3>
            </div>
            <div className="divide-y divide-slate-100">
              {appointments.length === 0 ? (
                <div className="p-8 text-center text-slate-400">
                  <p>No appointments yet. Use the AI assistant to book one!</p>
                </div>
              ) : (
                appointments.map((apt) => (
                  <div key={apt.id} className="px-6 py-4 hover:bg-slate-50">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-slate-900">
                          {apt.doctor_name}
                        </p>
                        <p className="text-sm text-slate-500">
                          {apt.date} at {apt.start_time} - {apt.end_time}
                        </p>
                        {apt.reason && (
                          <p className="text-sm text-slate-400 mt-1">
                            Reason: {apt.reason}
                          </p>
                        )}
                      </div>
                      <span
                        className={`text-xs px-3 py-1 rounded-full font-medium ${
                          statusColors[apt.status] || 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {apt.status}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {activeTab === 'notifications' && <NotificationPanel />}
      </main>
    </div>
  );
}
