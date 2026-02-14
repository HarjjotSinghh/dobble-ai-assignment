/**
 * Patient Dashboard - Refined Minimalist Design
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { appointmentAPI } from '../services/api';
import ChatInterface from '../components/ChatInterface';
import NotificationPanel from '../components/NotificationPanel';
import {
  MessageSquare,
  Calendar,
  Bell,
  LogOut,
  User,
  Stethoscope,
  ChevronRight,
  Clock
} from 'lucide-react';

export default function PatientDashboard() {
  const { user, logout } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [activeTab, setActiveTab] = useState('chat');

  useEffect(() => {
    appointmentAPI.getMyAppointments()
      .then((res) => setAppointments(res.data))
      .catch(() => { });
  }, []);

  const statusStyles = {
    scheduled: 'bg-accent-light text-slate-950 border-accent-dark/30',
    completed: 'bg-emerald-50 text-emerald-900 border-emerald-300',
    cancelled: 'bg-red-50 text-red-900 border-red-300',
  };

  const navItems = [
    { id: 'chat', label: 'AI Assistant', icon: MessageSquare },
    { id: 'appointments', label: 'Appointments', icon: Calendar },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ];

  return (
    <div className="flex h-screen bg-white font-sans text-slate-900">
      {/* Sidebar Navigation */}
      <aside className="w-72 border-r border-slate-200 flex flex-col p-6 gap-8 bg-slate-50">
        <div className="flex items-center gap-3 px-2">
          <div className="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center border border-slate-950">
            <Stethoscope className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-display font-bold tracking-tight text-slate-950">CareBridge</h1>
            <p className="text-xs uppercase tracking-widest text-slate-700 font-black">Patient Portal</p>
          </div>
        </div>

        <nav className="flex-1 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all group border ${activeTab === item.id
                  ? 'bg-slate-900 text-white border-slate-950 shadow-md'
                  : 'text-slate-700 hover:bg-slate-100 hover:text-slate-950 border-transparent hover:border-slate-200'
                  }`}
              >
                <Icon className={`w-5 h-5 ${activeTab === item.id ? 'text-white' : 'text-slate-500 group-hover:text-slate-950'}`} />
                {item.label}
                {activeTab === item.id && <ChevronRight className="ml-auto w-4 h-4 opacity-50" />}
              </button>
            );
          })}
        </nav>

        <div className="mt-auto pt-6 border-t border-slate-200 space-y-4">
          <div className="flex items-center gap-3 px-2">
            <div className="w-10 h-10 rounded-full bg-white border border-slate-300 flex items-center justify-center text-slate-950 font-black shadow-sm">
              {user?.name?.charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold truncate text-slate-950">{user?.name}</p>
              <p className="text-xs text-slate-700 truncate font-black uppercase tracking-tighter">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold text-red-700 border border-transparent hover:bg-red-50 hover:border-red-200 transition-all uppercase tracking-widest"
          >
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-white">
        <header className="h-20 border-b border-slate-200 bg-slate-50/50 backdrop-blur-md px-8 flex items-center justify-between">
          <h2 className="text-2xl font-display font-bold text-slate-950">
            {navItems.find(i => i.id === activeTab)?.label}
          </h2>
        </header>

        <div className="flex-1 overflow-y-auto p-8 animate-fade-in">
          {activeTab === 'chat' && (
            <div className="h-full max-w-5xl mx-auto">
              <ChatInterface role="patient" />
            </div>
          )}

          {activeTab === 'appointments' && (
            <div className="max-w-4xl mx-auto space-y-6">
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h3 className="text-xl font-display font-bold text-slate-950">Upcoming Visits</h3>
                  <p className="text-slate-700 text-sm font-medium">Manage your scheduled healthcare consultations.</p>
                </div>
              </div>

              {appointments.length === 0 ? (
                <div className="bg-slate-50 rounded-3xl p-16 text-center border border-slate-300">
                  <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-4 text-slate-900 border border-slate-200 shadow-sm">
                    <Calendar className="w-8 h-8" />
                  </div>
                  <h4 className="text-lg font-bold text-slate-950 font-display">No appointments found</h4>
                  <p className="text-slate-700 max-w-xs mx-auto mt-2 font-medium">Use the AI assistant to find a doctor and book your next visit.</p>
                  <button
                    onClick={() => setActiveTab('chat')}
                    className="mt-6 px-8 py-3 bg-slate-900 text-white rounded-xl font-bold border border-slate-950 transition-all duration-300 active:scale-[0.98] uppercase tracking-widest text-xs shadow-lg shadow-slate-900/20"
                  >
                    Go to Chat
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4">
                  {appointments.map((apt) => (
                    <div
                      key={apt.id}
                      className="bg-white p-6 rounded-2xl border border-slate-200 flex items-center justify-between group hover:border-slate-400 transition-all shadow-sm"
                    >
                      <div className="flex items-center gap-5">
                        <div className="w-14 h-14 bg-slate-50 rounded-2xl flex items-center justify-center text-slate-900 font-display font-black group-hover:bg-slate-900 group-hover:text-white border border-slate-200 transition-colors">
                          <User className="w-6 h-6" />
                        </div>
                        <div>
                          <p className="text-lg font-display font-bold text-slate-950">
                            {apt.doctor_name}
                          </p>
                          <div className="flex items-center gap-4 mt-1 text-sm text-slate-700 font-bold">
                            <span className="flex items-center gap-1.5">
                              <Calendar className="w-4 h-4 text-slate-500" />
                              {apt.date}
                            </span>
                            <span className="flex items-center gap-1.5">
                              <Clock className="w-4 h-4 text-slate-500" />
                              {apt.start_time} - {apt.end_time}
                            </span>
                          </div>
                          {apt.reason && (
                            <p className="text-xs text-slate-800 mt-2 bg-slate-100 w-fit px-2 py-1 rounded-md border border-slate-200 font-black uppercase tracking-tighter">
                              REASON: {apt.reason}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-3">
                        <span
                          className={`text-xs px-3 py-1 rounded-full font-black uppercase tracking-[0.1em] border ${statusStyles[apt.status] || 'bg-slate-50 text-slate-700 border-slate-300'
                            }`}
                        >
                          {apt.status}
                        </span>
                        <button className="text-xs text-slate-600 font-black uppercase tracking-widest hover:text-slate-950 transition-colors underline decoration-slate-200 underline-offset-4">
                          View Details
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="max-w-3xl mx-auto">
              <NotificationPanel />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}