/**
 * Doctor Dashboard - Summary reports, appointment management, and AI chat.
 *
 * Doctors can:
 * - View appointment statistics via the AI assistant
 * - Get natural language reports ("How many patients visited yesterday?")
 * - Trigger reports via dashboard buttons
 * - Receive notifications via Slack/in-app
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { appointmentAPI, chatAPI } from '../services/api';
import ChatInterface from '../components/ChatInterface';
import NotificationPanel from '../components/NotificationPanel';

export default function DoctorDashboard() {
  const { user, logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [appointments, setAppointments] = useState([]);
  const [activeTab, setActiveTab] = useState('chat');
  const [reportLoading, setReportLoading] = useState(false);
  const [reportResult, setReportResult] = useState('');

  useEffect(() => {
    // Fetch today's stats
    appointmentAPI.getDoctorStats()
      .then((res) => setStats(res.data))
      .catch(() => {});

    // Fetch appointments
    appointmentAPI.getMyAppointments()
      .then((res) => setAppointments(res.data))
      .catch(() => {});
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
            <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-900">MediAssist AI</h1>
              <p className="text-xs text-slate-500">Doctor Portal</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-600">
              Welcome, <strong>{user?.name}</strong>
            </span>
            <span className="bg-emerald-100 text-emerald-700 text-xs px-2 py-1 rounded-full font-medium">
              Doctor
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
          {['chat', 'dashboard', 'appointments', 'notifications'].map((tab) => (
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
            <ChatInterface role="doctor" />
          </div>
        )}

        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <StatCard
                label="Today's Appointments"
                value={stats?.scheduled || 0}
                color="blue"
              />
              <StatCard
                label="Completed"
                value={stats?.completed || 0}
                color="emerald"
              />
              <StatCard
                label="Cancelled"
                value={stats?.cancelled || 0}
                color="red"
              />
              <StatCard
                label="Total"
                value={stats?.total_appointments || 0}
                color="purple"
              />
            </div>

            {/* Quick Report Buttons */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
              <h3 className="font-semibold text-slate-900 mb-4">
                Quick Reports (AI-Generated)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <ReportButton
                  label="Yesterday's Summary"
                  query="How many patients visited yesterday? Give me a detailed summary with patient names and reasons."
                  onClick={triggerReport}
                  loading={reportLoading}
                />
                <ReportButton
                  label="Today's Schedule"
                  query="How many appointments do I have today? List all with patient names and times."
                  onClick={triggerReport}
                  loading={reportLoading}
                />
                <ReportButton
                  label="This Week Overview"
                  query="Give me an overview of my appointments for this week - from Monday to today. Also send this as a Slack notification."
                  onClick={triggerReport}
                  loading={reportLoading}
                />
                <ReportButton
                  label="Fever Patients"
                  query="How many patients visited me with fever in the last 7 days? List their names and appointment dates."
                  onClick={triggerReport}
                  loading={reportLoading}
                />
              </div>

              {/* Report Result */}
              {(reportResult || reportLoading) && (
                <div className="mt-4 p-4 bg-slate-50 rounded-xl">
                  {reportLoading ? (
                    <div className="flex items-center gap-2 text-slate-500">
                      <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-sm">AI is generating your report...</span>
                    </div>
                  ) : (
                    <div className="text-sm text-slate-700 whitespace-pre-wrap">
                      {reportResult}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Visit Reasons */}
            {stats?.visit_reasons && Object.keys(stats.visit_reasons).length > 0 && (
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
                <h3 className="font-semibold text-slate-900 mb-4">Visit Reasons (Today)</h3>
                <div className="space-y-2">
                  {Object.entries(stats.visit_reasons).map(([reason, count]) => (
                    <div key={reason} className="flex items-center justify-between py-2">
                      <span className="text-sm text-slate-600 capitalize">{reason}</span>
                      <span className="text-sm font-medium text-slate-900 bg-slate-100 px-3 py-1 rounded-full">
                        {count} visit{count > 1 ? 's' : ''}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'appointments' && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h3 className="font-semibold text-slate-900">My Appointments</h3>
            </div>
            <div className="divide-y divide-slate-100">
              {appointments.length === 0 ? (
                <div className="p-8 text-center text-slate-400">No appointments found.</div>
              ) : (
                appointments.map((apt) => (
                  <div key={apt.id} className="px-6 py-4 hover:bg-slate-50">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-slate-900">
                          {apt.patient_name}
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

function StatCard({ label, value, color }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    emerald: 'bg-emerald-50 text-emerald-600 border-emerald-200',
    red: 'bg-red-50 text-red-600 border-red-200',
    purple: 'bg-purple-50 text-purple-600 border-purple-200',
  };

  return (
    <div className={`rounded-2xl border p-5 ${colors[color]}`}>
      <p className="text-sm opacity-75">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
    </div>
  );
}

function ReportButton({ label, query, onClick, loading }) {
  return (
    <button
      onClick={() => onClick(query)}
      disabled={loading}
      className="flex items-center gap-3 p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors text-left disabled:opacity-50"
    >
      <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center flex-shrink-0">
        <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
      <div>
        <p className="font-medium text-slate-900 text-sm">{label}</p>
        <p className="text-xs text-slate-500 mt-0.5">Click to generate AI report</p>
      </div>
    </button>
  );
}
