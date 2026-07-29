/**
 * main.js – StegoCloud Client-Side JavaScript
 * Steganography-Based Cloud Data Protection System
 *
 * Handles:
 *   - Sidebar toggle (responsive)
 *   - Auto-dismiss flash alerts
 *   - Active nav link highlighting
 *   - Smooth scroll utility
 */

/* ── DOMContentLoaded wrapper ─────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {

  /* ── 1. Sidebar toggle (mobile) ─────────────────────────────────────────── */
  const toggleBtn = document.getElementById('sidebarToggle');
  const sidebar   = document.getElementById('sidebar');
  const mainContent = document.getElementById('mainContent');

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', function () {
      sidebar.classList.toggle('open');

      // On desktop, shrink main content instead
      if (window.innerWidth > 768) {
        sidebar.classList.toggle('collapsed');
        if (mainContent) {
          mainContent.classList.toggle('expanded');
        }
      }
    });

    // Close sidebar on outside click (mobile)
    document.addEventListener('click', function (e) {
      if (
        window.innerWidth <= 768 &&
        sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !toggleBtn.contains(e.target)
      ) {
        sidebar.classList.remove('open');
      }
    });
  }

  /* ── 2. Auto-dismiss flash alerts after 5 seconds ───────────────────────── */
  const alerts = document.querySelectorAll('.alert.flash-slide');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.classList.remove('show');
      alert.style.transition = 'opacity .5s ease';
      alert.style.opacity = '0';
      setTimeout(function () { alert.remove(); }, 500);
    }, 5000);
  });

  /* ── 3. Active nav link pulse on click ──────────────────────────────────── */
  document.querySelectorAll('.sidebar-nav .nav-link').forEach(function (link) {
    link.addEventListener('click', function () {
      document.querySelectorAll('.sidebar-nav .nav-link').forEach(l => l.classList.remove('active'));
      this.classList.add('active');
    });
  });

  /* ── 4. Animate stat card numbers (count-up) ────────────────────────────── */
  function countUp(el, target, duration) {
    let start = 0;
    const step = target / (duration / 16);
    const timer = setInterval(function () {
      start += step;
      if (start >= target) { start = target; clearInterval(timer); }
      el.textContent = Math.round(start);
    }, 16);
  }

  document.querySelectorAll('.stat-card-num').forEach(function (el) {
    const val = parseInt(el.textContent.trim(), 10);
    if (!isNaN(val) && val > 0) {
      el.textContent = '0';
      // Only animate numeric values (skip strings like "MFA: Enabled")
      const observer = new IntersectionObserver(function (entries) {
        if (entries[0].isIntersecting) {
          countUp(el, val, 800);
          observer.disconnect();
        }
      });
      observer.observe(el);
    }
  });

  /* ── 5. Smooth fade-in for page content ─────────────────────────────────── */
  const pageContent = document.querySelector('.page-content');
  if (pageContent) {
    pageContent.style.opacity = '0';
    pageContent.style.transform = 'translateY(10px)';
    requestAnimationFrame(function () {
      pageContent.style.transition = 'opacity .4s ease, transform .4s ease';
      pageContent.style.opacity    = '1';
      pageContent.style.transform  = 'translateY(0)';
    });
  }

  /* ── 6. Glowing submit button pulse on hover ─────────────────────────────── */
  document.querySelectorAll('.btn-primary-glow').forEach(function (btn) {
    btn.addEventListener('mouseenter', function () {
      this.style.boxShadow = '0 0 28px rgba(0,212,255,.55)';
    });
    btn.addEventListener('mouseleave', function () {
      this.style.boxShadow = '';
    });
  });

  /* ── 7. Table row click-to-highlight ────────────────────────────────────── */
  document.querySelectorAll('.sc-table tbody tr').forEach(function (row) {
    row.addEventListener('click', function () {
      document.querySelectorAll('.sc-table tbody tr').forEach(r => r.classList.remove('row-selected'));
      this.classList.add('row-selected');
    });
  });

  /* ── 8. Tooltip init (Bootstrap) ────────────────────────────────────────── */
  if (typeof bootstrap !== 'undefined') {
    var tooltipEls = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipEls.forEach(function (el) {
      new bootstrap.Tooltip(el, { trigger: 'hover' });
    });
  }

  /* ── 9. Form input glow on focus ────────────────────────────────────────── */
  document.querySelectorAll('.sc-input').forEach(function (input) {
    input.addEventListener('focus', function () {
      this.parentElement.style.position = 'relative';
    });
  });

  /* ── 10. Keyboard shortcut: Escape closes sidebar on mobile ─────────────── */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && sidebar && sidebar.classList.contains('open')) {
      sidebar.classList.remove('open');
    }
  });

});

/* ── Global helper: toggle password visibility ──────────────────────────── */
window.togglePassword = function (inputId) {
  var el  = document.getElementById(inputId);
  var eye = document.querySelector('[onclick*="' + inputId + '"] i');
  if (!el) return;
  if (el.type === 'password') {
    el.type = 'text';
    if (eye) eye.className = 'bi bi-eye-slash';
  } else {
    el.type = 'password';
    if (eye) eye.className = 'bi bi-eye';
  }
};
