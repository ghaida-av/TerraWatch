import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import AppRoutes from './app/router';
import { InvestigationProvider } from './store/InvestigationContext';
import './styles/index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <InvestigationProvider>
        <AppRoutes />
      </InvestigationProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
