// замените существующую функцию findInitDataFromUrl на эту
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
    // парсим хеш-параметры (#...)
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    // Telegram может положить данные в tgWebAppData (внешний браузер)
    const tgWebAppData = hashParams.get("tgWebAppData");
    if (tgWebAppData) {
      // tgWebAppData содержит закодированную строку вида "query_id=...&user=...&auth_date=...&hash=..."
      // декодируем её и вернём как подходящую init_data форму для бэкенда
      try {
        const decoded = decodeURIComponent(tgWebAppData);
        return decoded;
      } catch (e) {
        return tgWebAppData;
      }
    }
    if (hashParams.get("initData")) return hashParams.get("initData");
    if (hashParams.get("tgWebAppInitData")) return hashParams.get("tgWebAppInitData");
  } catch (e) {
    // ignore
  }
  return null;
}