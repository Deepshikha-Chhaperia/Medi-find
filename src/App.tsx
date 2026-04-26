import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import Index from "./pages/Index.tsx";
import NotFound from "./pages/NotFound.tsx";
import Results from "./pages/Results.tsx";
import MapPage from "./pages/MapPage.tsx";
import FacilityDetail from "./pages/FacilityDetail.tsx";
import Admin from "./pages/Admin.tsx";
import Insights from "./pages/Insights.tsx";
import Compare from "./pages/Compare.tsx";
import { AppShell } from "./components/layout/AppShell";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AppShell>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/results" element={<Results />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/facility/:id" element={<FacilityDetail />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="/insights" element={<Insights />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AppShell>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
