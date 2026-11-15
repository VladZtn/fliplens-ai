// Links that open the same item on eBay (sold only) and CeX in the user's own
// browser. Nothing is fetched or stored by FlipLens: the user checks for
// themselves, which keeps us within both sites' terms.

const EBAY_UK_SEARCH = "https://www.ebay.co.uk/sch/i.html";
const CEX_UK_SEARCH = "https://uk.webuy.com/search";

// eBay's condition codes for search filters.
const EBAY_CONDITION: Record<string, string> = { new: "1000", used: "3000" };

export function checkQuery(base: string, variant?: string | null): string {
  const query = base.trim().replace(/\s+/g, " ");
  const extra = (variant ?? "").trim();
  if (!extra || query.toLowerCase().replace(/\s/g, "").includes(extra.toLowerCase().replace(/\s/g, ""))) {
    return query;
  }
  return `${query} ${extra}`;
}

export function ebaySoldUrl(query: string, condition?: string | null): string {
  const params = new URLSearchParams({
    _nkw: query,
    LH_Sold: "1",
    LH_Complete: "1",
    LH_PrefLoc: "1",
  });
  const code = condition ? EBAY_CONDITION[condition.toLowerCase()] : undefined;
  if (code) params.set("LH_ItemCondition", code);
  return `${EBAY_UK_SEARCH}?${params.toString()}`;
}

export function cexSearchUrl(query: string): string {
  return `${CEX_UK_SEARCH}?${new URLSearchParams({ stext: query }).toString()}`;
}
