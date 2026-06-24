import Link from "next/link";
import { MapPin, Calendar, Scale, IndianRupee, Tag } from "lucide-react";
import { CrimeRecord } from "@/lib/api";
import { formatCurrency, formatDate, CATEGORY_COLORS } from "@/lib/utils";

interface Props {
  record: CrimeRecord;
}

export default function CrimeCard({ record }: Props) {
  const color = CATEGORY_COLORS[record.crime_category || ""] || "#6b7280";

  return (
    <Link href={`/record/${record.id}`} className="block">
      <div className="bg-white rounded-lg border border-gray-200 p-5 hover:border-red-300 hover:shadow-sm transition-all">
        <div className="flex items-start justify-between gap-3 mb-3">
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold text-white"
            style={{ backgroundColor: color }}
          >
            <Tag className="h-3 w-3" />
            {record.crime_category || "Unknown"}
          </span>
          {record.fir_number && (
            <span className="text-xs text-gray-500 font-mono">FIR {record.fir_number}</span>
          )}
        </div>

        {record.summary && (
          <p className="text-sm text-gray-700 mb-3 line-clamp-3">{record.summary}</p>
        )}

        <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-gray-500">
          {(record.district || record.state) && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {[record.district, record.state].filter(Boolean).join(", ")}
            </span>
          )}
          {record.crime_date && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {formatDate(record.crime_date)}
            </span>
          )}
          {record.amount_involved && (
            <span className="flex items-center gap-1">
              <IndianRupee className="h-3 w-3" />
              {formatCurrency(record.amount_involved)}
            </span>
          )}
          {record.legal_sections && record.legal_sections.length > 0 && (
            <span className="flex items-center gap-1">
              <Scale className="h-3 w-3" />
              {record.legal_sections.slice(0, 3).join(", ")}
              {record.legal_sections.length > 3 && ` +${record.legal_sections.length - 3}`}
            </span>
          )}
        </div>

        {record.keywords && record.keywords.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {record.keywords.slice(0, 5).map((kw) => (
              <span
                key={kw}
                className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
              >
                {kw}
              </span>
            ))}
          </div>
        )}
      </div>
    </Link>
  );
}
