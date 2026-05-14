document.addEventListener('DOMContentLoaded', () => {
    const splash = document.querySelector('.splash');

    if (splash) {
        setTimeout(() => {
            // 1. Pehle class add hogi transition shuru karne ke liye
            splash.classList.add('display-none');
            
            // 2. Transition khatam hone par element ko 'none' kar dena taake niche click ho sakay
            splash.addEventListener('transitionend', () => {
                splash.style.display = 'none';
            });
        }, 2000); // 2 seconds baad shuru hoga
    }
});