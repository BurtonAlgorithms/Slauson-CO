#!/bin/bash
# Test webhook with actual headshot and logo images (base64 encoded)

# Use actual image files
HEADSHOT_PATH="/Users/henoktewolde/headshot_example.jpeg"
LOGO_PATH="/Users/henoktewolde/logo_example.jpeg"

# Check if images exist
if [ ! -f "$HEADSHOT_PATH" ]; then
    echo "❌ Error: Headshot not found at $HEADSHOT_PATH"
    exit 1
fi

if [ ! -f "$LOGO_PATH" ]; then
    echo "❌ Error: Logo not found at $LOGO_PATH"
    exit 1
fi

echo "✓ Found headshot: $HEADSHOT_PATH"
echo "✓ Found logo: $LOGO_PATH"
echo ""

# Encode images to base64
echo "Encoding images to base64..."
HEADSHOT_B64=$(base64 -i "$HEADSHOT_PATH" | tr -d '\n')
LOGO_B64=$(base64 -i "$LOGO_PATH" | tr -d '\n')

echo "✓ Images encoded"
echo ""
echo "Sending webhook request with images..."
echo ""

# Send webhook request
curl -X POST http://localhost:5001/webhook/onboarding \
  -H "Content-Type: application/json" \
  -d "{
    \"company_data\": {
      \"name\": \"Astranis\",
      \"description\": \"Astranis is building small, low-cost telecommunications satellites to connect the four billion people who currently lack internet access.\",
      \"address\": \"San Francisco, CA\",
      \"location\": \"San Francisco, CA\",
      \"investment_date\": \"2021-03-15\",
      \"investment_round\": \"SERIES B\",
      \"quarter\": \"Q1\",
      \"year\": \"2021\",
      \"investment_stage\": \"SERIES B • Q1 2021\",
      \"founders\": [\"John Gedmark\", \"Ryan McLinko\"],
      \"co_investors\": [\"Andreessen Horowitz\", \"Venrock\", \"Tribe Capital\"],
      \"background\": \"Astranis is revolutionizing satellite internet by building smaller, more cost-effective satellites. The company's innovative approach enables faster deployment and lower costs, making internet access more accessible globally. Founded in 2015, Astranis has raised over \$350M to date.\"
    },
    \"headshot\": \"$HEADSHOT_B64\",
    \"logo\": \"$LOGO_B64\"
  }"

echo ""
echo ""
echo "✓ Webhook request sent!"

