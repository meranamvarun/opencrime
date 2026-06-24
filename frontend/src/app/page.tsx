import Link from "next/link";
import { Search, Upload, BarChart2, Shield, Lock, Database, Globe } from "lucide-react";

export default function HomePage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-gradient-to-br from-red-700 via-red-800 to-red-900 text-white py-24">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <div className="inline-flex items-center gap-2 bg-red-600/50 rounded-full px-4 py-1.5 text-sm mb-6">
            <Shield className="h-4 w-4" />
            Open-source · Privacy-first · Public records
          </div>
          <h1 className="text-5xl font-extrabold mb-6 leading-tight">
            Public Crime Intelligence,
            <br />
            Open to Everyone
          </h1>
          <p className="text-xl text-red-100 mb-10 max-w-2xl mx-auto">
            Transform fragmented FIRs and police records into structured, searchable, and
            privacy-preserving intelligence — powered by AI.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link
              href="/search"
              className="flex items-center gap-2 bg-white text-red-700 font-semibold px-6 py-3 rounded-lg hover:bg-red-50 transition-colors"
            >
              <Search className="h-5 w-5" />
              Search Records
            </Link>
            <Link
              href="/analytics"
              className="flex items-center gap-2 bg-red-600 text-white font-semibold px-6 py-3 rounded-lg hover:bg-red-500 transition-colors border border-red-500"
            >
              <BarChart2 className="h-5 w-5" />
              View Analytics
            </Link>
            <Link
              href="/upload"
              className="flex items-center gap-2 bg-transparent text-white font-semibold px-6 py-3 rounded-lg hover:bg-red-800 transition-colors border border-red-400"
            >
              <Upload className="h-5 w-5" />
              Upload Document
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12 text-gray-900">
            Built for Transparency, Designed for Privacy
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {FEATURES.map((f) => (
              <div key={f.title} className="p-6 rounded-xl border border-gray-200 hover:border-red-200 hover:shadow-sm transition-all">
                <div className="w-12 h-12 bg-red-50 rounded-lg flex items-center justify-center mb-4">
                  <f.icon className="h-6 w-6 text-red-600" />
                </div>
                <h3 className="font-semibold text-lg mb-2 text-gray-900">{f.title}</h3>
                <p className="text-gray-600 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12 text-gray-900">How It Works</h2>
          <div className="relative">
            <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-red-200 hidden md:block" />
            {STEPS.map((step, i) => (
              <div key={i} className="flex gap-6 mb-10 relative">
                <div className="flex-shrink-0 w-16 h-16 bg-red-600 rounded-full flex items-center justify-center text-white font-bold text-lg z-10">
                  {i + 1}
                </div>
                <div className="pt-3">
                  <h3 className="font-semibold text-lg text-gray-900 mb-1">{step.title}</h3>
                  <p className="text-gray-600">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-red-700 text-white text-center">
        <div className="max-w-2xl mx-auto px-4">
          <h2 className="text-3xl font-bold mb-4">Start Exploring Crime Data</h2>
          <p className="text-red-100 mb-8">
            Search across thousands of crime records or contribute by uploading public documents.
          </p>
          <Link
            href="/search"
            className="inline-flex items-center gap-2 bg-white text-red-700 font-semibold px-8 py-3 rounded-lg hover:bg-red-50 transition-colors"
          >
            <Search className="h-5 w-5" />
            Search Now
          </Link>
        </div>
      </section>
    </div>
  );
}

const FEATURES = [
  {
    icon: Search,
    title: "AI-Powered Search",
    desc: "Ask natural language questions or use structured filters to find crime patterns across thousands of records.",
  },
  {
    icon: Lock,
    title: "Privacy by Design",
    desc: "Automatic PII detection and redaction ensures personal identities are protected before any record is published.",
  },
  {
    icon: Database,
    title: "Structured Extraction",
    desc: "Claude AI converts raw OCR text into structured data — crime category, legal sections, amount, modus operandi.",
  },
  {
    icon: BarChart2,
    title: "Trend Analytics",
    desc: "Visualize crime trends by category, time, and geography with interactive charts and heatmaps.",
  },
  {
    icon: Globe,
    title: "Open API",
    desc: "Every record is accessible via a standardized REST API for developers and researchers.",
  },
  {
    icon: Upload,
    title: "Document Ingestion",
    desc: "Upload scanned PDFs or images of public FIRs. OCR + AI handles the rest automatically.",
  },
];

const STEPS = [
  {
    title: "Upload or Ingest",
    desc: "Submit scanned PDFs or images of public crime documents via the web interface or API.",
  },
  {
    title: "OCR + AI Extraction",
    desc: "Tesseract OCR extracts text, then Claude AI identifies structured fields: crime type, location, legal sections, and more.",
  },
  {
    title: "PII Redaction",
    desc: "All personally identifiable information — names, phone numbers, Aadhaar, addresses — is automatically detected and removed.",
  },
  {
    title: "Publish & Search",
    desc: "Clean, structured, privacy-safe records are indexed for full-text search, analytics, and API access.",
  },
];
