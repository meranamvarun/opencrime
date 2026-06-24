import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1`
  : "/api/v1";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

export interface CrimeRecord {
  id: string;
  crime_category?: string;
  crime_date?: string;
  fir_number?: string;
  police_station?: string;
  district?: string;
  state?: string;
  summary?: string;
  keywords?: string[];
  legal_sections?: string[];
  amount_involved?: number;
  modus_operandi?: string;
  redacted_text?: string;
  entities?: Record<string, string[]>;
  processing_status: string;
  created_at: string;
}

export interface SearchResult {
  total: number;
  page: number;
  page_size: number;
  results: CrimeRecord[];
}

export interface AnalyticsSummary {
  total_records: number;
  by_category: { category: string; count: number }[];
  by_state: { state: string; count: number }[];
  by_month: { month: string; count: number }[];
  recent_count_30d: number;
  total_amount_involved?: number;
}

export async function searchRecords(params: {
  q: string;
  crime_category?: string;
  state?: string;
  district?: string;
  date_from?: string;
  date_to?: string;
  min_amount?: number;
  max_amount?: number;
  page?: number;
  page_size?: number;
}): Promise<SearchResult> {
  const { data } = await api.get("/search", { params });
  return data;
}

export async function getAnalytics(state?: string): Promise<AnalyticsSummary> {
  const { data } = await api.get("/analytics/summary", {
    params: state ? { state } : {},
  });
  return data;
}

export async function listRecords(params?: {
  page?: number;
  page_size?: number;
  state?: string;
  crime_category?: string;
}): Promise<SearchResult> {
  const { data } = await api.get("/analytics/records", { params });
  return data;
}

export async function getRecord(id: string): Promise<CrimeRecord> {
  const { data } = await api.get(`/analytics/records/${id}`);
  return data;
}

export async function uploadDocument(file: File): Promise<{ id: string; status: string }> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getDocumentStatus(
  documentId: string
): Promise<{ status: string; crime_record_id?: string }> {
  const { data } = await api.get(`/documents/${documentId}`);
  return data;
}

export async function getMapData(state?: string): Promise<{
  points: { id: string; category: string; district: string; state: string; lat: number; lng: number; date?: string }[];
}> {
  const { data } = await api.get("/analytics/map", {
    params: state ? { state } : {},
  });
  return data;
}
