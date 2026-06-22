import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Portfolio Generator | CV to Portfolio",
  description:
    "Transform your CV into a stunning animated portfolio website in seconds. Powered by AI.",
  keywords: ["portfolio", "CV", "resume", "AI", "generator"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-[#050505] text-white antialiased">{children}</body>
    </html>
  );
}
