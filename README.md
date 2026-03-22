# MediaAPI — Universal Media Download API

A powerful, high-level API server for downloading media from 1000+ platforms including YouTube, Instagram, TikTok, Twitter/X, and more.

## ✨ Features
- **Universal Support**: 1000+ platforms via `yt-dlp`.
- **Multiple Formats**: Download as Video (up to 4K), Audio (MP3/M4A), or Thumbnails.
- **Playlist Support**: Fetch all items from YouTube playlists or channels.
- **Premium Dashboard**: 
  - **Landing Page**: Public API key creation.
  - **User Dashboard**: Track usage, limits, and request history.
  - **API Docs**: Interactive documentation with live testing.
- **Admin Panel**: Hidden admin panel for managing keys, stats, and logs.
- **Rate Limiting**: Integrated API key system with daily limits.
- **FastAPI Backend**: Async, fast, and scalable.

## 🚀 Deployment (Render Guide)

1. **Fork/Upload to GitHub**: Push this codebase to your GitHub repository.
2. **Create New Web Service on Render**:
   - Connect your GitHub repo.
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. **Environment Variables**:
   Add these in the Render dashboard under **Environment**:
   - `ADMIN_SECRET`: `2810` (or your preferred admin password)
   - `MAX_FREE_REQUESTS`: `100` (daily limit for free keys)
   - `DATABASE_URL`: `sqlite:///./mediaapi.db` (Render disks are ephemeral on free tier; use an external DB like Supabase/Neon for persistence).
4. **Deploy**: Click "Create Web Service".

## 🔐 Admin Panel
To access the admin panel:
1. Go to `https://your-app.onrender.com/#shaun`
2. Enter password: `2810` (default)
3. You can now manage keys, view global logs, and check server stats.

## 🍪 Adding Cookies (for YouTube)
To download age-restricted or member-only videos:
1. Export your cookies from your browser (using an extension like "Get cookies.txt").
2. Save the content to a file named `cookies.txt` in the root directory.
3. Redeploy to Render.

## 🛠 Tech Stack
- **Backend**: FastAPI
- **Engine**: yt-dlp
- **Database**: SQLite / SQLAlchemy
- **Frontend**: Vanilla HTML/CSS/JS (Glassmorphism)
