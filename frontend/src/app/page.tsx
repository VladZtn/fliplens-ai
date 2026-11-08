"use client";

import { ChangeEvent, DragEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import ResultView from "@/components/ResultView";
import { exampleResult } from "@/components/exampleResult";
import { analyzeDeal, ApiError, DealAnalysis, fetchUsage, SELL_PLATFORMS, SellPlatform, UsageInfo } from "@/lib/api";

const MAX_FILE_SIZE = 8 * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

export default function Home() {
  const [title, setTitle] = useState("");
  const [purchasePrice, setPurchasePrice] = useState("");
  const [resalePrice, setResalePrice] = useState("");
  const [extraCosts, setExtraCosts] = useState("0");
  const [sellPlatform, setSellPlatform] = useState<SellPlatform>("ebay_business");
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const [limitReached, setLimitReached] = useState(false);
  const [description, setDescription] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [result, setResult] = useState<DealAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [needsResale, setNeedsResale] = useState(false);
  const resaleRef = useRef<HTMLInputElement>(null);

  const previewUrl = useMemo(() => (image ? URL.createObjectURL(image) : ""), [image]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => {
    let active = true;
    fetchUsage().then((value) => {
      if (!active || !value) return;
      setUsage(value);
      setLimitReached(!value.unlimited && value.remaining <= 0);
    });
    return () => {
      active = false;
    };
  }, []);

  function acceptFile(file?: File) {
    setError("");
    if (!file) return;
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError("Upload a JPEG, PNG or WebP image.");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError("The image must be smaller than 8 MB.");
      return;
    }
    setImage(file);
    setResult(null);
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    acceptFile(event.target.files?.[0]);
    event.target.value = "";
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    acceptFile(event.dataTransfer.files?.[0]);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNeedsResale(false);

    if (!image) {
      setError("Add a listing screenshot or product photo first.");
      return;
    }

    const purchase = Number(purchasePrice);
    const resale = resalePrice ? Number(resalePrice) : undefined;
    const costs = Number(extraCosts || 0);

    if (!title.trim() || purchase <= 0 || (resale !== undefined && resale <= 0) || costs < 0) {
      setError("Complete the title and price fields with valid values.");
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const data = await analyzeDeal({
        title: title.trim(),
        purchasePrice: purchase,
        expectedResalePrice: resale,
        extraCosts: costs,
        sellPlatform,
        description: description.trim(),
        image,
      });
      setResult(data);
      if (data.usage) {
        setUsage(data.usage);
        setLimitReached(!data.usage.unlimited && data.usage.remaining <= 0);
      }
      window.setTimeout(() => {
        document.getElementById("analysis-result")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 50);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 429) {
        setLimitReached(true);
        setUsage((current) => (current ? { ...current, remaining: 0 } : current));
      }
      const message = caught instanceof Error ? caught.message : "Analysis failed. Please try again.";
      setError(message);
      if (/resale (estimate|price)/i.test(message)) {
        setNeedsResale(true);
        window.setTimeout(() => resaleRef.current?.focus(), 50);
      }
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setResult(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="site-shell">
      <nav className="nav">
        <a className="brand" href="#top" aria-label="FlipLens home">
          <span className="brand-mark">F</span>
          <span>FlipLens</span>
        </a>
        {usage && !usage.unlimited && (
          <span className={`usage-pill ${limitReached ? "exhausted" : ""}`}>
            <b>{limitReached ? 0 : usage.remaining}</b> free {usage.remaining === 1 ? "check" : "checks"} left today
          </span>
        )}
      </nav>

      <div className={`app ${result || loading ? "has-result" : ""}`}>
        {!result && !loading && (
          <section className="intro" id="top">
            <h1>Know the deal before you buy.</h1>
            <p className="lede">Add a listing photo. FlipLens prices it against live eBay listings, takes off the fees and tells you what to offer.</p>
            <ol className="steps">
              <li><b>1</b>Photo or screenshot of the listing</li>
              <li><b>2</b>Live eBay prices, minus selling fees</li>
              <li><b>3</b>A verdict and a fair offer</li>
            </ol>
          </section>
        )}

        <form className="deal-form" onSubmit={onSubmit} noValidate>
          <label
            className={`drop-zone ${dragging ? "dragging" : ""} ${image ? "has-image" : ""}`}
            onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={onFileChange} />
            {image ? (
              <>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={previewUrl} alt="Selected listing preview" />
                <span className="button button-light image-change">Change photo</span>
              </>
            ) : (
              <span className="drop-empty">
                <span className="drop-icon" aria-hidden="true">
                  <svg width="22" height="22" viewBox="0 0 24 24"><path d="M12 16V4m0 0-4.5 4.5M12 4l4.5 4.5M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </span>
                <strong>Drop a listing photo</strong>
                <span className="button button-light">Choose file</span>
              </span>
            )}
          </label>

          <div className="form-grid">
            <label className="field field-wide">
              <span>What is it?</span>
              <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="iPhone 16 Pro 128GB" required />
            </label>
            <label className="field">
              <span>Asking price</span>
              <div className="money-input"><b>£</b><input type="number" min="0.01" step="0.01" inputMode="decimal" value={purchasePrice} onChange={(event) => setPurchasePrice(event.target.value)} placeholder="550" required /></div>
            </label>
            <label className={`field ${needsResale ? "needs-attention" : ""}`}>
              <span>Your resale price <em>optional</em></span>
              <div className="money-input"><b>£</b><input ref={resaleRef} type="number" min="0.01" step="0.01" inputMode="decimal" value={resalePrice} onChange={(event) => { setResalePrice(event.target.value); setNeedsResale(false); }} placeholder="From eBay" /></div>
            </label>
            <label className="field">
              <span>You will sell on</span>
              <select value={sellPlatform} onChange={(event) => setSellPlatform(event.target.value as SellPlatform)}>
                {SELL_PLATFORMS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label className="field">
              <span>Postage &amp; repairs</span>
              <div className="money-input"><b>£</b><input type="number" min="0" step="0.01" inputMode="decimal" value={extraCosts} onChange={(event) => setExtraCosts(event.target.value)} /></div>
            </label>
            <label className="field field-wide">
              <span>Listing description <em>optional, improves accuracy</em></span>
              <textarea rows={2} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Paste the seller’s text: storage, condition, what’s included" />
            </label>
          </div>

          {error && <div className="error-message" role="alert">{error}</div>}

          <button className="button button-primary" type="submit" disabled={loading || limitReached}>
            {loading ? <><span className="spinner" aria-hidden="true" /> Checking the deal…</> : "Check this deal"}
          </button>
          {limitReached && <p className="form-note">Free checks reset at midnight UTC.</p>}
        </form>

        <div className="main-pane">
          {loading && (
            <section className="loading-panel" aria-live="polite">
              <span className="scan-frame"><span /></span>
              <p>Reading the listing and pulling eBay prices…</p>
            </section>
          )}
          {result && <ResultView result={result} onReset={reset} />}
          {!result && !loading && (
            <div className="example" inert>
              <p className="example-label"><span>Example</span> This is what you get after a check</p>
              <ResultView result={exampleResult} example />
            </div>
          )}
        </div>
      </div>

      <footer className="footer"><span>FlipLens</span><p>Faster, safer resale decisions.</p></footer>
    </main>
  );
}
