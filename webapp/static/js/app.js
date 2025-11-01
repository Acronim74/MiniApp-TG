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
      const qs = new URLSearchParams(window.location.search);
      if (qs.get("initData")) return qs.get("initData");
      if (qs.get("tgWebAppInitData")) return qs.get("tgWebAppInitData");
      if (qs.get("init_data")) return qs.get("init_data");
    } catch (e) {
      // ignore
    }
    try {
      const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
      if (hashParams.get("initData")) return hashParams.get("initData");
      if (hashParams.get("tgWebAppInitData")) return hashParams.get("tgWebAppInitData");
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

    // 3) fallback: query/hash params (only for quick local demo or non-standard clients)
    const qpInit = findInitDataFromUrl();
    if (qpInit) {
      console.debug("Found initData in URL (fallback)");
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

  bootstrap();
})();