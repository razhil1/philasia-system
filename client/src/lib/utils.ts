import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number | string) {
  return `₱${parseFloat(value as string || "0").toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatDate(date: string | Date | null | undefined) {
  if (!date) return "—";
  return new Date(date).toLocaleDateString("en-PH", { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(date: string | Date | null | undefined) {
  if (!date) return "—";
  return new Date(date).toLocaleString("en-PH", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export const MOVEMENT_TYPES: Record<string, { label: string; color: string }> = {
  delivery:    { label: "Delivery",    color: "bg-emerald-100 text-emerald-700" },
  transfer:    { label: "Transfer",    color: "bg-blue-100 text-blue-700" },
  pullout:     { label: "Pullout",     color: "bg-cyan-100 text-cyan-700" },
  adjustment:  { label: "Adjustment", color: "bg-amber-100 text-amber-700" },
  return:      { label: "Return",      color: "bg-slate-100 text-slate-700" },
  consumption: { label: "Consumption",color: "bg-red-100 text-red-700" },
  scrap:       { label: "Scrap",       color: "bg-gray-100 text-gray-700" },
};

export const ROLES: Record<string, string> = {
  admin: "Administrator", project_manager: "Project Manager",
  delivery_guy: "Delivery", accounting: "Accounting",
  finance_manager: "Finance Manager", stock_clerk: "Stock Clerk", viewer: "Viewer",
};

export const STATUS_COLORS: Record<string, string> = {
  pending:   "bg-amber-100 text-amber-700",
  approved:  "bg-blue-100 text-blue-700",
  fulfilled: "bg-emerald-100 text-emerald-700",
  rejected:  "bg-red-100 text-red-700",
  partial:   "bg-purple-100 text-purple-700",
  active:    "bg-emerald-100 text-emerald-700",
  planned:   "bg-slate-100 text-slate-600",
  on_hold:   "bg-amber-100 text-amber-700",
  completed: "bg-blue-100 text-blue-700",
  available:    "bg-emerald-100 text-emerald-700",
  deployed:     "bg-blue-100 text-blue-700",
  maintenance:  "bg-amber-100 text-amber-700",
  scrapped:     "bg-red-100 text-red-700",
};
