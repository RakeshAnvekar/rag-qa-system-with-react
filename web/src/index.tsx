// src/index.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App"; // App.tsx in same folder

const rootEl = document.getElementById("root") as HTMLElement | null;
if (!rootEl) {
  throw new Error("Root element not found — make sure public/index.html contains <div id='root'></div>");
}

const root = ReactDOM.createRoot(rootEl);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
