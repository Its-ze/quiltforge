(() => {
  const isWindows = navigator.userAgent.includes('Windows');
  const primaryLinks = document.querySelectorAll('.download-link');
  primaryLinks.forEach((link) => {
    link.addEventListener('click', () => {
      try { localStorage.setItem('quiltforge-download', new Date().toISOString()); } catch (_) {}
    });
  });
  if (!isWindows) {
    primaryLinks.forEach((link) => {
      link.title = 'QuiltForge requires a 64-bit Windows 10 or Windows 11 computer';
    });
  }
})();

