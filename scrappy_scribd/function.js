// ====== Local Storage Caching ======
function saveImageToCache(key, data) {
  const cacheData = { timestamp: Date.now(), data };
  localStorage.setItem(key, JSON.stringify(cacheData));
}


