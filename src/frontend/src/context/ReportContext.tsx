"use client";

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface ReportContextType {
  images: string[];
  setImages: React.Dispatch<React.SetStateAction<string[]>>;
  contextText: string;
  setContextText: React.Dispatch<React.SetStateAction<string>>;
  location: string;
  setLocation: React.Dispatch<React.SetStateAction<string>>;
  priority: string;
  setPriority: React.Dispatch<React.SetStateAction<string>>;
  fullName: string;
  setFullName: React.Dispatch<React.SetStateAction<string>>;
  contact: string;
  setContact: React.Dispatch<React.SetStateAction<string>>;
}

const ReportContext = createContext<ReportContextType | undefined>(undefined);

export function ReportProvider({ children }: { children: ReactNode }) {
  const [images, setImages] = useState<string[]>([]);
  const [contextText, setContextText] = useState("");
  const [location, setLocation] = useState("");
  const [priority, setPriority] = useState("");
  const [fullName, setFullName] = useState("");
  const [contact, setContact] = useState("");

  return (
    <ReportContext.Provider value={{ 
      images, setImages, 
      contextText, setContextText,
      location, setLocation,
      priority, setPriority, 
      fullName, setFullName, 
      contact, setContact 
    }}>
      {children}
    </ReportContext.Provider>
  );
}

export function useReportContext() {
  const context = useContext(ReportContext);
  if (!context) {
    throw new Error('useReportContext must be used within a ReportProvider');
  }
  return context;
}
