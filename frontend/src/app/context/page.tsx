"use client";

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { useReportContext } from '@/src/context/ReportContext';

export default function UserContext() {
  const router = useRouter();
  const { 
    images, 
    contextText, setContextText,
    priority, setPriority,
    fullName, setFullName,
    contact, setContact
  } = useReportContext();

  const handleSubmit = () => {
    // Check if the required text fields are empty
    if (!contextText.trim() || !fullName.trim() || !contact.trim() || !priority.trim()) {
      alert("Please provide the incident context, priority, your full name, and contact information before submitting.");
      return;
    }

    // If all validation passes, navigate to the confirmation page
    router.push('/confirmation');
  };

  return (
    <main className="min-h-screen flex flex-col items-center bg-white text-black max-w-md mx-auto border-x border-gray-100 shadow-2xl">
      <div className="w-full flex flex-col h-full">
        
        <header className="w-full bg-black h-[72px] flex items-center px-4 gap-3 shrink-0">
          <div className="bg-white w-[52px] h-[36px] flex items-center justify-center p-1 rounded-sm">
            <img src="/bart-logo.png" alt="BART" className="w-full h-full object-contain" />
          </div>
          <div className="text-white text-[15px] font-bold leading-tight tracking-wide">
            Bay Area<br />Rapid Transit
          </div>
        </header>

        <div className="flex flex-col items-center w-full pt-6 flex-1">
          
          {/* Dynamic Image Display Box */}
          <div className="w-[85%] h-[180px] border-[3px] border-[#0099D8] bg-[#D1D5DB] flex items-center justify-center mb-5 p-2 relative overflow-y-auto">
            {images.length > 0 ? (
              <div className="w-full h-full flex flex-wrap gap-2 content-start justify-center">
                {images.map((src, index) => (
                  <img 
                    key={index} 
                    src={src} 
                    alt={`Uploaded preview ${index + 1}`} 
                    className="h-full max-w-full object-cover border border-gray-400" 
                  />
                ))}
              </div>
            ) : (
              <img 
                  src="/bart-train-placeholder.jpg" 
                  alt="Uploaded preview placeholder" 
                  className="w-full h-full object-cover"
                  style={{ backgroundColor: '#9CA3AF' }} 
              />
            )}
          </div>

          <textarea 
            placeholder="Enter Incident Context Here:" 
            value={contextText}
            onChange={(e) => setContextText(e.target.value)}
            className="w-[85%] h-28 bg-[#D1D5DB] border border-black p-3 text-sm mb-4 resize-none text-black placeholder:text-gray-700 focus:outline-none focus:border-[#0099D8]"
          />

          <div className="w-[85%] relative mb-4">
            <select 
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full bg-[#D1D5DB] border border-black p-3 text-sm appearance-none text-gray-700 focus:outline-none focus:border-[#0099D8] cursor-pointer"
            >
              <option value="" disabled>Select Priority</option>
              <option value="low">Low</option>
              <option value="high">High</option>
              <option value="emergency">Emergency</option>
              <option value="unknown">Unknown</option>
            </select>
            <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="black" strokeWidth="3" strokeLinecap="square" strokeLinejoin="miter">
                <path d="M6 9l6 6 6-6"/>
              </svg>
            </div>
          </div>

        

          <input 
            type="text" 
            placeholder="Full name:" 
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-[85%] bg-[#D1D5DB] border border-black p-3 text-sm mb-4 text-black placeholder:text-gray-700 focus:outline-none focus:border-[#0099D8]"
          />

          <input 
            type="text" 
            placeholder="Contact (Phone or Email):" 
            value={contact}
            onChange={(e) => setContact(e.target.value)}
            className="w-[85%] bg-[#D1D5DB] border border-black p-3 text-sm mb-6 text-black placeholder:text-gray-700 focus:outline-none focus:border-[#0099D8]"
          />

          <div className="w-full bg-[#FF7676] text-white font-bold py-3 text-center text-[15px] mb-6 tracking-wide shrink-0">
            In case of emergency, please contact 911 first
          </div>

          <button 
            onClick={handleSubmit}
            className="mb-6 shrink-0 bg-[#0099D8] text-white font-bold py-2.5 px-8 text-[15px] border-2 border-gray-300 shadow-[2px_2px_0_0_#9CA3AF] hover:bg-[#007AB8] hover:translate-y-[1px] hover:shadow-[1px_1px_0_0_#9CA3AF] transition-all"
          >
            Submit
          </button>

          <Link href="/" className="pb-8 shrink-0">
            <div className="bg-[#D1D5DB] border-2 border-gray-300 w-16 h-10 flex items-center justify-center cursor-pointer shadow-[2px_2px_0_0_#9CA3AF] hover:bg-gray-400 hover:translate-y-[1px] hover:shadow-[1px_1px_0_0_#9CA3AF] transition-all">
              <ArrowLeft size={24} className="text-black" strokeWidth={2.5} />
            </div>
          </Link>

        </div>
      </div>
    </main>
  );
}