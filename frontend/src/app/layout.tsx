import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";

export const metadata: Metadata = {
  title: "OpenCrime – Public Crime Intelligence",
  description:
    "Open-source platform transforming public crime records into structured, searchable, privacy-preserving data.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">
        <Header />
        <main>{children}</main>
        <footer className="border-t bg-white mt-16 py-8">
          <div className="max-w-7xl mx-auto px-4 text-center text-sm text-gray-500">
            <p>OpenCrime — Open-source public crime intelligence platform</p>
            <p className="mt-1">
              Data sourced from public records. All PII automatically redacted.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
