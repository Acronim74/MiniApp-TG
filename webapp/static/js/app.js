(function(){
  // try to post initData to backend
  async function postInitData(initData) {
    try {
      const resp = await fetch("/auth/init", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ init_data: initData }),
      });
      const json = await resp.json();
      return { ok: resp.ok, status: resp.status, body: json };
    } catch (e) {
      return { ok: false, status: 0, body: { error: String(e) } };
    }
  }

  function showUser(user, raw) {
    document.getElementById("username").textContent = user.username || user.first_name || "—";
    document.getElementById("tid").textContent = user.id || "—";
    document.getElementById("auth_date").textContent = user.auth_date ? new Date(user.auth_date * 1000).toLocaleString() : "—";
    document.getElementById("greeting").textContent = user.username ? `Привет, ${user.username}!` : "Привет!";
    document.getElementById("response").textContent = JSON.stringify(raw, null, 2);
  }

  // wait up to timeoutMs for Telegram.WebApp.initData to appear
  async function waitForTelegramInitData(timeoutMs = 2000, intervalMs = 100) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      try {
        if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) {
          console.debug("Found Telegram.WebApp.initData (poll)");
          return window.Telegram.WebApp.initData;
        }
      } catch (e) {
        // ignore
      }
      await new Promise(r => setTimeout(r, intervalMs));
    }
    return null;
  }

  // try multiple fallback locations for initData (query params, hash)
  function findInitDataFromUrl() {
    try {
      // first try regular query params (decoded)
      const qs = new URLSearchParams(window.location.search);
      if (qs.get("initData")) return qs.get("initData");
      if (qs.get("tgWebAppInitData")) return qs.get("tgWebAppInitData");
      if (qs.get("init_data")) return qs.get("init_data");
    } catch (e) {
      // ignore
    }

    try {
      // IMPORTANT: If Telegram opened the page in an external browser it may put
      // data in the hash as tgWebAppData. We must prefer the RAW substring from
      // location.hash (percent-encoded) to avoid modifying the original string
      // used by Telegram to compute the hash.
      const hash = window.location.hash || "";
      const match = hash.match(/(?:#|&)?tgWebAppData=([^&]+)/);
      if (match && match[1]) {
        // return the raw percent-encoded fragment (DO NOT decode here)
        return match[1];
      }

      // fallback to parsed hash params (decoded) if tgWebAppData key not found
      const hashParams = new URLSearchParams(hash.replace(/^#/, ""));
      if (hashParams.get("initData")) return hashParams.get("initData");
      if (hashParams.get("tgWebAppInitData")) return hashParams.get("tgWebAppInitData");
      if (hashParams.get("init_data")) return hashParams.get("init_data");
    } catch (e) {
      // ignore
    }
    return null;
  }

  async function bootstrap() {
    console.debug("Bootstrap: attempting to obtain Telegram initData");

    // 1) direct synchronous read (fast path)
    try {
      if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) {
        console.debug("Found Telegram.WebApp.initData (sync)");
        const initData = window.Telegram.WebApp.initData;
        const res = await postInitData(initData);
        if (res.ok && res.body && res.body.user) {
          showUser(res.body.user, res.body);
          return;
        } else {
          document.getElementById("response").textContent = "Verification failed: " + JSON.stringify(res);
          return;
        }
      }
    } catch (e) {
      console.debug("Error reading Telegram.WebApp.initData (sync):", e);
    }

    // 2) wait a short time for Telegram to inject the object (race condition)
    const waitedInitData = await waitForTelegramInitData(2000, 100);
    if (waitedInitData) {
      const res = await postInitData(waitedInitData);
      if (res.ok && res.body && res.body.user) {
        showUser(res.body.user, res.body);
        return;
      } else {
        document.getElementById("response").textContent = "Verification failed: " + JSON.stringify(res);
        return;
      }
    }

    // 3) fallback: query/hash params (including raw tgWebAppData)
    const qpInit = findInitDataFromUrl();
    if (qpInit) {
      console.debug("Found initData in URL/hash (fallback)");
      const res = await postInitData(qpInit);
      if (res.ok && res.body && res.body.user) {
        showUser(res.body.user, res.body);
        return;
      } else {
        document.getElementById("response").textContent = "Verification failed: " + JSON.stringify(res);
        return;
      }
    }

    // nothing found
    document.getElementById("response").textContent = "No initData found. Open WebApp from Telegram client to send initData.";
    console.debug("No initData discovered by any method");
  }

  // run when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();