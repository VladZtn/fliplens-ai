export type ListingAnalysis = {
  product_name: string;
  brand: string | null;
  model: string | null;
  variant?: string | null;
  category: string | null;
  condition: string | null;
  currency: string | null;
  asking_price: number | null;
  included_items: string[];
  detected_issues: string[];
  risk_flags: string[];
  confidence: number;
  summary: string;
};

export type MarketComparable = {
  title: string;
  price: number;
  currency: string;
  condition: string | null;
  item_url: string | null;
  source_id: string | null;
  identity_score: number;
};

export type MarketPricing = {
  query: string;
  estimated_market_price: number;
  market_low: number;
  market_high: number;
  comparable_count: number;
  raw_comparable_count: number;
  pricing_confidence: number;
  safe_buy_price: number;
  source: string;
  data_kind: string;
  condition_filter?: string | null;
  comparables?: MarketComparable[];
};

export type FeeBreakdown = {
  platform: string;
  platform_label: string;
  total: number;
  final_value_fee: number;
  per_order_fee: number;
  vat: number;
  rule: string;
  note: string;
};

export type UsageInfo = {
  limit: number;
  remaining: number;
  unlimited: boolean;
};

export type SellPlatform = "ebay_business" | "ebay_private" | "vinted" | "facebook_local" | "none";

export const SELL_PLATFORMS: { value: SellPlatform; label: string; hint: string }[] = [
  { value: "ebay_business", label: "eBay, business", hint: "6.9–12.9% + 40p per order + VAT on fees" },
  { value: "ebay_private", label: "eBay, private", hint: "No final value fee in most categories" },
  { value: "vinted", label: "Vinted", hint: "No seller fee" },
  { value: "facebook_local", label: "Facebook, local", hint: "No fee for local collection" },
  { value: "none", label: "No fees", hint: "Only your own costs" },
];

export type NextAction = {
  code: string;
  title: string;
  message: string;
  suggested_offer: number | null;
};

export type DealAnalysis = {
  listing: ListingAnalysis;
  purchase_price: number;
  expected_resale_price: number;
  market_pricing: MarketPricing | null;
  next_action: NextAction;
  extra_costs: number;
  selling_fees?: number;
  fees?: FeeBreakdown | null;
  usage?: UsageInfo | null;
  expected_profit: number;
  roi: number;
  margin: number;
  flip_score: number;
  recommendation: string;
  risk_penalty: number;
  risk_level: string;
  critical_risk: boolean;
  score_roi_points: number;
  score_margin_points: number;
  score_confidence_points: number;
  score_risk_points: number;
  base_deal_score: number;
  decision_reason: string;
  pricing_source: string;
  pricing_warning?: string | null;
  disclaimer: string;
};

export type AnalyzeDealInput = {
  title: string;
  purchasePrice: number;
  expectedResalePrice?: number;
  extraCosts: number;
  sellPlatform: SellPlatform;
  description?: string;
  image: File;
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const MAX_IMAGE_SIDE = 2000;
const RESIZE_ABOVE_BYTES = 600 * 1024;

// Phone photos are several megabytes. Shrinking them in the browser makes the
// upload and the AI step faster, and 2000px keeps listing text readable.
async function shrinkImage(file: File): Promise<File> {
  if (file.size <= RESIZE_ABOVE_BYTES) return file;
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, MAX_IMAGE_SIDE / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    const context = canvas.getContext("2d");
    if (!context) return file;
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    if (!blob || blob.size >= file.size) return file;
    return new File([blob], file.name.replace(/\.\w+$/, "") + ".jpg", { type: "image/jpeg" });
  } catch {
    return file;
  }
}

export async function analyzeDeal(input: AnalyzeDealInput): Promise<DealAnalysis> {
  const form = new FormData();
  form.append("title", input.title);
  form.append("purchase_price", String(input.purchasePrice));
  if (input.expectedResalePrice) form.append("expected_resale_price", String(input.expectedResalePrice));
  form.append("extra_costs", String(input.extraCosts));
  form.append("sell_platform", input.sellPlatform);
  form.append("description", input.description ?? "");
  form.append("image", await shrinkImage(input.image));

  const response = await fetch(`${API_URL}/api/v1/deals/analyze-image`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    let message = "Analysis failed. Please try again.";
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") message = payload.detail;
    } catch {
      // Keep the user-friendly fallback when the server returns non-JSON.
    }
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<DealAnalysis>;
}

export async function fetchUsage(): Promise<UsageInfo | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/deals/usage`);
    if (!response.ok) return null;
    return (await response.json()) as UsageInfo;
  } catch {
    return null;
  }
}
