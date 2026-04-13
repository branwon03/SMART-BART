// src/mobile/lib/submissions.ts
const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL; //my .env file has EXPO_PUBLIC_API_BASE_URL=http://10.56.194.213:8000 currently

export async function submitMobileReport(params: {
  images: string[]; // Array of URIs from your image picker
  description: string;
  location: string;
}) {
  const form = new FormData();

  
  params.images.forEach((uri, i) => {
    // @ts-ignore - FormData expects this specific structure in React Native
    form.append("media", {
      uri: uri,
      type: "image/jpeg",
      name: `incident-image-${i}.jpg`,
    });
  });

  form.append("description", params.description);
  form.append("photo_location_id", params.location);

  const res = await fetch(`${API_BASE_URL}/api/submissions`, {
    method: "POST",
    body: form,
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Submission failed: ${errorText}`);
  }

  return res.json();
}