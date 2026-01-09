#!/bin/bash
# Test Auth Flow

# 1. Signup
echo "--- SIGNUP ---"
curl -c cookies.txt -b cookies.txt -X POST http://127.0.0.1:8000/api/auth/signup/ \
  -H "Content-Type: application/json" \
  -d '{"username": "auth_test_user", "password": "password123", "email": "test@example.com"}' 
echo -e "\n"

# 2. Check Me
echo "--- CHECK ME ---"
curl -c cookies.txt -b cookies.txt http://127.0.0.1:8000/api/auth/me/
echo -e "\n"

# 3. Trade (Authenticated) - reusing rain-tomorrow-777 or finding a market
echo "--- TRADE AUTHENTICATED ---"
# Need to find a market slug first, let's just assume one exists or list them
MARKET_SLUG=$(curl -s http://127.0.0.1:8000/api/markets/ | grep -o '"slug": "[^"]*"' | head -1 | cut -d'"' -f4)
echo "Trading on market: $MARKET_SLUG"

if [ -n "$MARKET_SLUG" ]; then
    # Get outcome ID
    OUTCOME_ID=$(curl -s http://127.0.0.1:8000/api/markets/$MARKET_SLUG/ | grep -o '"id": [0-9]*' | head -1 | cut -d' ' -f2)
    echo "Outcome ID: $OUTCOME_ID"
    
    curl -c cookies.txt -b cookies.txt -X POST http://127.0.0.1:8000/api/markets/$MARKET_SLUG/trade/ \
      -H "Content-Type: application/json" \
      -d "{\"outcome_id\": $OUTCOME_ID, \"amount\": 10}"
    echo -e "\n"
fi

# 4. Logout
echo "--- LOGOUT ---"
curl -c cookies.txt -b cookies.txt -X POST http://127.0.0.1:8000/api/auth/logout/
echo -e "\n"

# 5. Check Me (Should fail)
echo "--- CHECK ME (Logged Out) ---"
curl -c cookies.txt -b cookies.txt http://127.0.0.1:8000/api/auth/me/
echo -e "\n"

# 6. Trade (Should fail)
echo "--- TRADE UNAUTHENTICATED ---"
if [ -n "$MARKET_SLUG" ]; then
    curl -c cookies.txt -b cookies.txt -X POST http://127.0.0.1:8000/api/markets/$MARKET_SLUG/trade/ \
      -H "Content-Type: application/json" \
      -d "{\"outcome_id\": $OUTCOME_ID, \"amount\": 10}"
    echo -e "\n"
fi
