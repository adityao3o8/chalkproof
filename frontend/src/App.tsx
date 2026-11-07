import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import ProjectPage from "./pages/ProjectPage";
import PreviewPage from "./pages/PreviewPage";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header className="topbar">
          <Link to="/" className="brand">
            Chalkproof
          </Link>
          <span className="tagline">Local AI lesson studio</span>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/projects/:id" element={<ProjectPage />} />
            <Route path="/projects/:id/preview" element={<PreviewPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
