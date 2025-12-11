// src/App.tsx
import React from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import UserChat from "./Pages/UserChat";
import AdminPage from "./Pages/AdminPage";


export default function App() {
  return (
    <BrowserRouter>
      <nav style={{ padding: 12, borderBottom: "1px solid #eee" }}>
        <Link to="/admin" style={{ marginRight: 12 }}>Admin</Link>
        <Link to="/chat">Chat</Link>
      </nav>
      <Routes>
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/chat" element={<UserChat />} />
        <Route index element={<UserChat />} />
      </Routes>
    </BrowserRouter>
  );
}
