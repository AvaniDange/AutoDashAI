import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

// Import all pages/components
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import HomePage from "./pages/HomePage";
import DataCleaner from "./pages/DataCleaner";
import FileToTableConverter from "./pages/FileToTableConverter";

function App() {
  return (
    <Router>
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <Routes>
          {/* Auth Pages */}
          <Route path="/" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          {/* Main Pages */}
          <Route path="/homepage" element={<HomePage />} />
          <Route path="/data-cleaning" element={<DataCleaner />} />
          <Route path="/ai-conversion" element={<FileToTableConverter />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
