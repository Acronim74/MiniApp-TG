(function(){
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

  async function bootstrap() {
    // 1) Try Telegram.WebApp.initData (preferred)
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg && tg.initData) {
      const initData = tg.initData;
      // send to backend for verification
      const res = await postInitData(initData);
      if (res.ok && res.body && res.body.user) {
        showUser(res.body.user, res.body);
        return;
      } else {
        document.getElementById("response").textContent = "Verification failed: " + JSON.stringify(res);
      }
      return;
    }

    // 2) fallback: query params (only for quick local demo)
    try {
      const params = Object.fromEntries(new URLSearchParams(window.location.search));
      if (params.id) {
        const user = { id: params.id, username: params.username || params.user || "", auth_date: null };
        showUser(user, { ok: true, user });
        return;
      }
    } catch (e) {
      // ignore
    }

    document.getElementById("response").textContent = "No initData found. Open WebApp from Telegram client to send initData.";
  }

  bootstrap();
})();