document.addEventListener('DOMContentLoaded', function () {
  const menuIcon = document.getElementById('menu-icon');
  const menu = document.getElementById('menu');

  // 1. Mobile Hamburger Menu Click Toggle
  if (menuIcon && menu) {
    menuIcon.addEventListener('click', function (e) {
      e.stopPropagation();
      menu.classList.toggle('active');
    });
  }

  // 2. Mobile Dropdowns - Strict Tap & Toggle Logic
  const dropdowns = document.querySelectorAll('.dropdown');

  dropdowns.forEach((dropdown) => {
    // Top-level <a> link inside dropdown (e.g., Guide, Packages)
    const mainLink = dropdown.querySelector('a');

    if (mainLink) {
      // Mobile screen check function
      const handleMobileDropdownToggle = function (e) {
        if (window.innerWidth <= 991) {
          const subMenu = dropdown.querySelector('.dropdown-menu');

          // Agar is item ke neeche dropdown menu majood hai
          if (subMenu) {
            // Page jump aur link navigation ko block karein
            e.preventDefault();
            e.stopPropagation();

            const isOpen = dropdown.classList.contains('mobile-open');

            // Pehle baaki saare open dropdowns ko band karein
            dropdowns.forEach((other) => {
              if (other !== dropdown) {
                other.classList.remove('mobile-open');
              }
            });

            // If pehle se open tha -> BAND KARO
            if (isOpen) {
              dropdown.classList.remove('mobile-open');
            } 
            // If band tha -> KHOLO
            else {
              dropdown.classList.add('mobile-open');
            }
          }
        }
      };

      // Direct click event listener
      mainLink.addEventListener('click', handleMobileDropdownToggle);
    }
  });

  // 3. Mobile par kisi khali jagah click karne par sab band kar do
  document.addEventListener('click', function (e) {
    if (window.innerWidth <= 991) {
      // Agar click menu ke andar nahi hua
      if (menu && !menu.contains(e.target) && menuIcon && !menuIcon.contains(e.target)) {
        menu.classList.remove('active');
        dropdowns.forEach((dropdown) => dropdown.classList.remove('mobile-open'));
      }
    }
  });
});

// User Profile Menu Toggle Function
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