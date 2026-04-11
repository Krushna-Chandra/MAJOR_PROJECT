import React from 'react';
import { Link } from 'react-router-dom';
import logo from '../assets/Website Logo.png';

const Header = () => {
  return (
    <nav style={{
      display: 'flex',
      alignItems: 'center',
      padding: '10px 24px',
      backgroundColor: '#f8f9fa',
      borderBottom: '1px solid #e9ecef',
      minHeight: '60px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.03)'
    }}>
      <Link
        to="/"
        style={{
          display: 'flex',
          alignItems: 'center',
          textDecoration: 'none'
        }}
      >
        <img
          src={logo}
          alt="INTERVIEWR Logo"
          style={{
            height: '40px',
            width: '40px',
            borderRadius: '50%',
            marginRight: '16px',
            boxShadow: '0 1px 4px rgba(0,0,0,0.08)'
          }}
        />
        <span style={{
          fontSize: '22px',
          fontWeight: 'bold',
          color: '#333',
          letterSpacing: '2px',
          marginRight: 'auto'
        }}>INTERVIEWR</span>
      </Link>
    </nav>
  );
};

export default Header;
