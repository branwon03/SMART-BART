import Link from "next/link";
import { ConfirmationCloseLink } from "./ConfirmationCloseLink";

export default function Confirmation() {
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

        <div className="w-full bg-[#0099D8] text-white text-[24px] font-bold py-8 px-6 text-center leading-tight">
          Success!<br />
          Your Submission Has Been<br />
          Processed
        </div>

        <div className="flex flex-col items-center w-full pt-12 flex-1">
          <div className="bg-[#D1D5DB] border-[2px] border-black text-black text-[16px] py-8 px-6 text-center w-[85%] mb-14 leading-relaxed font-medium">
            You may be contacted for additional information regarding your report. If you have any further questions, please reach out to example.email@bart.org
          </div>

          <Link href="/review" className="mb-8">
            <button className="bg-[#0099D8] text-white font-bold py-2.5 px-6 text-[16px] border-[2px] border-gray-300 shadow-[2px_2px_0_0_#9CA3AF] hover:bg-[#007AB8] hover:translate-y-[1px] hover:shadow-[1px_1px_0_0_#9CA3AF] transition-all">
              Review Submission
            </button>
          </Link>

          <ConfirmationCloseLink />
        </div>
      </div>
    </main>
  );
}
