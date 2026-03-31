import { Link, Route, Routes } from "react-router-dom";

function DashboardPage() {
  return <div>Trending indie games will appear here.</div>;
}

function GameDetailPage() {
  return <div>Game detail layout with video and sentiment summary.</div>;
}

export default function App() {
  return (
    <main>
      <h1>Indie Game Discovery</h1>
      <nav>
        <Link to="/">Dashboard</Link> | <Link to="/game/sample-id">Game Detail</Link>
      </nav>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/game/:gameId" element={<GameDetailPage />} />
      </Routes>
    </main>
  );
}
