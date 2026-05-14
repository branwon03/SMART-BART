#!/bin/sh
npx expo start --tunnel &
EXPO_PID=$!

sleep 15
TUNNEL_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | grep -o 'https://.*' | sed 's/https/exp/')

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

wait $EXPO_PID