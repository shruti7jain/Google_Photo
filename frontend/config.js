// Google Photos Discovery Engine - API Configuration
// When running locally, connects to localhost:8000.
// Once deployed on Railway, replace the fallback URL with your Railway backend domain!
window.API_BASE_URL = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ? "http://localhost:8000"
  : (window.ENV_API_URL || "https://google-photo-production.up.railway.app");
