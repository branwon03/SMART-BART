"use client";
import { useState } from "react";
import { Upload, ArrowRight, AlertCircle, Loader2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useReportContext } from '../context/ReportContext';
import * as tf from '@tensorflow/tfjs';
import * as blazeface from '@tensorflow-models/blazeface';

export default function ImageUpload() {
  const { images, setImages } = useReportContext();
  const router = useRouter(); 
  const [imageError, setImageError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false); 

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    setIsProcessing(true);
    setImageError(null);

    try {
      // Initialize TensorFlow and load Blazeface
      await tf.ready();
      const model = await blazeface.load();

      const newImages: string[] = [];

      // Loop through all uploaded files
      for (let i = 0; i < fileList.length; i++) {
        const file = fileList[i];
        
        if (file.size < 100 * 1024) {
          setImageError("One or more images were too low quality and were skipped.");
          continue; 
        }

        // Convert pitcure to an HTML image element
        const img = new Image();
        img.src = URL.createObjectURL(file);
        await new Promise((resolve) => { img.onload = resolve; });

        // Create an invisible Canvas
        const canvas = document.createElement("canvas");
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext("2d");
        if (!ctx) continue;

        // Draw the original image onto the canvas
        ctx.drawImage(img, 0, 0);

        // Detect Faces using the AI model (Passing the canvas instead of img is more reliable)
        const predictions = await model.estimateFaces(canvas, false);
        
        console.log(`Image ${i + 1}: Found ${predictions.length} face(s)`);

        // Blur faces
        if (predictions.length > 0) {
          predictions.forEach((prediction) => {
            const topLeft = prediction.topLeft as [number, number];
            const bottomRight = prediction.bottomRight as [number, number];
            
            // Padding blurs whole head, can be adjusted if we need to minimize
            const padding = 40; 
            const x = topLeft[0] - padding;
            const y = topLeft[1] - padding;
            const width = (bottomRight[0] - topLeft[0]) + (padding * 2);
            const height = (bottomRight[1] - topLeft[1]) + (padding * 2);

            ctx.save(); // Save unblurred canvas state
            
            // Draw an invisible path around the face
            ctx.beginPath();
            ctx.rect(x, y, width, height);
            ctx.clip();

            // Adjust blur if needed in the future
            ctx.filter = "blur(30px)";
            ctx.drawImage(img, 0, 0);

            ctx.restore();
          });
        }

        // Export blurred canvas
        newImages.push(canvas.toDataURL("image/jpeg", 0.8));
      }

      setImages((prev) => [...prev, ...newImages]);

    } catch (error) {
      console.error("Error processing image:", error);
      setImageError("Something went wrong while applying the privacy blur.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleNextPage = () => {
    if (images.length === 0) {
      alert("Please upload at least one image of the incident before proceeding.");
      return;
    }
    router.push('/context');
  };

  return (
    <main className="min-h-screen flex flex-col items-center bg-white text-black max-w-md mx-auto border-x border-gray-100 shadow-2xl">
      <div className="w-full flex flex-col h-full items-center">
        
        <header className="w-full bg-black h-[72px] flex items-center px-4 gap-3 shrink-0">
          <div className="bg-white w-[52px] h-[36px] flex items-center justify-center p-1 rounded-sm">
            <img src="/bart-logo.png" alt="BART" className="w-full h-full object-contain" />
          </div>
          <div className="text-white text-[15px] font-bold leading-tight tracking-wide">
            Bay Area<br />Rapid Transit
          </div>
        </header>

        <h1 className="w-full bg-[#0099D8] text-white text-[22px] font-bold py-3 px-6 text-center shrink-0">
          Incident Reporting Form
        </h1>

        <div className="flex flex-col items-center w-full pt-4 flex-1">
          
          <div className="bg-[#D1D5DB] text-black text-sm py-5 px-8 text-center w-[85%] mb-8">
            Please upload one or more images of the identified incident. You will be prompted to enter your name, contact information, and additional incident context on the next page.
          </div>

          <div className={`w-[85%] aspect-[3/4] border-[4px] ${imageError ? 'border-red-500 bg-red-50' : 'border-[#0099D8] bg-[#D1D5DB]'} relative flex items-center justify-center mb-6 transition-colors`}>
            {isProcessing ? (
              <div className="flex flex-col items-center text-[#0099D8]">
                <Loader2 size={64} className="animate-spin mb-4" />
                <p className="text-sm font-bold text-black">Applying Privacy Blur...</p>
              </div>
            ) : images.length === 0 ? (
              <Upload size={80} strokeWidth={1.5} className={imageError ? 'text-red-400' : 'text-black'} />
            ) : (
              <div className="w-full h-full p-2 flex flex-wrap gap-2 overflow-y-auto content-start justify-center">
                {images.map((src, index) => (
                  <img 
                    key={index} 
                    src={src} 
                    alt={`Uploaded preview ${index + 1}`} 
                    className="w-[45%] aspect-square object-cover border border-gray-400" 
                  />
                ))}
              </div>
            )}
          </div>

          {/* Upload Button */}
          <label className={`cursor-pointer bg-[#0099D8] text-white py-2 px-6 text-[15px] font-bold shadow-md transition-colors mb-6 ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:bg-[#007AB8]'}`}>
            {isProcessing ? 'Processing...' : 'Upload Images'}
            <input 
              type="file" 
              multiple 
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden" 
              disabled={isProcessing}
            />
          </label>

          {imageError && (
            <div className="flex items-start gap-2 text-red-600 bg-red-50 p-3 border border-red-200 rounded-md w-[85%] mb-6 shadow-sm">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <p className="text-sm font-medium">{imageError}</p>
            </div>
          )}

          <button 
            onClick={handleNextPage}
            disabled={isProcessing}
            className={`bg-[#D1D5DB] border border-gray-300 w-16 h-10 flex items-center justify-center shadow-md transition-colors mb-8 ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-400 cursor-pointer'}`}
          >
            <ArrowRight size={24} className="text-black" strokeWidth={2} />
          </button>
          
        </div>
      </div>
    </main>
  );
}