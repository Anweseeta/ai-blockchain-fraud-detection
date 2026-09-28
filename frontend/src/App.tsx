import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { Analyze } from "./pages/Analyze";
import { Batch } from "./pages/Batch";
import { Dashboard } from "./pages/Dashboard";
import { History } from "./pages/History";
import { NotFound } from "./pages/NotFound";
import { PredictionDetail } from "./pages/PredictionDetail";
import { Status } from "./pages/Status";

const qc = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 15000, retry: 1 },
  },
});

export function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="analyze" element={<Analyze />} />
            <Route path="batch" element={<Batch />} />
            <Route path="history" element={<History />} />
            <Route path="predictions/:id" element={<PredictionDetail />} />
            <Route path="status" element={<Status />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
