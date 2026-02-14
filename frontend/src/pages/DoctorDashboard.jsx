/**
 * Doctor Dashboard - Refined Minimalist Design
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { appointmentAPI, chatAPI } from '../services/api';
import ChatInterface from '../components/ChatInterface';
import NotificationPanel from '../components/NotificationPanel';
import {
  LayoutDashboard,
  MessageSquare,
  Calendar,
  Bell,
  LogOut,
  User,
  Stethoscope,
  ChevronRight,
  TrendingUp,
  FileText,
  Activity,
  ArrowUpRight
} from 'lucide-react';

export default function DoctorDashboard() {
  const { user, logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [appointments, setAppointments] = useState([]);
  const [activeTab, setActiveTab] = useState('chat');
  const [reportLoading, setReportLoading] = useState(false);
  const [reportResult, setReportResult] = useState('');

  useEffect(() => {
    appointmentAPI.getDoctorStats()
      .then((res) => setStats(res.data))
      .catch(() => { });

    appointmentAPI.getMyAppointments()
      .then((res) => setAppointments(res.data))
      .catch(() => { });
  }, []);

  const triggerReport = async (query) => {
    setReportLoading(true);
    setReportResult('');
    try {
      const res = await chatAPI.sendMessage(query, null);
      setReportResult(res.data.reply);
    } catch (err) {
      setReportResult('Failed to generate report. Please try again.');
    } finally {
      setReportLoading(false);
    }
  };

  const statusStyles = {
    scheduled: 'bg-accent-light text-slate-950 border-accent-dark/30',
    completed: 'bg-emerald-50 text-emerald-900 border-emerald-300',
    cancelled: 'bg-red-50 text-red-900 border-red-300',
  };

  const navItems = [
    { id: 'chat', label: 'AI Intelligence', icon: MessageSquare },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'appointments', label: 'Patient Schedule', icon: Calendar },
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
            <p className="text-xs uppercase tracking-widest text-slate-700 font-black">Doctor Portal</p>
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
            <div className="w-10 h-10 rounded-full bg-slate-900 border border-slate-950 flex items-center justify-center text-white font-black text-sm">
              DR
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
          <div className="flex items-center gap-4">
            <div className="bg-white text-slate-950 px-3 py-1.5 rounded-lg text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2 border border-slate-300 shadow-sm">
              <div className="w-1.5 h-1.5 bg-emerald-600 rounded-full animate-pulse" />
              Live Engine
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-8 animate-fade-in">
          {activeTab === 'chat' && (
            <div className="h-full max-w-5xl mx-auto">
              <ChatInterface role="doctor" />
            </div>
          )}

          {activeTab === 'dashboard' && (
            <div className="max-w-6xl mx-auto space-y-8">
              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <StatCard
                  label="Today's Appointments"
                  value={stats?.scheduled || 0}
                  icon={Calendar}
                  color="blue"
                />
                <StatCard
                  label="Completed"
                  value={stats?.completed || 0}
                  icon={Activity}
                  color="green"
                />
                <StatCard
                  label="Cancelled"
                  value={stats?.cancelled || 0}
                  icon={Activity}
                  color="red"
                />
                <StatCard
                  label="Weekly Volume"
                  value={stats?.total_appointments || 0}
                  icon={TrendingUp}
                  color="purple"
                />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Quick Reports Section */}
                <div className="lg:col-span-2 space-y-6">
                  <div className="bg-slate-50 rounded-[2rem] border border-slate-300 p-8">
                    <div className="flex items-center justify-between mb-8">
                      <h3 className="text-xl font-display font-bold text-slate-950">AI Intelligence Reports</h3>
                      <button className="text-xs font-black uppercase tracking-widest text-slate-600 hover:text-slate-950 flex items-center gap-1 transition-colors underline decoration-slate-300 underline-offset-4">
                        View History <ArrowUpRight className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {[
                        { label: "Yesterday's Summary", query: "How many patients visited yesterday? Give me a detailed summary with patient names and reasons.", icon: FileText },
                        { label: "Today's Schedule", query: "How many appointments do I have today? List all with patient names and times.", icon: Calendar },
                        { label: "Weekly Overview", query: "Give me an overview of my appointments for this week - from Monday to today. Also send this as a Slack notification.", icon: TrendingUp },
                        { label: "Condition Tracking", query: "How many patients visited me with fever in the last 7 days? List their names and appointment dates.", icon: Activity },
                      ].map((report, idx) => (
                        <button
                          key={idx}
                          onClick={() => triggerReport(report.query)}
                          disabled={reportLoading}
                          className="flex items-start gap-4 p-5 rounded-2xl bg-white border border-slate-200 hover:bg-slate-900 group transition-all duration-300 text-left disabled:opacity-50 hover:border-slate-950 shadow-sm hover:shadow-lg"
                        >
                          <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center flex-shrink-0 group-hover:bg-white/10 group-hover:text-white group-hover:border-white/20 transition-colors shadow-sm">
                            <report.icon className="w-5 h-5 text-slate-600 group-hover:text-white" />
                          </div>
                          <div>
                            <p className="font-bold text-slate-950 group-hover:text-white transition-colors text-sm">{report.label}</p>
                            <p className="text-xs font-black text-slate-500 mt-1 group-hover:text-white/70 uppercase tracking-tighter">System Generated</p>
                          </div>
                        </button>
                      ))}
                    </div>

                    {/* Report Output */}
                    {(reportResult || reportLoading) && (
                      <div className="mt-8 p-6 rounded-2xl bg-slate-950 text-white animate-slide-up border border-black shadow-inner">
                        {reportLoading ? (
                          <div className="flex items-center gap-3">
                            <div className="w-2 h-2 bg-accent rounded-full animate-ping" />
                            <p className="text-xs font-black uppercase tracking-[0.2em] opacity-70">Synthesizing</p>
                          </div>
                        ) : (
                          <div className="prose prose-invert prose-sm max-w-none">
                            <p className="whitespace-pre-wrap leading-relaxed opacity-90 font-medium">{reportResult}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Visit Distribution */}
                <div className="space-y-6">
                  <div className="bg-white rounded-[2rem] border border-slate-300 p-8">
                    <h3 className="text-xl font-display font-bold text-slate-950 mb-6 uppercase tracking-tight">Patient Load</h3>
                    <div className="space-y-6">
                      {stats?.visit_reasons && Object.entries(stats.visit_reasons).length > 0 ? (
                        Object.entries(stats.visit_reasons).map(([reason, count]) => (
                          <div key={reason} className="group">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs font-black text-slate-900 capitalize tracking-tighter">{reason}</span>
                              <span className="text-xs font-black text-slate-600 uppercase tracking-widest">{count} Visits</span>
                            </div>
                            <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                              <div
                                className="h-full bg-slate-900 rounded-full transition-all duration-1000 group-hover:bg-slate-700"
                                style={{ width: `${(count / (stats.total_appointments || 1)) * 100}%` }}
                              />
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="text-slate-500 text-xs text-center py-8 font-black uppercase tracking-widest opacity-50">Empty Dataset</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'appointments' && (
            <div className="max-w-4xl mx-auto space-y-6">
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h3 className="text-xl font-display font-bold text-slate-950">Patient List</h3>
                  <p className="text-slate-700 text-sm font-medium">Detailed overview of your current appointment schedule.</p>
                </div>
              </div>

              <div className="bg-white rounded-[2rem] border border-slate-300 overflow-hidden shadow-sm">
                <div className="divide-y divide-slate-100">
                  {appointments.length === 0 ? (
                    <div className="p-16 text-center text-slate-400">
                      <Calendar className="w-12 h-12 mx-auto mb-4 opacity-20" />
                      <p className="font-bold uppercase tracking-widest text-xs">Schedule Clear</p>
                    </div>
                  ) : (
                    appointments.map((apt) => (
                      <div key={apt.id} className="p-6 hover:bg-slate-50/50 transition-colors flex items-center justify-between group">
                        <div className="flex items-center gap-5">
                          <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center font-black text-slate-950 group-hover:bg-slate-900 group-hover:text-white group-hover:border-slate-950 transition-all shadow-sm">
                            {apt.patient_name?.charAt(0)}
                          </div>
                          <div>
                            <p className="font-bold text-slate-950 text-base">{apt.patient_name}</p>
                            <div className="flex items-center gap-3 mt-1 text-xs text-slate-700 font-bold">
                              <span className="flex items-center gap-1">
                                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                                {apt.date}
                              </span>
                              <span className="flex items-center gap-1">
                                <Activity className="w-3.5 h-3.5 text-slate-400" />
                                {apt.start_time} - {apt.end_time}
                              </span>
                            </div>
                            {apt.reason && (
                              <p className="text-xs text-slate-900 mt-2 bg-slate-100 border border-slate-200 w-fit px-2 py-0.5 rounded uppercase tracking-tighter font-black">
                                REASON: {apt.reason}
                              </p>
                            )}
                          </div>
                        </div>
                        <span
                          className={`text-xs px-3 py-1 rounded-full font-black uppercase tracking-widest border ${statusStyles[apt.status] || 'bg-slate-50 text-slate-700 border-slate-300'
                            }`}
                        >
                          {apt.status}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
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

function StatCard({ label, value, icon: Icon, color }) {
  const themes = {
    blue: 'border-blue-300 bg-blue-50 text-blue-900',
    green: 'border-emerald-300 bg-emerald-50 text-emerald-900',
    red: 'border-red-300 bg-red-50 text-red-900',
    purple: 'border-purple-300 bg-purple-50 text-purple-900',
  };

  return (
    <div className={`rounded-[2rem] border-2 p-6 ${themes[color]} shadow-sm`}>
      <div className="flex items-center justify-between mb-4">
        <div className="p-2.5 rounded-xl bg-white border border-current border-opacity-30 shadow-sm">
          <Icon className="w-5 h-5" />
        </div>
        <span className="text-xs font-black uppercase tracking-[0.2em] opacity-80">Telemetry</span>
      </div>
      <p className="text-3xl font-display font-black tracking-tighter">{value}</p>
      <p className="text-xs font-black mt-1 uppercase tracking-widest opacity-80">{label}</p>
    </div>
  );
}