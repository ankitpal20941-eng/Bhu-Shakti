import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { useSession } from "./store/session";
import { applyTheme, useUi } from "./store/ui";
import { useEffect } from "react";
import Login from "./pages/Login";
import Overview from "./pages/Overview";
import RiskMap from "./pages/RiskMap";
import ResponseCenter from "./pages/ResponseCenter";
import Alerts from "./pages/Alerts";
import FieldOperations from "./pages/FieldOperations";
import Analytics from "./pages/Analytics";
import DataHealth from "./pages/DataHealth";
import Models from "./pages/Models";
import Scenarios from "./pages/Scenarios";
import Admin from "./pages/Admin";
import Citizen from "./pages/Citizen";
import SituationRoom from "./pages/SituationRoom";
import ImpactAnalysis from "./pages/ImpactAnalysis";
import RainfallIntelligence from "./pages/RainfallIntelligence";
import HistoricalReplay from "./pages/HistoricalReplay";
import DistrictComparison from "./pages/DistrictComparison";
import DataConfidence from "./pages/DataConfidence";
import ModelMonitoring from "./pages/ModelMonitoring";
import NotificationMonitor from "./pages/NotificationMonitor";
import FieldTeams from "./pages/FieldTeams";
import EmergencyFacilities from "./pages/EmergencyFacilities";
import SatelliteChange from "./pages/SatelliteChange";
import RunoutAnalysis from "./pages/RunoutAnalysis";

function Protected({ children }: { children: React.ReactElement }) {
  const token = useSession((s) => s.token);
  const user = useSession((s) => s.user);
  if (!token) return <Navigate to="/login" replace />;
  if (user?.role === "citizen") return <Navigate to="/citizen" replace />;
  return children;
}

export default function App() {
  const theme = useUi((s) => s.theme);
  useEffect(() => applyTheme(theme), [theme]);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/citizen" element={<Citizen />} />
      <Route
        element={
          <Protected>
            <AppShell />
          </Protected>
        }
      >
        <Route index element={<Overview />} />
        <Route path="/situation-room" element={<SituationRoom />} />
        <Route path="/impact-analysis" element={<ImpactAnalysis />} />
        <Route path="/rainfall-intelligence" element={<RainfallIntelligence />} />
        <Route path="/historical-replay" element={<HistoricalReplay />} />
        <Route path="/district-comparison" element={<DistrictComparison />} />
        <Route path="/data-confidence" element={<DataConfidence />} />
        <Route path="/model-monitoring" element={<ModelMonitoring />} />
        <Route path="/notification-monitor" element={<NotificationMonitor />} />
        <Route path="/field-teams" element={<FieldTeams />} />
        <Route path="/emergency-facilities" element={<EmergencyFacilities />} />
        <Route path="/satellite-change" element={<SatelliteChange />} />
        <Route path="/runout-analysis" element={<RunoutAnalysis />} />
        <Route path="/map" element={<RiskMap />} />
        <Route path="/response" element={<ResponseCenter />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/field" element={<FieldOperations />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/data-health" element={<DataHealth />} />
        <Route path="/models" element={<Models />} />
        <Route path="/scenarios" element={<Scenarios />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
