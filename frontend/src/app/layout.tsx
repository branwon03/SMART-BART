import type { Metadata } from "next";
import "./globals.css";
import { ReportProvider } from "../context/ReportContext";

export const metadata: Metadata = {
  title: "BART Incident Reporting",
  description: "Report incidents on the Bay Area Transit System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-gray-200 text-black min-h-screen">
        <ReportProvider>
          {children}
        </ReportProvider>
      </body>
    </html>
  );
}