#!/bin/bash

echo "📸 Creating Landing Page Screenshot..."
echo ""

# Use headless browser if available
if command -v google-chrome &> /dev/null; then
    google-chrome --headless --disable-gpu --screenshot=/tmp/landing.png \
      --window-size=1920,1080 \
      file:///mnt/f/aia/landing-page/index.html
    
    echo "✅ Screenshot saved: /tmp/landing.png"
    echo ""
    echo "View with:"
    echo "  display /tmp/landing.png"
    echo "  or"
    echo "  eog /tmp/landing.png"
    
elif command -v firefox &> /dev/null; then
    firefox --headless --screenshot=/tmp/landing.png \
      file:///mnt/f/aia/landing-page/index.html
    
    echo "✅ Screenshot saved: /tmp/landing.png"
else
    echo "⚠️ No headless browser found"
    echo "Install: sudo apt install google-chrome-stable"
fi
