"use client";

import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid, Legend,
} from "recharts";
import { getAnalytics, AnalyticsSummary } from "@/lib/api";
import { CATEGORY_COLORS, formatCurrency } from "@/lib/utils";
import { TrendingUp, AlertCircle, MapPin, IndianRupee } from "lucide-react";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getAnalytics()
      .then(setData)
      .catch(() => setError("Failed to load analytics. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center text-gray-500">
        Loading analytics…
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-red-700 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-semibold">Could not load analytics</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Crime Analytics</h1>
      <p className="text-gray-500 mb-8">Aggregate statistics from published crime records</p>

      {/* Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <StatCard
          label="Total Records"
          value={data.total_records.toLocaleString()}
          icon={<AlertCircle className="h-5 w-5 text-red-600" />}
          bg="bg-red-50"
        />
        <StatCard
          label="Last 30 Days"
          value={data.recent_count_30d.toLocaleString()}
          icon={<TrendingUp className="h-5 w-5 text-orange-600" />}
          bg="bg-orange-50"
        />
        <StatCard
          label="States Covered"
          value={data.by_state.length.toString()}
          icon={<MapPin className="h-5 w-5 text-blue-600" />}
          bg="bg-blue-50"
        />
        <StatCard
          label="Total Amount"
          value={formatCurrency(data.total_amount_involved ?? 0)}
          icon={<IndianRupee className="h-5 w-5 text-green-600" />}
          bg="bg-green-50"
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-8 mb-8">
        {/* Category distribution */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-lg text-gray-900 mb-5">By Crime Category</h2>
          {data.by_category.length === 0 ? (
            <p className="text-gray-400 text-sm py-8 text-center">No data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.by_category} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis
                  type="category"
                  dataKey="category"
                  width={130}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {data.by_category.map((entry) => (
                    <Cell
                      key={entry.category}
                      fill={CATEGORY_COLORS[entry.category] || "#6b7280"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Pie chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-lg text-gray-900 mb-5">Category Share</h2>
          {data.by_category.length === 0 ? (
            <p className="text-gray-400 text-sm py-8 text-center">No data yet</p>
          ) : (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="60%" height={240}>
                <PieChart>
                  <Pie
                    data={data.by_category}
                    dataKey="count"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                  >
                    {data.by_category.map((entry) => (
                      <Cell
                        key={entry.category}
                        fill={CATEGORY_COLORS[entry.category] || "#6b7280"}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2">
                {data.by_category.slice(0, 8).map((item) => (
                  <div key={item.category} className="flex items-center gap-2 text-xs">
                    <span
                      className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: CATEGORY_COLORS[item.category] || "#6b7280" }}
                    />
                    <span className="text-gray-600 truncate">{item.category}</span>
                    <span className="ml-auto font-semibold text-gray-800">{item.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Monthly trend */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <h2 className="font-semibold text-lg text-gray-900 mb-5">Monthly Trend (Last 12 Months)</h2>
        {data.by_month.length === 0 ? (
          <p className="text-gray-400 text-sm py-8 text-center">No trend data yet</p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={data.by_month}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#dc2626"
                strokeWidth={2}
                dot={{ fill: "#dc2626", r: 4 }}
                name="Cases"
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Top states */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="font-semibold text-lg text-gray-900 mb-5">Top States by Crime Records</h2>
        {data.by_state.length === 0 ? (
          <p className="text-gray-400 text-sm py-8 text-center">No data yet</p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.by_state}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="state" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#dc2626" radius={[4, 4, 0, 0]} name="Records" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  bg,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  bg: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className={`w-10 h-10 ${bg} rounded-lg flex items-center justify-center mb-3`}>
        {icon}
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-sm text-gray-500 mt-0.5">{label}</p>
    </div>
  );
}
