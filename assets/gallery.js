/* ストア画像ギャラリー: サムネイルをクリックで拡大表示(左右キー・スワイプ・Escに対応) */
(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll('.store-gallery a.gallery-thumb'));
  if (!links.length || typeof HTMLDialogElement === 'undefined') return;
  var dlg = document.createElement('dialog');
  dlg.className = 'gallery-dialog';
  dlg.setAttribute('aria-label', '画像の拡大表示');
  dlg.innerHTML =
    '<div class="gallery-stage"><img alt="">' +
    '<button type="button" class="gallery-btn gallery-close" aria-label="閉じる">&times;</button>' +
    '<button type="button" class="gallery-btn gallery-prev" aria-label="前の画像">&#8249;</button>' +
    '<button type="button" class="gallery-btn gallery-next" aria-label="次の画像">&#8250;</button>' +
    '<div class="gallery-count" aria-live="polite"></div></div>';
  document.body.appendChild(dlg);
  var img = dlg.querySelector('img'), count = dlg.querySelector('.gallery-count'), cur = 0;
  function show(i) {
    cur = (i + links.length) % links.length;
    var a = links[cur], t = a.querySelector('img');
    img.src = a.getAttribute('href');
    img.alt = t ? t.alt : '';
    count.textContent = (cur + 1) + ' / ' + links.length;
  }
  links.forEach(function (a, i) {
    a.addEventListener('click', function (e) { e.preventDefault(); show(i); dlg.showModal(); });
  });
  dlg.querySelector('.gallery-close').addEventListener('click', function () { dlg.close(); });
  dlg.querySelector('.gallery-prev').addEventListener('click', function () { show(cur - 1); });
  dlg.querySelector('.gallery-next').addEventListener('click', function () { show(cur + 1); });
  dlg.addEventListener('click', function (e) { if (e.target === dlg || e.target.classList.contains('gallery-stage')) dlg.close(); });
  dlg.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') show(cur - 1);
    if (e.key === 'ArrowRight') show(cur + 1);
  });
  var x0 = null;
  dlg.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; }, { passive: true });
  dlg.addEventListener('touchend', function (e) {
    if (x0 === null) return;
    var dx = e.changedTouches[0].clientX - x0; x0 = null;
    if (Math.abs(dx) > 50) show(dx < 0 ? cur + 1 : cur - 1);
  }, { passive: true });
})();
