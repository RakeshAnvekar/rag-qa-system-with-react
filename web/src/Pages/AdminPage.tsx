import React, { useState } from "react";

const API_BASE = "http://localhost:8000";

const AdminPage: React.FC = () => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [responseMsg, setResponseMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      // Convert FileList to Array and append to existing selection
      const filesArray = Array.from(e.target.files);
      setSelectedFiles((prev) => [...prev, ...filesArray]);
      setResponseMsg(null);
      setErrorMsg(null);
      // Clear the input so selecting the same file again will trigger change
      e.currentTarget.value = "";
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleClearAll = () => {
    setSelectedFiles([]);
  };

const handleUpload = async () => {
  if (!selectedFiles || selectedFiles.length === 0) {
    setErrorMsg("Please select at least one file to upload.");
    return;
  }

  setUploading(true);
  setResponseMsg(null);
  setErrorMsg(null);

  try {
    const formData = new FormData();

    // append each file with the key "files" (backend expects files: List[UploadFile])
    selectedFiles.forEach((file) => {
      formData.append("files", file);
    });

    // optional fields
    formData.append("collection_name", "company_docs");

    const res = await fetch("http://localhost:8000/api/admin/upload", {
      method: "POST",
      // IMPORTANT: do NOT set 'Content-Type' header manually
      body: formData,
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Upload failed: ${res.status} ${text}`);
    }

    const data = await res.json();
    setResponseMsg(`Uploaded successfully! Added chunks: ${data.added_chunks}`);
    setSelectedFiles([]);
  } catch (err: any) {
    setErrorMsg(err.message || "Something went wrong during upload.");
  } finally {
    setUploading(false);
  }
};


  return (
    <div style={styles.container}>
      <h2>Admin – Upload Documents</h2>

      <div style={styles.box}>
        <input
          type="file"
          onChange={handleFileChange}
          multiple
          accept=".txt,.pdf,.docx,.pptx" // optional: restrict types
        />

        {selectedFiles.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <strong>Files to upload:</strong>
            <ul>
              {selectedFiles.map((f, i) => (
                <li key={`${f.name}-${i}`} style={{ marginTop: 6 }}>
                  <span>{f.name} ({Math.round(f.size / 1024)} KB)</span>
                  <button
                    onClick={() => handleRemoveFile(i)}
                    style={styles.removeButton}
                    type="button"
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
            <button onClick={handleClearAll} style={styles.smallButton} type="button">
              Clear All
            </button>
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={uploading || selectedFiles.length === 0}
          style={{ ...styles.button, opacity: uploading || selectedFiles.length === 0 ? 0.7 : 1 }}
        >
          {uploading ? "Uploading..." : `Upload ${selectedFiles.length > 0 ? `(${selectedFiles.length})` : ""}`}
        </button>

        {responseMsg && (
          <div style={{ ...styles.message, color: "green" }}>{responseMsg}</div>
        )}

        {errorMsg && (
          <div style={{ ...styles.message, color: "red" }}>{errorMsg}</div>
        )}
      </div>
    </div>
  );
};

// Basic inline styles (replace with Tailwind/Material UI later)
const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: "30px",
    maxWidth: "720px",
    margin: "0 auto",
    fontFamily: "Arial, sans-serif",
  },
  box: {
    border: "1px solid #ccc",
    padding: "20px",
    borderRadius: "6px",
    backgroundColor: "#fafafa",
  },
  button: {
    marginTop: "15px",
    padding: "10px 20px",
    backgroundColor: "#4CAF50",
    color: "#fff",
    border: "none",
    cursor: "pointer",
    borderRadius: "4px",
  },
  smallButton: {
    marginTop: 8,
    marginLeft: 8,
    padding: "6px 10px",
    backgroundColor: "#1976d2",
    color: "#fff",
    border: "none",
    cursor: "pointer",
    borderRadius: "4px",
  },
  removeButton: {
    marginLeft: 12,
    padding: "4px 8px",
    backgroundColor: "#f44336",
    color: "#fff",
    border: "none",
    cursor: "pointer",
    borderRadius: "4px",
  },
  message: {
    marginTop: "15px",
    fontWeight: "bold",
  },
};

export default AdminPage;
