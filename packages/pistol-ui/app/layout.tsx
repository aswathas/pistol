import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "pistol — Indian stocks, ask anything",
  description: "Free AI agent for the Indian stock market. 53 tools. NSE/BSE data, technicals, fundamentals, screeners, backtests.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://rsms.me/" />
        <link rel="stylesheet" href="https://rsms.me/inter/inter.css" />
        <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" async />
      </head>
      <body className="min-h-screen bg-bg text-ink antialiased">{children}</body>
    </html>
  );
}
