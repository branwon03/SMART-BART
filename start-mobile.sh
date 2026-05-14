#!/bin/sh

echo "Waiting for tunnels to start..."
sleep 25

# Get backend URL from frontend Cloudflare tunnel logs
BACKEND_URL=$(docker logs bart-mobile-tunnel 2>&1 | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -1)

if [ -z "$BACKEND_URL" ]; then
  echo "Warning: Could not get frontend tunnel URL, falling back to http://backend:8000"
  BACKEND_URL="http://backend:8000"
fi

echo "Using backend URL: $BACKEND_URL"
echo "EXPO_PUBLIC_API_BASE_URL=$BACKEND_URL" > /app/.env

# Start Expo with tunnel for Expo Go QR code
npx expo start --tunnel &
EXPO_PID=$!

sleep 20

# Get mobile tunnel URL from ngrok
TUNNEL_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | grep -o 'https://.*' | head -1 | sed 's/https/exp/')

echo ""
echo "========================================="
echo "MOBILE TUNNEL URL:"
echo "$TUNNEL_URL"
echo "========================================="
echo ""
echo "Scan this QR code with Expo Go:"
echo ""
qrencode -t ANSIUTF8 "$TUNNEL_URL"
echo ""
echo "========================================="
echo "BACKEND URL (via frontend proxy):"
echo "$BACKEND_URL"
echo "========================================="

wait $EXPO_PID