"use client";

import React, { createContext, useCallback, useContext, useState, ReactNode } from 'react';

interface ReportContextType {
  images: string[];
  setImages: React.Dispatch<React.SetStateAction<string[]>>;
  rawFiles: File[];
  setRawFiles: React.Dispatch<React.SetStateAction<File[]>>;
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
  clearSubmission: () => void;
}

const ReportContext = createContext<ReportContextType | undefined>(undefined);

export function ReportProvider({ children }: { children: ReactNode }) {
  const [images, setImages] = useState<string[]>([]);
  const [rawFiles, setRawFiles] = useState<File[]>([]);
  const [contextText, setContextText] = useState("");
  const [location, setLocation] = useState("");
  const [priority, setPriority] = useState("");
  const [fullName, setFullName] = useState("");
  const [contact, setContact] = useState("");

  const clearSubmission = useCallback(() => {
    setImages([]);
    setRawFiles([]);
    setContextText("");
    setLocation("");
    setPriority("");
    setFullName("");
    setContact("");
  }, []);

  return (
    <ReportContext.Provider value={{ 
      images, setImages,
      rawFiles, setRawFiles,
      contextText, setContextText,
      location, setLocation,
      priority, setPriority, 
      fullName, setFullName, 
      contact, setContact,
      clearSubmission,
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
