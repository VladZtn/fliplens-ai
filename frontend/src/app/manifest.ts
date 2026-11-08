import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "FlipLens AI",
    short_name: "FlipLens",
    description: "AI-assisted marketplace deal analysis, pricing and risk checks.",
    start_url: "/",
    display: "standalone",
    background_color: "#f4f4ef",
    theme_color: "#2d2e2b",
    orientation: "portrait-primary",
    icons: [
      {
        src: "/icons/icon-192.png",
        sizes: "192x192",
        type: "image/png",
      },
      {
        src: "/icons/icon-512.png",
        sizes: "512x512",
        type: "image/png",
      },
      {
        src: "/icons/icon-512-maskable.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
