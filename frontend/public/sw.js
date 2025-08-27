// Service Worker for Code Tracker notifications
const CACHE_NAME = 'code-tracker-v1';

self.addEventListener('install', (event) => {
  console.log('Service Worker installing');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('Service Worker activating');
  event.waitUntil(self.clients.claim());
});

// Handle push notifications
self.addEventListener('push', (event) => {
  console.log('Push notification received', event);
  
  let notificationData = {};
  
  if (event.data) {
    try {
      notificationData = event.data.json();
    } catch (e) {
      notificationData = {
        title: 'Code Tracker Reminder',
        body: event.data.text() || 'Time to check your coding goals!',
        icon: '/favicon.ico',
        badge: '/favicon.ico'
      };
    }
  } else {
    notificationData = {
      title: 'Code Tracker Reminder',
      body: 'Time to check your coding goals!',
      icon: '/favicon.ico',
      badge: '/favicon.ico'
    };
  }
  
  const options = {
    body: notificationData.body,
    icon: notificationData.icon || '/favicon.ico',
    badge: notificationData.badge || '/favicon.ico',
    vibrate: [200, 100, 200],
    requireInteraction: true,
    actions: [
      {
        action: 'view',
        title: 'View Dashboard'
      },
      {
        action: 'dismiss',
        title: 'Dismiss'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(notificationData.title, options)
  );
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
  console.log('Notification clicked', event);
  
  event.notification.close();
  
  if (event.action === 'view') {
    // Open the app
    event.waitUntil(
      self.clients.openWindow('/')
    );
  }
  // 'dismiss' action just closes the notification
});

// Handle background sync (for offline functionality)
self.addEventListener('sync', (event) => {
  console.log('Background sync triggered', event);
  
  if (event.tag === 'check-coding-status') {
    event.waitUntil(
      // Here you could sync data when back online
      console.log('Syncing coding status...')
    );
  }
});

console.log('Code Tracker Service Worker loaded');