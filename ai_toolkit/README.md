# AI Toolkit — Deployment Guide

## Architecture
- **Frontend**: Single HTML page → Cloudflare Pages (free, no cold start)
- **Backend**: Cloudflare Worker → DeepSeek API proxy (free 100k req/day, no cold start)
- **AI**: DeepSeek Chat API (50 yuan budget)

## Quick Deploy

### 1. Deploy Worker (Backend)
```bash
cd earn_online/ai_toolkit
npx wrangler login
npx wrangler deploy worker.js
# Set API key:
npx wrangler secret put DEEPSEEK_API_KEY
# Paste your DeepSeek API key when prompted
```

### 2. Deploy Frontend
- Go to Cloudflare Dashboard → Workers & Pages → Pages
- Upload `index.html` or connect Git repo
- Deploy

### 3. Connect
Edit `index.html` line ~330: change `API_URL` to your Worker URL
Re-deploy the frontend after updating.

## Monetization Path

### Phase 1: Free + Ads (Month 1-3)
- Google AdSense on the tool page
- Build SEO traffic via blog content
- Target: 1000 daily visitors → ~$3-5/day AdSense

### Phase 2: Freemium (Month 3-6)
- Free: 20 uses/day
- Pro: $5/month unlimited
- Target: 50 paying users → $250/month

### Phase 3: B2B/White Label (Month 6+)
- API access for businesses
- Custom branding option

## Free Marketing Channels
1. **Reddit**: r/InternetIsBeautiful, r/FreeTools, r/webdev
2. **ProductHunt**: Launch the tool
3. **Twitter/X**: Share AI tips and link to tool
4. **IndieHackers**: Share revenue journey
5. **SEO**: Write blog posts targeting "free AI rewriter", "free text summarizer", etc.

## Cost Estimation
- DeepSeek: ~500 tokens/request average → ~100k requests from 50 yuan
- Cloudflare Pages: Free (unlimited static)
- Cloudflare Workers: Free (100k requests/day)
- Total: ¥0/month hosting + ¥50 one-time API budget
