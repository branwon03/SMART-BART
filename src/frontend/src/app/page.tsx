"use client";
import { useState } from "react";
import { Upload, ArrowRight, AlertCircle, Loader2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useReportContext } from '../context/ReportContext';
import { FaceDetector, FilesetResolver } from '@mediapipe/tasks-vision';

export default function ImageUpload() {
  const { images, setImages } = useReportContext();
  const router = useRouter(); 
  const [imageError, setImageError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false); 

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
  try {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) {
      alert("FAIL: No files detected by the browser.");
      return;
    }

    const filesArray = Array.from(fileList);
    e.target.value = '';
    
    setIsProcessing(true);
    setImageError(null);

    // Stage 1: Network / WASM Test
    const vision = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
    );


    // Stage 2: AI Model Test
    const faceDetector = await FaceDetector.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_full_range/float16/1/blaze_face_full_range.tflite",
        delegate: "GPU"
      },
      runningMode: "IMAGE",
      //possibly lower the min confidence to 0.2 - currently blurring small parts of objects
      minDetectionConfidence: 0.3,
      minSuppressionThreshold: 0.3
    });
   

    const newImages: string[] = [];

    // Stage 3: The Processing Loop
    for (let i = 0; i < filesArray.length; i++) {
      const file = filesArray[i];
      const img = new Image();
      const objectUrl = URL.createObjectURL(file);
      img.src = objectUrl;

      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = () => reject(new Error("Image failed to load onto Canvas"));
        setTimeout(() => reject(new Error("Image load timed out")), 10000);
      });

      const MAX_WIDTH = 800;
      let width = img.width;
      let height = img.height;

      if (width > MAX_WIDTH) {
        height = (MAX_WIDTH / width) * height;
        width = MAX_WIDTH;
      }

      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (!ctx) continue;

      ctx.drawImage(img, 0, 0, width, height);
      URL.revokeObjectURL(objectUrl); 

      // Stage 4: Detection
      const detections = faceDetector.detect(canvas).detections;
      

      if (detections.length > 0) {
        detections.forEach((detection) => {
          if (!detection.boundingBox) return;
          const { originX, originY, width: bboxWidth, height: bboxHeight } = detection.boundingBox;
          
          // 1. Create a tiny canvas to destroy the pixel data
          const mosaicCanvas = document.createElement("canvas");
          mosaicCanvas.width = 10; 
          mosaicCanvas.height = 10;
          const mosaicCtx = mosaicCanvas.getContext("2d");
          if (!mosaicCtx) return;

          // 2. Draw ONLY the face onto the tiny canvas (compresses the data)
          mosaicCtx.drawImage(
            img, 
            originX, originY, bboxWidth, bboxHeight, // Grab the face
            0, 0, 10, 10                             // Shove it into the 10x10 box
          );

          // Calculate the oval mask coordinates
          const centerX = originX + (bboxWidth / 2);
          const centerY = originY + (bboxHeight / 2);
          const radiusX = bboxWidth / 2;
          const radiusY = (bboxHeight / 2) * 1.1;

          ctx.save();
          
          // 3. Cut the oval hole
          ctx.beginPath();
          ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
          ctx.clip();
          
          // 4. THE MAGIC: Turn off smoothing to get sharp, chunky pixels
          ctx.imageSmoothingEnabled = false;
          
          // 5. Stretch the tiny 10x10 image back over the original face size
          ctx.drawImage(
            mosaicCanvas, 
            0, 0, 10, 10,                            // Source (the tiny compressed image)
            originX, originY, bboxWidth, bboxHeight  // Destination (stretch it big)
          ); 
          
          ctx.restore();
        });
      }
      newImages.push(canvas.toDataURL("image/jpeg", 0.7));
    }
    
    setImages((prev) => [...prev, ...newImages]);


  } catch (error: unknown) {
    // Stage 5: The Silent Killer catcher
    const message = error instanceof Error ? error.message : String(error);
    alert(`CRITICAL ERROR: ${message}`);
    console.error("Processing error:", message);
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
            <img src="/logo.png" alt="BART" className="w-full h-full object-contain" />
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
            Please upload one or more images of the identified incident. You will be prompted to enter your name, contact information, and additional incident context on the next page. All faces featured in uploaded images will be blurred.
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

          {/* The Invisible Overlay Upload Button */}
          {/*DO NOT CHANGE -- VERY IMPORTANT*/}
          <div className="relative inline-block mb-6">
            <div className={`flex items-center justify-center bg-[#0099D8] text-white py-2 px-6 text-[15px] font-bold shadow-md transition-colors ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:bg-[#007AB8]'}`}>
              {isProcessing ? 'Processing...' : 'Upload Images'}
            </div>
            <input 
              type="file" 
              multiple 
              accept="image/*"
              disabled={isProcessing}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" 
              onChange={handleImageUpload}
            />
          </div>

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
