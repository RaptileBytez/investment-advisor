import { Route, Routes, Navigate } from "react-router-dom";

import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
