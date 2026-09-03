import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';

(window as any).openOrder = (encodedUrl: string) => {
  const url = decodeURIComponent(encodedUrl);
  const navigate = (window as any).__navigate__ || ((path: string) => { window.location.hash = '#/' + path; });
  navigate('/deal/' + encodeURIComponent(url));
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);