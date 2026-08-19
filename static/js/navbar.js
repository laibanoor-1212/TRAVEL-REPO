document.addEventListener('DOMContentLoaded', function () {
  const menuIcon = document.getElementById('menu-icon');
  const menu = document.getElementById('menu');

  // Mobile Hamburger Menu Click Toggle
  if (menuIcon && menu) {
    menuIcon.addEventListener('click', function (e) {
      e.stopPropagation();
      menu.classList.toggle('active');
    });
  }

  // Mobile Accordion Dropdowns
  const dropdowns = document.querySelectorAll('.dropdown');
  dropdowns.forEach((dropdown) => {
    dropdown.addEventListener('click', function (e) {
      if (window.innerWidth <= 991) {
        // Toggle mobile class for clicked dropdown
        this.classList.toggle('mobile-open');
      }
    });
  });

  // Close Menu on Outside Click
  document.addEventListener('click', function (e) {
    if (menu && menu.classList.contains('active')) {
      if (!menu.contains(e.target) && !menuIcon.contains(e.target)) {
        menu.classList.remove('active');
      }
    }
  });
});

// User Profile Menu Toggle Function (Matches onclick="toggleUserMenu()" in HTML)
function toggleUserMenu() {
  const userMenu = document.getElementById('userMenu');
  if (userMenu) {
    userMenu.classList.toggle('active');
  }
}

// Close User Dropdown on Outside Click
window.addEventListener('click', function (e) {
  const userMenu = document.getElementById('userMenu');
  const userWrap = document.querySelector('.user-profile-wrap');
  
  if (userMenu && userMenu.classList.contains('active')) {
    if (userWrap && !userWrap.contains(e.target)) {
      userMenu.classList.remove('active');
    }
  }
});