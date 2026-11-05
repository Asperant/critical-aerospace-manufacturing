import { Navigate, Route, Routes } from "react-router-dom";

import { RootLayout } from "./layout/RootLayout";
import { NotFoundPage } from "./routes/NotFoundPage";
import { OverviewPage } from "./routes/OverviewPage";
import { DemoLabPage } from "./routes/DemoLabPage";
import { SystemViewPage } from "./routes/SystemViewPage";

export function App() {
  return (
    <Routes>
      <Route element={<RootLayout />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="demo-lab" element={<DemoLabPage />} />
        <Route path="system" element={<SystemViewPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
