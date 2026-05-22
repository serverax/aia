# AiA Landing Page

Animated motion graphics landing page for AI Manufacturing Intelligence platform.

## Features

- ✨ **Smooth Animations** - Floating machines, pulsing orb, rotating rings
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile
- 🎨 **Modern UI** - Gradient backgrounds, glassmorphism effects
- ⚡ **Fast Loading** - Pure HTML/CSS/JS, no external dependencies
- 🚀 **Production Ready** - Optimized for Kubernetes deployment

## Local Development

```bash
# Simply open index.html in a browser
open landing-page/index.html

# Or run a local server
python -m http.server 8000 --directory landing-page
# Visit http://localhost:8000
```

## Deployment

### Option 1: Docker

```bash
cd landing-page
docker build -t aia-landing:latest .
docker run -p 80:80 aia-landing:latest
```

### Option 2: Kubernetes

```bash
kubectl apply -f landing-page/nginx.yaml

# Access at: http://aia.ordinoxai.com
```

### Option 3: Static Hosting

Deploy index.html to any web hosting service (Netlify, Vercel, AWS S3, etc.)

## Customization

### Colors
Change gradient colors in CSS:
```css
background: linear-gradient(135deg, #64c8ff 0%, #00ffff 100%);
```

### Text
Edit hero section and feature cards in HTML

### Animations
Modify keyframe animations in CSS for different effects

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## Performance

- Zero external dependencies
- Optimized animations (GPU-accelerated)
- Fast paint/composite cycles
- Mobile-friendly

---

**Status: Production Ready ✅**
