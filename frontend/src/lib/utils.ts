import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount?: number | null): string {
  if (amount == null) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

export const CRIME_CATEGORIES = [
  "Cyber Fraud",
  "Vehicle Theft",
  "Robbery",
  "Murder",
  "Assault",
  "Kidnapping",
  "Drug Trafficking",
  "Property Crime",
  "Sexual Offence",
  "Burglary",
  "Cheating",
  "Other",
];

export const INDIA_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
  "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
  "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
  "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
  "Delhi", "Jammu and Kashmir", "Ladakh",
];

export const CATEGORY_COLORS: Record<string, string> = {
  "Cyber Fraud": "#3b82f6",
  "Vehicle Theft": "#f59e0b",
  "Robbery": "#ef4444",
  "Murder": "#7c3aed",
  "Assault": "#f97316",
  "Kidnapping": "#ec4899",
  "Drug Trafficking": "#84cc16",
  "Property Crime": "#06b6d4",
  "Sexual Offence": "#8b5cf6",
  "Burglary": "#d97706",
  "Cheating": "#10b981",
  "Other": "#6b7280",
};
