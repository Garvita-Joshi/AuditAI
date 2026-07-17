import React from 'react';
import { NavLink } from 'react-router-dom';
import { ShieldCheck, Upload, LayoutDashboard, FileText, Activity } from 'lucide-react';
import './Navbar.css';

export default function Navbar() {
  return (
    <nav className="navbar glass-card">
      <div className="navbar-content">
        <div className="navbar-brand">
          <ShieldCheck className="brand-icon" size={28} />
          <span className="brand-text">AuditAI</span>
        </div>
        
        <div className="navbar-links">
          <NavLink to="/" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </NavLink>
          
          <NavLink to="/upload" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
            <Upload size={18} />
            <span>Upload</span>
          </NavLink>
          
          <NavLink to="/claims" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
            <FileText size={18} />
            <span>Claims</span>
          </NavLink>

          <NavLink to="/audit-screens" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
            <Activity size={18} />
            <span>Audit Screens</span>
          </NavLink>
        </div>
      </div>
    </nav>
  );
}
