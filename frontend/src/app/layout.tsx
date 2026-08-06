import type { Metadata } from "next";
import { Inter, EB_Garamond } from "next/font/google";
import "./globals.css";
import { AuthProvider }       from "./components/AuthContext";
import { RBACProvider }       from "./components/RBACContext";
import { NavigationBar }      from "./components/NavigationBar";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const garamond = EB_Garamond({
  subsets: ["latin"],
  weight: ["400", "500"],
  style: ["normal", "italic"],
  variable: "--font-garamond",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Sententia.ai — Cross-Border Fund Structuring",
  description:
    "AI-powered cross-border investment structure generation and compliance validation for multi-jurisdiction FDI scenarios.",
  keywords: ["FDI", "fund structuring", "compliance", "cross-border investment", "SPV", "tax treaty"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${garamond.variable} h-full`}>
      <body className="min-h-full antialiased">
        {/*
          AuthProvider must wrap RBACProvider so RBACContext can read
          the real role from the Supabase profile (FR-7.1).
        */}
        <AuthProvider>
          <RBACProvider>
            <NavigationBar />
            {children}
          </RBACProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
