import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import ClaimsTable from './pages/ClaimsTable';
import ClaimDetail from './pages/ClaimDetail';
import AuditScreens from './pages/AuditScreens';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Navbar />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/claims" element={<ClaimsTable />} />
          <Route path="/claims/:id" element={<ClaimDetail />} />
          <Route path="/audit-screens" element={<AuditScreens />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
