import { useEffect, useMemo, useRef, useState } from "react";
import frontPhoto from "./assets/front-photo.svg";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const AUTH_STORAGE_KEY = "storageapp_auth";
const PROFILE_PHOTO_STORAGE_PREFIX = "storageapp_profile_photo";

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[i]}`;
}

function detectKind(file) {
  if (file.type.startsWith("video/")) return "video";
  return "photo";
}

function encodePathSegments(path) {
  return path
    .split("/")
    .filter(Boolean)
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}

export default function App() {
  const fileInputRef = useRef(null);
  const profilePhotoInputRef = useRef(null);

  const [view, setView] = useState("explore");
  const [authMode, setAuthMode] = useState("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [token, setToken] = useState("");
  const [userEmail, setUserEmail] = useState("");
  const [feed, setFeed] = useState([]);
  const [albums, setAlbums] = useState([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [sharedUrl, setSharedUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [profilePhotoData, setProfilePhotoData] = useState("");

  const quotaBytes = 15 * 1024 * 1024 * 1024;
  const usedBytes = useMemo(() => feed.reduce((sum, item) => sum + item.size_bytes, 0), [feed]);
  const quotaPercent = Math.min(100, Math.round((usedBytes / quotaBytes) * 100));
  const stories = albums.slice(0, 7).map((album) => album.title);

  useEffect(() => {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw);
      if (parsed.token) setToken(parsed.token);
      if (parsed.email) setUserEmail(parsed.email);
    } catch {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    loadData(token);
  }, [token]);

  useEffect(() => {
    if (!userEmail) {
      setProfilePhotoData("");
      return;
    }
    const saved = localStorage.getItem(`${PROFILE_PHOTO_STORAGE_PREFIX}:${userEmail}`) || "";
    setProfilePhotoData(saved);
  }, [userEmail]);

  async function apiRequest(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (options.token) headers.Authorization = `Bearer ${options.token}`;
    if (options.body && !(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    let response;
    try {
      response = await fetch(`${API_BASE}${path}`, {
        method: options.method || "GET",
        headers,
        body: options.body instanceof FormData ? options.body : options.body ? JSON.stringify(options.body) : undefined
      });
    } catch (err) {
      throw new Error(`Network error: cannot reach backend at ${API_BASE}`);
    }
    if (!response.ok) {
      let detail = `Request failed (${response.status})`;
      try {
        const payload = await response.json();
        detail = payload.detail || detail;
      } catch {
        // keep fallback detail
      }
      throw new Error(detail);
    }
    if (response.status === 204) return null;
    return response.json();
  }

  async function loadData(activeToken) {
    try {
      const [feedData, albumsData] = await Promise.all([
        apiRequest("/media/feed", { token: activeToken }),
        apiRequest("/albums", { token: activeToken })
      ]);
      setFeed(feedData || []);
      setAlbums(albumsData || []);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAuthSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setStatus("");
    try {
      if (authMode === "register") {
        await apiRequest("/auth/register", {
          method: "POST",
          body: { email: authEmail, password: authPassword }
        });
      }

      const form = new URLSearchParams();
      form.append("username", authEmail);
      form.append("password", authPassword);

      const loginResponse = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form.toString()
      });
      if (!loginResponse.ok) {
        const payload = await loginResponse.json().catch(() => ({}));
        throw new Error(payload.detail || "Invalid credentials");
      }
      const loginData = await loginResponse.json();

      setToken(loginData.access_token);
      setUserEmail(authEmail);
      localStorage.setItem(
        AUTH_STORAGE_KEY,
        JSON.stringify({ token: loginData.access_token, email: authEmail })
      );
      setAuthPassword("");
      setStatus("Authenticated.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function handleLogout() {
    setToken("");
    setUserEmail("");
    setFeed([]);
    setAlbums([]);
    setSharedUrl("");
    localStorage.removeItem(AUTH_STORAGE_KEY);
    setStatus("Logged out.");
    setError("");
  }

  function handleProfilePhotoSelect(file) {
    if (!file) return;
    if (!file.type?.startsWith("image/")) {
      setError("Please choose an image for profile photo.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const value = typeof reader.result === "string" ? reader.result : "";
      setProfilePhotoData(value);
      if (userEmail) {
        localStorage.setItem(`${PROFILE_PHOTO_STORAGE_PREFIX}:${userEmail}`, value);
      }
      setStatus("Profile photo updated.");
      setError("");
    };
    reader.readAsDataURL(file);
  }

  async function handleUpload(file) {
    if (!file || !token) return;
    if (!(file.type?.startsWith("image/") || file.type?.startsWith("video/"))) {
      setError("Please upload only image or video files.");
      return;
    }
    setBusy(true);
    setError("");
    setStatus("");
    try {
      const meta = await apiRequest("/media/upload-url", {
        method: "POST",
        token,
        body: {
          filename: file.name,
          content_type: file.type || "application/octet-stream",
          size_bytes: file.size,
          kind: detectKind(file)
        }
      });

      const uploadUrl = new URL(meta.upload_url, API_BASE);
      const apiOrigin = new URL(API_BASE).origin;
      const isLocalUpload =
        uploadUrl.origin === apiOrigin && uploadUrl.pathname.startsWith("/media/upload/");
      const uploadHeaders = { "Content-Type": file.type || "application/octet-stream" };
      if (isLocalUpload) uploadHeaders.Authorization = `Bearer ${token}`;

      const uploadResponse = await fetch(uploadUrl.toString(), {
        method: meta.upload_method || "PUT",
        headers: uploadHeaders,
        body: file
      });
      if (!uploadResponse.ok) {
        const payload = await uploadResponse.json().catch(() => ({}));
        throw new Error(payload.detail || "Upload failed");
      }

      await loadData(token);
      setView("explore");
      setStatus(`Uploaded ${file.name}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleCreateAlbum() {
    if (!token) return;
    const title = window.prompt("Album title");
    if (!title) return;
    try {
      await apiRequest("/albums", { method: "POST", token, body: { title } });
      await loadData(token);
      setView("albums");
      setStatus("Album created.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAddToAlbum(mediaId) {
    if (!token) return;
    if (!albums.length) {
      setStatus("Create an album first.");
      return;
    }
    const choices = albums.map((album, index) => `${index + 1}. ${album.title}`).join("\n");
    const picked = window.prompt(`Select album number:\n${choices}`);
    const idx = Number(picked) - 1;
    const album = albums[idx];
    if (!album) return;
    try {
      await apiRequest(`/albums/${album.id}/items`, {
        method: "POST",
        token,
        body: { media_id: mediaId }
      });
      setStatus(`Added to "${album.title}".`);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleShare(mediaId) {
    if (!token) return;
    try {
      const share = await apiRequest("/share", {
        method: "POST",
        token,
        body: { media_id: mediaId }
      });
      const url = `${API_BASE}/share/${share.token}`;
      setSharedUrl(url);
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url);
      }
      setStatus("Share link created.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(mediaId) {
    if (!token) return;
    try {
      await apiRequest(`/media/${mediaId}`, { method: "DELETE", token });
      await loadData(token);
      setStatus("Media deleted.");
    } catch (err) {
      setError(err.message);
    }
  }

  function mediaUrl(item) {
    return `${API_BASE}/uploads/${encodePathSegments(item.s3_key)}`;
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-dot" />
          StorageApp
        </div>
        <nav className="nav">
          <button className="ghost" onClick={() => setView("explore")}>Explore</button>
          <button className="ghost" onClick={() => setView("albums")}>Albums</button>
          <button className="ghost" onClick={() => setView("shared")}>Shared</button>
          <button className="cta" onClick={() => fileInputRef.current?.click()} disabled={!token || busy}>
            Upload
          </button>
          {token ? (
            <button className="ghost" onClick={handleLogout}>Logout</button>
          ) : null}
        </nav>
      </header>

      <main className="layout">
        <section className="profile">
          <div className="avatar">
            <img
              src={profilePhotoData || frontPhoto}
              alt="Profile"
            />
            {token ? (
              <button
                type="button"
                className="avatar-picker"
                onClick={() => profilePhotoInputRef.current?.click()}
                title="Upload profile photo"
              >
                +
              </button>
            ) : null}
          </div>
          <div>
            {token ? (
              <>
                <h1>hey, {userEmail.split("@")[0] || "creator"}</h1>
                <p>Private vault for photos & videos. Share only when you choose.</p>
                <div className="quota">
                  <div className="quota-label">
                    <span>Storage</span>
                    <span>{`${formatBytes(usedBytes)} of 15 GB`}</span>
                  </div>
                  <div className="quota-bar">
                    <div className="quota-fill" style={{ width: `${quotaPercent}%` }} />
                  </div>
                </div>
                <div className="profile-actions">
                  <button className="cta" onClick={handleCreateAlbum}>New Album</button>
                  <button className="ghost" onClick={() => setView("shared")}>View Shared</button>
                </div>
              </>
            ) : (
              <form className="auth-form" onSubmit={handleAuthSubmit}>
                <h1>{authMode === "login" ? "welcome back" : "create account"}</h1>
                <p>Authenticate to sync the UI with your backend storage.</p>
                <input
                  type="email"
                  placeholder="Email"
                  value={authEmail}
                  onChange={(event) => setAuthEmail(event.target.value)}
                  required
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={authPassword}
                  onChange={(event) => setAuthPassword(event.target.value)}
                  minLength={8}
                  required
                />
                <div className="profile-actions">
                  <button className="cta" type="submit" disabled={busy}>
                    {authMode === "login" ? "Login" : "Register + Login"}
                  </button>
                  <button
                    className="ghost"
                    type="button"
                    onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}
                  >
                    {authMode === "login" ? "Need account?" : "Have account?"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </section>

        <section className="stories">
          {stories.map((name) => (
            <div className="story" key={name}>
              <div className="story-ring" />
              <span>{name}</span>
            </div>
          ))}
        </section>

        {status ? <div className="status ok">{status}</div> : null}
        {error ? <div className="status err">{error}</div> : null}
        {sharedUrl ? (
          <div className="status ok">
            Share URL: <a href={sharedUrl} target="_blank" rel="noreferrer">{sharedUrl}</a>
          </div>
        ) : null}

        {view === "albums" ? (
          <section className="grid">
            {albums.map((album) => (
              <article className="card" key={album.id}>
                <div className="thumb"><span>album</span></div>
                <div className="card-meta">
                  <h3>{album.title}</h3>
                </div>
              </article>
            ))}
            {!albums.length ? <div className="status">No albums yet.</div> : null}
          </section>
        ) : view === "shared" ? (
          <section className="grid">
            <div className="status">
              {sharedUrl || "Create a media share link from Explore and it will appear here."}
            </div>
          </section>
        ) : (
          <section className="grid">
            {feed.map((post) => (
              <article className="card media-card" key={post.id}>
                <a
                  className={`thumb ${post.kind}`}
                  href={mediaUrl(post)}
                  target="_blank"
                  rel="noreferrer"
                  title="Open in new tab"
                >
                  {post.content_type.startsWith("image/") ? (
                    <img src={mediaUrl(post)} alt={post.filename} />
                  ) : post.content_type.startsWith("video/") ? (
                    <video src={mediaUrl(post)} controls preload="metadata" />
                  ) : (
                    <img src={frontPhoto} alt="Front" />
                  )}
                </a>
                <div className="card-meta">
                  <h3>{post.filename}</h3>
                  <div className="card-actions">
                    <button className="ghost" onClick={() => handleShare(post.id)}>Share</button>
                    <button className="ghost" onClick={() => handleAddToAlbum(post.id)}>Add to album</button>
                    <button className="ghost" onClick={() => handleDelete(post.id)}>Delete</button>
                  </div>
                </div>
              </article>
            ))}
            {!feed.length && token ? <div className="status">No media yet. Upload your first file.</div> : null}
            {!token ? <div className="status">Login to load your feed.</div> : null}
          </section>
        )}
      </main>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,video/*"
        hidden
        onChange={(event) => handleUpload(event.target.files?.[0])}
      />
      <input
        ref={profilePhotoInputRef}
        type="file"
        accept="image/*"
        hidden
        onChange={(event) => handleProfilePhotoSelect(event.target.files?.[0])}
      />
    </div>
  );
}
