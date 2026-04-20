/* Lori's Summon — Web Push worker for missed emergency acknowledgments */
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (err) {
    payload = {};
  }
  const title = payload.title || "Lori's Summon";
  const body = payload.body || "";
  const path = typeof payload.path === "string" ? payload.path : "/api/loris_summon/web";
  const icon = typeof payload.icon === "string" ? payload.icon : "";
  const tag = typeof payload.tag === "string" ? payload.tag : "loris-summon";
  const options = {
    body,
    icon,
    tag,
    requireInteraction: true,
    data: {
      path
    }
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const path = (event.notification.data && event.notification.data.path) || "/api/loris_summon/web";
  const url = new URL(path, self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({
      type: "window",
      includeUncontrolled: true
    }).then((clientList) => {
      for (const client of clientList) {
        if (client.url === url && "focus" in client) {
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(url);
      }
      return undefined;
    })
  );
});
