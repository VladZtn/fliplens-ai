"use client";

import { useState, type CSSProperties, type ReactNode } from "react";
import type { DealAnalysis } from "@/lib/api";

const NEUTRAL_IDENTITY_FLAGS = new Set([
  "product_identity_unverified",
  "identity_not_verified",
  "exact_model_not_verified",
]);

const PHONE_CHECKS = [
  "Settings → General → About matches the model",
  "IMEI is clean: not blocked, lost or on finance",
  "Battery Health is shown and acceptable",
  "Activation Lock / Find My is switched off",
  "Face ID, cameras, speakers and charging work",
];

const GENERAL_CHECKS = [
  "Serial number or model label matches the listing",
  "Tested in person before paying",
  "No damage the photos didn't show",
  "Paying with a protected method, not bank transfer",
];

function money(value: number, currency = "GBP") {
  return new Intl.NumberFormat("en-GB", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
}

function signedMoney(value: number, currency = "GBP") {
  return value < 0 ? `−${money(Math.abs(value), currency)}` : money(value, currency);
}

function signedPercent(value: number) {
  return value < 0 ? `−${Math.abs(value).toFixed(1)}%` : `${value.toFixed(1)}%`;
}

function normalizeFlag(flag: string) {
  return flag.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

function sentenceCase(value: string) {
  const text = value.replaceAll("_", " ").trim().toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function verdict(recommendation: string): { label: string; tone: "good" | "maybe" | "bad" } {
  const value = recommendation.trim().toUpperCase();
  if (value === "BUY" || value.includes("STRONG") || value.includes("EXCEPTIONAL")) return { label: "Buy", tone: "good" };
  if (value === "NEGOTIATE") return { label: "Haggle", tone: "maybe" };
  if (value === "VERIFY" || value === "VERIFY_DETAILS" || value === "CONSIDER") return { label: "Check", tone: "maybe" };
  return { label: "Pass", tone: "bad" };
}

function isPhone(result: DealAnalysis) {
  const text = [result.listing.category, result.listing.product_name, result.listing.model].join(" ").toLowerCase();
  return /phone|iphone|galaxy|pixel|smartphone/.test(text);
}

function Chevron() {
  return (
    <svg className="chevron" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
      <path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Fold({ label, showText, children, quiet = false }: { label: ReactNode; showText: string; children: ReactNode; quiet?: boolean }) {
  return (
    <details className={`fold ${quiet ? "fold-quiet" : ""}`}>
      <summary>
        <span className="fold-label">{label}</span>
        <span className="toggle-button">
          <span className="when-closed">{showText}</span>
          <span className="when-open">Hide</span>
          <Chevron />
        </span>
      </summary>
      <div className="fold-body">{children}</div>
    </details>
  );
}

type Props = {
  result: DealAnalysis;
  onReset?: () => void;
  example?: boolean;
};

export default function ResultView({ result, onReset, example = false }: Props) {
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState(false);

  const currency = result.listing.currency ?? "GBP";
  const { label, tone } = verdict(result.recommendation);
  const market = result.market_pricing;

  const flags = result.listing.risk_flags.map((flag) => ({ original: flag, key: normalizeFlag(flag) }));
  const riskFlags = flags.filter(({ key }) => !NEUTRAL_IDENTITY_FLAGS.has(key));
  const modelUnconfirmed = flags.some(({ key }) => NEUTRAL_IDENTITY_FLAGS.has(key));
  const checks = isPhone(result) ? PHONE_CHECKS : GENERAL_CHECKS;

  const meta = [result.listing.brand, result.listing.variant, result.listing.condition].filter(Boolean).join(", ");
  const fees = result.selling_fees ?? result.fees?.total ?? 0;
  const offer = result.next_action.suggested_offer;
  const scoreStyle = { "--score": `${result.flip_score * 3.6}deg` } as CSSProperties;

  function toggleCheck(item: string) {
    setChecked((current) => {
      const next = new Set(current);
      if (next.has(item)) next.delete(item);
      else next.add(item);
      return next;
    });
  }

  async function copyOfferMessage() {
    if (offer === null) return;
    const text = `Hi, is the ${result.listing.product_name} still available? Would you take ${money(offer, currency)}? I can collect quickly.`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2200);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className={`report ${example ? "report-example" : ""}`} id={example ? undefined : "analysis-result"} aria-label={example ? "Example report" : "Deal report"}>
      <header className="report-head">
        <div className={`swing-tag ${tone}`} aria-label={`Verdict: ${label}`}>
          <span>{label}</span>
        </div>
        <div className="report-title">
          <h2>{result.listing.product_name}</h2>
          {meta && <p>{meta}</p>}
        </div>
      </header>

      <div className="figures">
        <div className="figure">
          <strong className={result.expected_profit < 0 ? "loss" : "gain"}>{signedMoney(result.expected_profit, currency)}</strong>
          <span>profit after fees</span>
        </div>
        <div className="figure">
          <strong className={result.roi < 0 ? "loss" : undefined}>{signedPercent(result.roi)}</strong>
          <span>return on money spent</span>
        </div>
        <div className="figure">
          <strong className="score"><i className="score-dial" style={scoreStyle} aria-hidden="true" />{result.flip_score}</strong>
          <span>FlipScore out of 100</span>
        </div>
      </div>

      <div className="deal-row">
        <div className={`offer-box ${tone}`}>
          {offer !== null ? (
            <>
              <span className="offer-label">Offer up to</span>
              <strong className="offer-amount">{money(offer, currency)}</strong>
            </>
          ) : (
            <strong className="offer-headline">{result.next_action.title}</strong>
          )}
          <p>{result.next_action.message}</p>
          {offer !== null && !example && (
            <button type="button" className="button button-ink" onClick={copyOfferMessage}>
              {copied ? "Copied" : "Copy offer message"}
            </button>
          )}
        </div>

        <dl className="receipt" aria-label="How the profit is worked out">
          <div><dt>Sell for</dt><dd>{money(result.expected_resale_price, currency)}</dd></div>
          <div><dt>{result.fees ? `${result.fees.platform_label.split(" (")[0]} fees` : "Selling fees"}</dt><dd>−{money(fees, currency)}</dd></div>
          {result.extra_costs > 0 && <div><dt>Postage &amp; repairs</dt><dd>−{money(result.extra_costs, currency)}</dd></div>}
          <div><dt>You pay</dt><dd>−{money(result.purchase_price, currency)}</dd></div>
          <div className={`receipt-total ${result.expected_profit < 0 ? "loss" : "gain"}`}><dt>Profit</dt><dd>{signedMoney(result.expected_profit, currency)}</dd></div>
        </dl>
      </div>

      {result.pricing_warning && <p className="note warn" role="status">{result.pricing_warning}</p>}

      {market ? (
        <Fold
          showText={market.comparables?.length ? `Show ${market.comparables.length} listings` : "Show details"}
          label={market.source === "ebay_active_listings"
            ? <>Priced from <b>{market.comparable_count}</b> eBay listings, {money(market.market_low, currency)}–{money(market.market_high, currency)}</>
            : <>Test prices only. eBay is not connected</>}
        >
          {market.comparables && market.comparables.length > 0 && (
            <ul className="comps">
              {market.comparables.map((comp, index) => (
                <li key={comp.source_id ?? `${comp.title}-${index}`}>
                  {comp.item_url
                    ? <a href={comp.item_url} target="_blank" rel="noopener noreferrer">{comp.title}<span className="visually-hidden"> (opens eBay)</span></a>
                    : <span>{comp.title}</span>}
                  <b>{money(comp.price, comp.currency || currency)}</b>
                </li>
              ))}
            </ul>
          )}
          <p className="small-print">These are asking prices. Items often sell for less, so check sold listings too.</p>
        </Fold>
      ) : (
        <p className="note">Resale price is your own estimate and was not checked against eBay.</p>
      )}

      {!example && <section className="checks" aria-label="Before you buy">
        <div className="checks-head">
          <h3>Before you buy</h3>
          <span className={checked.size === checks.length ? "progress done" : "progress"}>{checked.size} of {checks.length} checked</span>
        </div>
        {(riskFlags.length > 0 || modelUnconfirmed) && (
          <ul className="flags">
            {modelUnconfirmed && <li className="flag-soft">Model not confirmed from the photo</li>}
            {riskFlags.map(({ original, key }) => <li key={key}>{sentenceCase(original)}</li>)}
          </ul>
        )}
        <ul className="checklist">
          {checks.map((item) => (
            <li key={item}>
              <label className={checked.has(item) ? "is-checked" : undefined}>
                <input type="checkbox" checked={checked.has(item)} onChange={() => toggleCheck(item)} />
                <span>{item}</span>
              </label>
            </li>
          ))}
        </ul>
      </section>}

      {!example && <Fold quiet showText="Show details" label="How this was worked out">
        <p className="fold-text">{result.listing.summary}</p>
        <dl className="breakdown">
          <div><dt>Profit points</dt><dd>+{result.score_roi_points + result.score_margin_points}</dd></div>
          <div><dt>AI confidence ({Math.round(result.listing.confidence * 100)}%)</dt><dd>+{result.score_confidence_points}</dd></div>
          <div><dt>Risk penalty</dt><dd>{result.score_risk_points}</dd></div>
          {result.fees && <div><dt>Fee rule</dt><dd>{result.fees.rule}</dd></div>}
          {market && <div><dt>Pricing confidence</dt><dd>{Math.round(market.pricing_confidence * 100)}%</dd></div>}
          {result.listing.included_items.length > 0 && <div><dt>Included</dt><dd>{result.listing.included_items.join(", ")}</dd></div>}
        </dl>
        <p className="small-print">{result.disclaimer}</p>
      </Fold>}

      {!example && onReset && (
        <div className="report-actions">
          <button className="button button-outline" type="button" onClick={onReset}>Check another listing</button>
        </div>
      )}
    </section>
  );
}
