import { Link, Route, Routes } from "react-router-dom";
import { Compass } from "lucide-react";

import { Layout } from "./components/Layout";
import { InboxPage } from "./pages/Inbox";
import { KnowledgePage } from "./pages/KnowledgeBase";
import { Overview } from "./pages/Overview";
import { SettingsPage } from "./pages/Settings";
import { AppProvider } from "./store/AppStore";

function NotFound() {
  return (
    <div className="card flex min-h-[420px] flex-col items-center justify-center px-6 text-center">
      <Compass className="h-8 w-8 text-slate-300" />
      <h1 className="mt-3 text-lg font-semibold text-slate-800">Page not found</h1>
      <p className="mt-1 text-sm text-slate-500">
        The page you were looking for does not exist in this workspace.
      </p>
      <Link to="/" className="btn btn-primary mt-4">
        Back to overview
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="inbox" element={<InboxPage />} />
          <Route path="inbox/:id" element={<InboxPage />} />
          <Route path="knowledge" element={<KnowledgePage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </AppProvider>
  );
}