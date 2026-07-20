import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import { Dashboard } from './pages/Dashboard';
import { Documents } from './pages/Documents';
import { Chat } from './pages/Chat';
import { Settings } from './pages/Settings';
import { DashboardLayout } from './layouts/DashboardLayout';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Default entry point goes directly to dashboard */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          {/* Core Workspace Routes */}
          <Route
            path="/dashboard"
            element={
              <DashboardLayout>
                <Dashboard />
              </DashboardLayout>
            }
          />
          <Route
            path="/documents"
            element={
              <DashboardLayout>
                <Documents />
              </DashboardLayout>
            }
          />
          <Route
            path="/chat"
            element={
              <DashboardLayout>
                <Chat />
              </DashboardLayout>
            }
          />
          <Route
            path="/settings"
            element={
              <DashboardLayout>
                <Settings />
              </DashboardLayout>
            }
          />

          {/* Catch all unmatched routes and send to dashboard */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
