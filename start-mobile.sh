#!/bin/sh
npx expo start --tunnel &
EXPO_PID=$!

# Wait for ngrok to be ready then print the tunnel URL
sleep 15
echo ""
echo "========================================="
echo "MOBILE TUNNEL URL:"
curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | grep -o 'https://.*' | sed 's/https/exp/'
echo "========================================="
echo ""

wait $EXPO_PID