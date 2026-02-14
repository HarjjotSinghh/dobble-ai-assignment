/**
 * Main App Component - Routes and Layout
 */

import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Login from './pages/Login';
import PatientDashboard from './pages/PatientDashboard';
import DoctorDashboard from './pages/DoctorDashboard';

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white font-sans">
        <div className="text-center space-y-6 animate-fade-in">
          <div className="relative">
            <div className="w-16 h-16 border-2 border-slate-100 border-t-slate-900 rounded-full animate-spin mx-auto"></div>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-2 h-2 bg-slate-900 rounded-full animate-pulse"></div>
            </div>
          </div>
          <div>
            <h2 className="text-lg font-display font-bold text-slate-900 tracking-tight">CareBridge</h2>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-700 font-black mt-1">Initializing Intelligence</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={!user ? <Login /> : <Navigate to="/" />}
      />
      <Route
        path="/*"
        element={
          !user ? (
            <Navigate to="/login" />
          ) : user.role === 'doctor' ? (
            <DoctorDashboard />
          ) : (
            <PatientDashboard />
          )
        }
      />
    </Routes>
  );
}

export default App;
