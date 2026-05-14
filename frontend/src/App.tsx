import { Route, Routes, Navigate } from "react-router-dom";

import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Portfolio from "./pages/Portfolio";
import StockDetail from "./pages/StockDetail";
import StrategiesPage from "./pages/Strategies";
import TradeLog from "./pages/TradeLog";
import Learn from "./pages/Learn";
import LearnEntry from "./pages/LearnEntry";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/strategies" element={<StrategiesPage />} />
        <Route path="/stocks/:ticker" element={<StockDetail />} />
        <Route path="/trades" element={<TradeLog />} />
        <Route path="/learn" element={<Learn />} />
        <Route path="/learn/:term" element={<LearnEntry />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
