import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import { ToastProvider } from './components/Toast';
import Agents from './pages/Agents';
import Billing from './pages/Billing';
import CRM from './pages/CRM';
import DealPage from './pages/Deal';
import InvoicePage from './pages/Invoice';
import LLMFilter from './pages/LLMFilter';
import Monitoring from './pages/Monitoring';
import Orders from './pages/Orders';
import Overview from './pages/Overview';
import Pipeline from './pages/Pipeline';
import OrchestratorChat from './pages/OrchestratorChat';
import TaskPage from './pages/Task';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5000,
    },
  },
});

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <HashRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Navigate to="/overview" replace />} />
              <Route path="/overview" element={<Overview />} />
              <Route path="/pipeline" element={<Pipeline />} />
              <Route path="/orders" element={<Orders />} />
              <Route path="/llm-filter" element={<LLMFilter />} />
              <Route path="/crm" element={<CRM />} />
              <Route path="/agents" element={<Agents />} />
              <Route path="/billing" element={<Billing />} />
              <Route path="/monitoring" element={<Monitoring />} />
              <Route path="/orchestrator" element={<OrchestratorChat />} />
              <Route path="/deal/:id" element={<DealPage />} />
              <Route path="/task/:id" element={<TaskPage />} />
              <Route path="/invoice/:id" element={<InvoicePage />} />
              <Route path="*" element={<Navigate to="/overview" replace />} />
            </Route>
          </Routes>
        </HashRouter>
      </ToastProvider>
    </QueryClientProvider>
    </ErrorBoundary>
  );
}