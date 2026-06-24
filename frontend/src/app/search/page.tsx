"use client";

import { useState, useCallback } from "react";
import { Search, Filter, X, ChevronLeft, ChevronRight } from "lucide-react";
import { searchRecords, CrimeRecord } from "@/lib/api";
import { CRIME_CATEGORIES, INDIA_STATES } from "@/lib/utils";
import CrimeCard from "@/components/CrimeCard";

const EMPTY: CrimeRecord[] = [];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({
    crime_category: "",
    state: "",
    date_from: "",
    date_to: "",
    min_amount: "",
    max_amount: "",
  });
  const [showFilters, setShowFilters] = useState(false);
  const [results, setResults] = useState<CrimeRecord[]>(EMPTY);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");

  const PAGE_SIZE = 20;

  const doSearch = useCallback(
    async (p = 1) => {
      if (!query.trim()) return;
      setLoading(true);
      setError("");
      try {
        const res = await searchRecords({
          q: query,
          ...Object.fromEntries(
            Object.entries(filters).filter(([, v]) => v !== "")
          ),
          page: p,
          page_size: PAGE_SIZE,
        });
        setResults(res.results);
        setTotal(res.total);
        setPage(p);
        setSearched(true);
      } catch (e) {
        setError("Search failed. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    [query, filters]
  );

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Search Crime Records</h1>

      {/* Search bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          doSearch(1);
        }}
        className="flex gap-2 mb-4"
      >
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='e.g. "cyber fraud UPI" or "vehicle theft Bengaluru"'
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 text-gray-900"
          />
        </div>
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-1.5 px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-700"
        >
          <Filter className="h-4 w-4" />
          Filters
        </button>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 font-semibold"
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {/* Filters panel */}
      {showFilters && (
        <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Crime Category</label>
            <select
              value={filters.crime_category}
              onChange={(e) => setFilters((f) => ({ ...f, crime_category: e.target.value }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900"
            >
              <option value="">All categories</option>
              {CRIME_CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
            <select
              value={filters.state}
              onChange={(e) => setFilters((f) => ({ ...f, state: e.target.value }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900"
            >
              <option value="">All states</option>
              {INDIA_STATES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date From</label>
            <input
              type="date"
              value={filters.date_from}
              onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date To</label>
            <input
              type="date"
              value={filters.date_to}
              onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Min Amount (₹)</label>
            <input
              type="number"
              value={filters.min_amount}
              onChange={(e) => setFilters((f) => ({ ...f, min_amount: e.target.value }))}
              placeholder="e.g. 100000"
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Amount (₹)</label>
            <input
              type="number"
              value={filters.max_amount}
              onChange={(e) => setFilters((f) => ({ ...f, max_amount: e.target.value }))}
              placeholder="e.g. 1000000"
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div className="sm:col-span-2 lg:col-span-3 flex justify-end">
            <button
              type="button"
              onClick={() =>
                setFilters({
                  crime_category: "",
                  state: "",
                  date_from: "",
                  date_to: "",
                  min_amount: "",
                  max_amount: "",
                })
              }
              className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
            >
              <X className="h-4 w-4" /> Clear filters
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-6 text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {searched && (
        <div>
          <p className="text-sm text-gray-500 mb-4">
            {total === 0
              ? "No records found."
              : `${total.toLocaleString()} record${total !== 1 ? "s" : ""} found`}
          </p>

          <div className="grid gap-4">
            {results.map((r) => (
              <CrimeCard key={r.id} record={r} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 mt-8">
              <button
                onClick={() => doSearch(page - 1)}
                disabled={page <= 1}
                className="p-2 rounded-md border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm text-gray-600">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => doSearch(page + 1)}
                disabled={page >= totalPages}
                className="p-2 rounded-md border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      )}

      {!searched && (
        <div className="text-center py-16 text-gray-400">
          <Search className="h-12 w-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">Enter a search query to find crime records</p>
          <p className="text-sm mt-1">Try: "cyber fraud", "vehicle theft", "robbery Delhi"</p>
        </div>
      )}
    </div>
  );
}
