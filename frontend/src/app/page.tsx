"use client";

import { useState } from "react";
import { analyze } from "@/lib/api";

export default function Home() {
  const [title, setTitle] = useState("");
  const [price, setPrice] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function handleAnalyze() {
    setLoading(true);

    try {
      const data = await analyze(title, Number(price));
      setResult(data);
    } catch (err) {
      console.error(err);
      alert("Failed to analyze");
    }

    setLoading(false);
  }

  return (
    <main className="min-h-screen bg-zinc-950 text-white flex justify-center p-10">
      <div className="w-full max-w-2xl">

        <h1 className="text-5xl font-bold mb-2">
          FlipLens AI
        </h1>

        <p className="text-zinc-400 mb-10">
          AI Marketplace Valuation
        </p>

        <input
          className="w-full p-4 rounded-xl bg-zinc-900 border border-zinc-700 mb-4"
          placeholder="Product title..."
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />

        <input
          className="w-full p-4 rounded-xl bg-zinc-900 border border-zinc-700 mb-4"
          placeholder="Asking price"
          type="number"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />

        <button
          onClick={handleAnalyze}
          className="w-full bg-white text-black rounded-xl p-4 font-semibold"
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>

        {result && (
          <div className="mt-8 rounded-xl bg-zinc-900 p-6 space-y-3">
            <div>💰 Market Price: £{result.estimated_market_price}</div>
            <div>📈 Profit: £{result.expected_profit}</div>
            <div>📊 ROI: {result.roi}%</div>
            <div>⭐ Score: {result.score}</div>
            <div>✅ {result.recommendation}</div>
          </div>
        )}

      </div>
    </main>
  );
}