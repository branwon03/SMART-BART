"use client";

import { ReportProvider } from "../../context/ReportContext";

export default function IncidentFlowLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <ReportProvider>{children}</ReportProvider>;
}
