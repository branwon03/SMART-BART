"use client";

import { useRouter } from "next/navigation";
import { useReportContext } from "@/context/ReportContext";

export function ConfirmationCloseLink() {
  const { clearSubmission } = useReportContext();
  const router = useRouter();

  return (
    <div className="mb-12">
      <button
        type="button"
        className="bg-[#0099D8] text-white font-bold py-2.5 px-10 text-[16px] border-[2px] border-gray-300 shadow-[2px_2px_0_0_#9CA3AF] hover:bg-[#007AB8] hover:translate-y-[1px] hover:shadow-[1px_1px_0_0_#9CA3AF] transition-all"
        onClick={() => {
          clearSubmission();
          router.push("/");
        }}
      >
        Close
      </button>
    </div>
  );
}
