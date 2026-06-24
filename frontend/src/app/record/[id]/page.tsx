import { getRecord } from "@/lib/api";
import { formatCurrency, formatDate, CATEGORY_COLORS } from "@/lib/utils";
import { MapPin, Calendar, Scale, IndianRupee, Tag, FileText, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

export default async function RecordPage({ params }: { params: { id: string } }) {
  let record;
  try {
    record = await getRecord(params.id);
  } catch {
    notFound();
  }

  const color = CATEGORY_COLORS[record.crime_category || ""] || "#6b7280";

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Link
        href="/search"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Search
      </Link>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <span
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold text-white"
              style={{ backgroundColor: color }}
            >
              <Tag className="h-4 w-4" />
              {record.crime_category || "Unknown Category"}
            </span>
            {record.fir_number && (
              <span className="text-sm text-gray-500 font-mono bg-gray-50 px-3 py-1.5 rounded-full border">
                FIR {record.fir_number}
              </span>
            )}
          </div>

          {record.summary && (
            <p className="mt-4 text-gray-700 text-base leading-relaxed">{record.summary}</p>
          )}
        </div>

        {/* Details grid */}
        <div className="p-6 grid sm:grid-cols-2 gap-5">
          {record.crime_date && (
            <Detail icon={Calendar} label="Crime Date" value={formatDate(record.crime_date)} />
          )}
          {(record.district || record.state) && (
            <Detail
              icon={MapPin}
              label="Location"
              value={[record.police_station, record.district, record.state]
                .filter(Boolean)
                .join(", ")}
            />
          )}
          {record.amount_involved && (
            <Detail
              icon={IndianRupee}
              label="Amount Involved"
              value={formatCurrency(record.amount_involved)}
            />
          )}
          {record.legal_sections && record.legal_sections.length > 0 && (
            <Detail
              icon={Scale}
              label="Legal Sections"
              value={record.legal_sections.join(", ")}
            />
          )}
        </div>

        {/* Modus Operandi */}
        {record.modus_operandi && (
          <div className="px-6 pb-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Modus Operandi</h3>
            <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-4 border border-gray-100">
              {record.modus_operandi}
            </p>
          </div>
        )}

        {/* Keywords */}
        {record.keywords && record.keywords.length > 0 && (
          <div className="px-6 pb-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Keywords</h3>
            <div className="flex flex-wrap gap-2">
              {record.keywords.map((kw) => (
                <span key={kw} className="px-2.5 py-1 bg-gray-100 text-gray-600 rounded-md text-sm">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Entities */}
        {record.entities && Object.keys(record.entities).length > 0 && (
          <div className="px-6 pb-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Entities</h3>
            <div className="grid sm:grid-cols-2 gap-3">
              {Object.entries(record.entities).map(([key, values]) =>
                Array.isArray(values) && values.length > 0 ? (
                  <div key={key} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                    <p className="text-xs font-semibold text-gray-500 capitalize mb-1">
                      {key.replace(/_/g, " ")}
                    </p>
                    <p className="text-sm text-gray-700">{values.join(", ")}</p>
                  </div>
                ) : null
              )}
            </div>
          </div>
        )}

        {/* Redacted text */}
        {record.redacted_text && (
          <div className="px-6 pb-6">
            <details className="group">
              <summary className="cursor-pointer flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-gray-900 select-none">
                <FileText className="h-4 w-4" />
                View Redacted Document Text
              </summary>
              <pre className="mt-3 text-xs text-gray-600 bg-gray-50 rounded-lg p-4 border border-gray-100 whitespace-pre-wrap font-mono max-h-96 overflow-y-auto">
                {record.redacted_text}
              </pre>
            </details>
          </div>
        )}

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 text-xs text-gray-400">
          Record ID: {record.id} · Added {formatDate(record.created_at)} ·
          All personal information has been automatically redacted.
        </div>
      </div>
    </div>
  );
}

function Detail({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex gap-3">
      <Icon className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
      <div>
        <p className="text-xs text-gray-500 font-medium mb-0.5">{label}</p>
        <p className="text-sm text-gray-900">{value}</p>
      </div>
    </div>
  );
}
