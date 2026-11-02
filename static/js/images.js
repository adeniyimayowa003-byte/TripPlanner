/* Image failure affects only the photograph; all planning actions stay usable. */
(() => {
  document.querySelectorAll('img[data-travel-image]').forEach((image) => {
    const showFallback = () => { image.hidden = true; };
    image.addEventListener('error', showFallback);
    // A cached failure can happen before this deferred script is loaded.
    if (image.complete && image.naturalWidth === 0) showFallback();
  });
})();
