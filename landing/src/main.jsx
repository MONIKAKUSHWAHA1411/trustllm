import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Reset browser defaults for full-width layout
document.body.style.margin = '0';
document.body.style.padding = '0';
document.documentElement.style.margin = '0';

const root = document.getElementById('root');
root.style.width = '100%';
root.style.maxWidth = '100%';
root.style.margin = '0';

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
