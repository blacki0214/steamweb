import { Route, Routes } from "react-router-dom";
import { MainLayout } from "./components/layout/MainLayout";
import { DiscoveryHome } from "./pages/DiscoveryHome/DiscoveryHome";

function GameDetailPage() {
  return <div className="p-8 text-on-surface">Game detail layout (Placeholder).</div>;
}

export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<DiscoveryHome />} />
        <Route path="/game/:gameId" element={<GameDetailPage />} />
      </Route>
    </Routes>
  );
}
