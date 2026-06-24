"use client";

import { useState, useCallback, useRef } from "react";
import { Upload, FileText, CheckCircle, XCircle, Clock, ArrowRight } from "lucide-react";
import Link from "next/link";
import { uploadDocument, getDocumentStatus } from "@/lib/api";

type Status = "idle" | "uploading" | "processing" | "completed" | "failed";

interface UploadedDoc {
  id: string;
  filename: string;
  status: Status;
  recordId?: string;
  error?: string;
}

export default function UploadPage() {
  const [docs, setDocs] = useState<UploadedDoc[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(async (files: FileList) => {
    for (const file of Array.from(files)) {
      const entry: UploadedDoc = {
        id: "",
        filename: file.name,
        status: "uploading",
      };
      setDocs((d) => [entry, ...d]);

      try {
        const res = await uploadDocument(file);
        const docId = res.id;

        setDocs((d) =>
          d.map((x) =>
            x.filename === file.name && x.status === "uploading"
              ? { ...x, id: docId, status: "processing" }
              : x
          )
        );

        // Poll for completion
        pollStatus(docId, file.name);
      } catch (e: any) {
        setDocs((d) =>
          d.map((x) =>
            x.filename === file.name && x.status === "uploading"
              ? { ...x, status: "failed", error: e?.response?.data?.detail || "Upload failed" }
              : x
          )
        );
      }
    }
  }, []);

  const pollStatus = useCallback((docId: string, filename: string) => {
    let attempts = 0;
    const max = 30;
    const interval = setInterval(async () => {
      attempts++;
      if (attempts > max) {
        clearInterval(interval);
        return;
      }
      try {
        const s = await getDocumentStatus(docId);
        if (s.status === "completed") {
          clearInterval(interval);
          setDocs((d) =>
            d.map((x) =>
              x.id === docId
                ? { ...x, status: "completed", recordId: s.crime_record_id }
                : x
            )
          );
        } else if (s.status === "failed") {
          clearInterval(interval);
          setDocs((d) =>
            d.map((x) =>
              x.id === docId ? { ...x, status: "failed", error: "Processing failed" } : x
            )
          );
        }
      } catch {
        // keep polling
      }
    }, 3000);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload Crime Document</h1>
      <p className="text-gray-500 mb-8">
        Upload scanned FIRs or police notices (PDF or image). Our AI will extract structured data
        and automatically redact personal information before publishing.
      </p>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
          dragging
            ? "border-red-500 bg-red-50"
            : "border-gray-300 bg-white hover:border-red-400 hover:bg-gray-50"
        }`}
      >
        <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-lg font-medium text-gray-700 mb-1">
          Drop files here or <span className="text-red-600">click to browse</span>
        </p>
        <p className="text-sm text-gray-500">PDF, JPG, PNG, TIFF up to 50MB</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
      </div>

      {/* Privacy notice */}
      <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-800">
        <strong>Privacy-first processing:</strong> All personal names, phone numbers, addresses,
        and ID numbers are automatically redacted before any record is published.
      </div>

      {/* Upload queue */}
      {docs.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Queue</h2>
          <div className="space-y-3">
            {docs.map((doc, i) => (
              <div
                key={`${doc.id || doc.filename}-${i}`}
                className="bg-white border border-gray-200 rounded-lg px-4 py-3 flex items-center gap-4"
              >
                <FileText className="h-5 w-5 text-gray-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{doc.filename}</p>
                  <p className="text-xs text-gray-500 capitalize">{STATUS_LABELS[doc.status]}</p>
                  {doc.error && (
                    <p className="text-xs text-red-600 mt-0.5">{doc.error}</p>
                  )}
                </div>
                <StatusIcon status={doc.status} />
                {doc.status === "completed" && doc.recordId && (
                  <Link
                    href={`/record/${doc.recordId}`}
                    className="flex items-center gap-1 text-xs text-red-600 hover:underline flex-shrink-0"
                  >
                    View <ArrowRight className="h-3 w-3" />
                  </Link>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Info box */}
      <div className="mt-10 bg-gray-50 rounded-xl border border-gray-200 p-6">
        <h2 className="font-semibold text-gray-900 mb-3">What happens after upload?</h2>
        <ol className="space-y-2 text-sm text-gray-600">
          <li className="flex gap-3"><span className="font-bold text-red-600">1</span> OCR extracts text from your document</li>
          <li className="flex gap-3"><span className="font-bold text-red-600">2</span> Claude AI extracts structured fields: crime category, FIR number, location, legal sections</li>
          <li className="flex gap-3"><span className="font-bold text-red-600">3</span> All PII (names, phone numbers, Aadhaar, addresses) is automatically redacted</li>
          <li className="flex gap-3"><span className="font-bold text-red-600">4</span> A public summary is generated and the record is published for search</li>
        </ol>
      </div>
    </div>
  );
}

const STATUS_LABELS: Record<Status, string> = {
  idle: "Waiting",
  uploading: "Uploading…",
  processing: "Processing with AI…",
  completed: "Complete",
  failed: "Failed",
};

function StatusIcon({ status }: { status: Status }) {
  if (status === "completed") return <CheckCircle className="h-5 w-5 text-green-500" />;
  if (status === "failed") return <XCircle className="h-5 w-5 text-red-500" />;
  return <Clock className="h-5 w-5 text-yellow-500 animate-pulse" />;
}
