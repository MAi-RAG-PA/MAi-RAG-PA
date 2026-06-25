// MAi-RAG/frontend/src/main.tsx

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/globals.css';
import { BrowserRouter } from 'react-router-dom';

// Force scroll to top on initial load and navigation
if (window.location.hash) {
  // Clear hash to prevent browser restoring scroll position
  history.replaceState(null, null, window.location.pathname);
}
// Ensure page starts at top
window.scrollTo(0, 0);

// Also listen for popstate (back/forward navigation)
window.addEventListener('popstate', () => {
  window.scrollTo(0, 0);
});

// Load saved theme on startup
const savedTheme = localStorage.getItem('mai-rag-theme');
if (savedTheme) {
  document.documentElement.setAttribute('data-theme', savedTheme);
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
