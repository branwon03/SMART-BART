"use client";

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { useReportContext } from '@/context/ReportContext';
import { submitReport } from '@/lib/submissions';

export default function UserContext() {
  const router = useRouter();
  const { 
    images, 
    contextText, setContextText,
    priority, setPriority,
    location, setLocation,
    fullName, setFullName,
    contact, setContact
  } = useReportContext();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!contextText.trim() || !fullName.trim() || !contact.trim() || !priority.trim()) {
      alert("Please provide the incident context, priority, your full name, and contact information before submitting.");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await submitReport({
        images,
        description: contextText,
        priority,
        location,
      });
      router.push('/confirmation');
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Submission failed. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center bg-white text-black max-w-md mx-auto border-x border-gray-100 shadow-2xl">
      <div className="w-full flex flex-col h-full">
        
        <header className="w-full bg-black h-[72px] flex items-center px-4 gap-3 shrink-0">
          <div className="bg-white w-[52px] h-[36px] flex items-center justify-center p-1 rounded-sm">
            <img src="/logo.png" alt="BART" className="w-full h-full object-contain" />
          </div>
          <div className="text-white text-[15px] font-bold leading-tight tracking-wide">
            Bay Area<br />Rapid Transit
          </div>
        </header>

        <div className="flex flex-col items-center w-full pt-6 flex-1">
          
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
              <div className="w-full h-full bg-[#9CA3AF]" />
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
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full bg-[#D1D5DB] border border-black p-3 text-sm appearance-none text-gray-700 focus:outline-none focus:border-[#0099D8] cursor-pointer"
            >
              <option value="" disabled>Select Station</option>
              <option value="12th St. Oakland City Center">12th St. Oakland City Center</option>
              <option value="16th St. Mission">16th St. Mission</option>
              <option value="19th St. Oakland">19th St. Oakland</option>
              <option value="24th St. Mission">24th St. Mission</option>
              <option value="Antioch">Antioch</option>
              <option value="Ashby">Ashby</option>
              <option value="Balboa Park">Balboa Park</option>
              <option value="Bay Fair">Bay Fair</option>
              <option value="Berryessa / North San Jose">Berryessa / North San Jose</option>
              <option value="Castro Valley">Castro Valley</option>
              <option value="Civic Center / UN Plaza">Civic Center / UN Plaza</option>
              <option value="Coliseum">Coliseum</option>
              <option value="Colma">Colma</option>
              <option value="Concord">Concord</option>
              <option value="Daly City">Daly City</option>
              <option value="Downtown Berkeley">Downtown Berkeley</option>
              <option value="Dublin / Pleasanton">Dublin / Pleasanton</option>
              <option value="El Cerrito del Norte">El Cerrito del Norte</option>
              <option value="El Cerrito Plaza">El Cerrito Plaza</option>
              <option value="Embarcadero">Embarcadero</option>
              <option value="Fremont">Fremont</option>
              <option value="Fruitvale">Fruitvale</option>
              <option value="Glen Park">Glen Park</option>
              <option value="Hayward">Hayward</option>
              <option value="Lafayette">Lafayette</option>
              <option value="Lake Merritt">Lake Merritt</option>
              <option value="MacArthur">MacArthur</option>
              <option value="Millbrae">Millbrae</option>
              <option value="Milpitas">Milpitas</option>
              <option value="Montgomery St.">Montgomery St.</option>
              <option value="North Berkeley">North Berkeley</option>
              <option value="North Concord / Martinez">North Concord / Martinez</option>
              <option value="Oakland International Airport">Oakland International Airport</option>
              <option value="Orinda">Orinda</option>
              <option value="Pittsburg / Bay Point">Pittsburg / Bay Point</option>
              <option value="Pittsburg Center">Pittsburg Center</option>
              <option value="Pleasant Hill / Contra Costa Centre">Pleasant Hill / Contra Costa Centre</option>
              <option value="Powell St.">Powell St.</option>
              <option value="Richmond">Richmond</option>
              <option value="Rockridge">Rockridge</option>
              <option value="San Bruno">San Bruno</option>
              <option value="San Francisco International Airport">San Francisco International Airport</option>
              <option value="San Leandro">San Leandro</option>
              <option value="South Hayward">South Hayward</option>
              <option value="South San Francisco">South San Francisco</option>
              <option value="Union City">Union City</option>
              <option value="Walnut Creek">Walnut Creek</option>
              <option value="Warm Springs / South Fremont">Warm Springs / South Fremont</option>
              <option value="West Dublin / Pleasanton">West Dublin / Pleasanton</option>
              <option value="West Oakland">West Oakland</option>
            </select>
            <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="black" strokeWidth="3" strokeLinecap="square" strokeLinejoin="miter">
                <path d="M6 9l6 6 6-6"/>
              </svg>
            </div>
          </div>

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

          {submitError && (
            <div className="w-[85%] bg-red-50 border border-red-300 text-red-700 text-sm p-3 mb-4 rounded">
              {submitError}
            </div>
          )}

          <button 
            onClick={handleSubmit}
            disabled={isSubmitting}
            className={`mb-6 shrink-0 bg-[#0099D8] text-white font-bold py-2.5 px-8 text-[15px] border-2 border-gray-300 shadow-[2px_2px_0_0_#9CA3AF] transition-all ${isSubmitting ? 'opacity-50 cursor-not-allowed' : 'hover:bg-[#007AB8] hover:translate-y-[1px] hover:shadow-[1px_1px_0_0_#9CA3AF]'}`}
          >
            {isSubmitting ? (
              <span className="flex items-center gap-2">
                <Loader2 size={16} className="animate-spin" />
                Submitting...
              </span>
            ) : (
              "Submit"
            )}
          </button>

          <Link href="/report" className="pb-8 shrink-0">
            <div className="bg-[#D1D5DB] border-2 border-gray-300 w-16 h-10 flex items-center justify-center cursor-pointer shadow-[2px_2px_0_0_#9CA3AF] hover:bg-gray-400 hover:translate-y-[1px] hover:shadow-[1px_1px_0_0_#9CA3AF] transition-all">
              <ArrowLeft size={24} className="text-black" strokeWidth={2.5} />
            </div>
          </Link>

        </div>
      </div>
    </main>
  );
}
