"use client";

import Link from 'next/link';
import { useReportContext } from '@/context/ReportContext';

export default function Review() {
  const { 
    images, setImages, 
    contextText, setContextText, 
    priority, setPriority,
    setFullName, setContact
  } = useReportContext();

  const handleClose = () => {
    setImages([]);
    setContextText("");
    setPriority("");
    setFullName("");
    setContact("");
  };

  return (
    <main className="min-h-screen flex flex-col items-center bg-white text-black max-w-md mx-auto border-x border-gray-100 shadow-2xl">
      <div className="w-full flex flex-col h-full items-center">
        
        <header className="w-full bg-black h-[72px] flex items-center px-4 gap-3 shrink-0">
          <div className="bg-white w-[52px] h-[36px] flex items-center justify-center p-1 rounded-sm">
            <img 
              src="/logo.png" 
              alt="BART" 
              className="w-full h-full object-contain" 
            />
          </div>
          <div className="text-white text-[15px] font-bold leading-tight tracking-wide">
            Bay Area<br />Rapid Transit
          </div>
        </header>

        <div className="flex flex-col items-center w-full pt-8 flex-1">
          
          <div className="w-[85%] aspect-[4/3] border-[3px] border-[#0099D8] bg-[#D1D5DB] flex items-center justify-center p-2 mb-6 relative overflow-hidden">
            {images.length > 0 ? (
              <img 
                src={images[0]} 
                alt="Submitted incident photo" 
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full bg-[#9CA3AF]" />
            )}
          </div>

          <div className="w-[85%] bg-[#D1D5DB] border-[2px] border-black p-5 flex flex-col mb-12">
            
            <p className="text-[15px] text-black mb-1.5 font-medium">Context:</p>
            <div className="w-full h-28 bg-white border-[2px] border-black mb-5 p-3 overflow-y-auto text-sm text-gray-800">
              {contextText || "No context provided."}
            </div>

            <p className="text-[15px] text-black mb-1.5 font-medium">Priority:</p>
            <div className="w-[60%] h-10 bg-white border-[2px] border-black p-2 flex items-center text-sm font-bold text-gray-800 capitalize">
              {priority || "None"}
            </div>

          </div>

          <Link href="/report" className="mb-12">
            <button 
              onClick={handleClose}
              className="bg-[#0099D8] text-white font-bold py-2 px-10 text-[16px] border-[2px] border-gray-300 shadow-[2px_2px_0_0_#9CA3AF] hover:bg-[#007AB8] hover:translate-y-[1px] hover:shadow-[1px_1px_0_0_#9CA3AF] transition-all"
            >
              Close
            </button>
          </Link>

        </div>
      </div>
    </main>
  );
}
