// Innerspeak — interactions: image slots, reveal-on-scroll, slider, mobile nav

// ---- Image slots: load each photo if present; keep the elegant placeholder if not ----
document.querySelectorAll('.img-slot').forEach(function (slot) {
  var file = slot.dataset.photo;
  if (!file) return;
  var img = document.createElement('img');
  img.alt = slot.dataset.alt || '';
  img.onerror = function () { img.remove(); }; // photo missing → styled placeholder stays
  img.src = 'images/' + file;
  slot.appendChild(img);
});

// ---- Reveal on scroll ----
var observer = new IntersectionObserver(function (entries) {
  entries.forEach(function (entry) {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });
document.querySelectorAll('.reveal').forEach(function (el) { observer.observe(el); });

// ---- Testimonial slider ----
(function () {
  var track = document.getElementById('sliderTrack');
  var dotsWrap = document.getElementById('sliderDots');
  if (!track || !dotsWrap) return;
  var quotes = track.children.length;
  var index = 0;
  var timer;

  for (var i = 0; i < quotes; i++) {
    var dot = document.createElement('button');
    dot.setAttribute('aria-label', 'Testimonial ' + (i + 1));
    dot.dataset.index = i;
    dot.addEventListener('click', function () {
      go(parseInt(this.dataset.index, 10));
      restart();
    });
    dotsWrap.appendChild(dot);
  }

  function go(i) {
    index = i;
    track.style.transform = 'translateX(-' + i * 100 + '%)';
    Array.prototype.forEach.call(dotsWrap.children, function (d, j) {
      d.classList.toggle('active', j === i);
    });
  }
  function next() { go((index + 1) % quotes); }
  function restart() {
    clearInterval(timer);
    timer = setInterval(next, 6000);
  }
  go(0);
  restart();
})();

// ---- Mobile nav ----
var toggle = document.getElementById('navToggle');
var links = document.getElementById('navLinks');
if (toggle && links) {
  toggle.addEventListener('click', function () {
    var open = links.classList.toggle('open');
    toggle.setAttribute('aria-expanded', open);
  });
  links.querySelectorAll('a').forEach(function (a) {
    a.addEventListener('click', function () { links.classList.remove('open'); });
  });
}

// ---- Footer year ----
var year = document.getElementById('year');
if (year) year.textContent = new Date().getFullYear();
