/**
 * app.js - Navegación y Lógica UI RehabBot v1.0
 */

let currentScreenId = 'screen_splash';

// Navegación con animaciones
function navTo(screenId, direction = 'push') {
    if (currentScreenId === screenId) return;

    const currentScreen = document.getElementById(currentScreenId);
    const targetScreen = document.getElementById(screenId);
    
    if (!targetScreen) return;

    // Limpiar clases de animación previas
    currentScreen.className = currentScreen.className.replace(/slide-left-enter|slide-left-exit|slide-right-enter|slide-right-exit/g, '').trim();
    targetScreen.className = targetScreen.className.replace(/slide-left-enter|slide-left-exit|slide-right-enter|slide-right-exit/g, '').trim();

    // Aplicar nuevas clases
    if (direction === 'push') {
        currentScreen.classList.add('slide-left-exit');
        targetScreen.classList.add('active', 'slide-left-enter');
    } else if (direction === 'pop') {
        currentScreen.classList.add('slide-right-exit');
        targetScreen.classList.add('active', 'slide-right-enter');
    } else {
        // Tab (sin animación lateral)
        currentScreen.classList.remove('active');
        targetScreen.classList.add('active');
    }

    // Al finalizar animación
    setTimeout(() => {
        if (direction !== 'tab') {
            currentScreen.classList.remove('active', 'slide-left-exit', 'slide-right-exit');
            targetScreen.classList.remove('slide-left-enter', 'slide-right-enter');
        }
    }, 320);

    currentScreenId = screenId;
    closeMenu();
    closeSOSModal();
}

// Menú Hamburguesa (Drawer) con Stagger
function openMenu() {
    const overlay = document.getElementById('drawer_overlay');
    const panel = document.getElementById('drawer_panel');
    const listItems = panel.querySelectorAll('.drawer-list li');
    
    overlay.classList.add('active');
    
    // Animación de entrada del panel
    setTimeout(() => {
        panel.classList.add('open');
        
        // Stagger de ítems (50ms entre cada uno)
        listItems.forEach((li, index) => {
            li.style.transition = `transform 0.25s ease-out ${index * 0.05}s, opacity 0.25s ease-out ${index * 0.05}s`;
            li.style.opacity = '1';
            li.style.transform = 'translateX(0)';
        });
    }, 10);
}

function closeMenu() {
    const overlay = document.getElementById('drawer_overlay');
    const panel = document.getElementById('drawer_panel');
    const listItems = panel.querySelectorAll('.drawer-list li');
    
    panel.classList.remove('open');
    
    // Resetear estilos de los ítems
    listItems.forEach(li => {
        li.style.transition = 'none';
        li.style.opacity = '0';
        li.style.transform = 'translateX(-30px)';
    });
    
    setTimeout(() => {
        overlay.classList.remove('active');
    }, 300);
}

// Modal SOS Global
function openSOSModal() {
    if (navigator.vibrate) navigator.vibrate([300, 100, 300, 100]); // Haptic
    
    const modal = document.getElementById('modal_sos');
    const textAlert = modal.querySelector('h2');
    
    modal.classList.add('active');
    textAlert.classList.add('sos-blink'); // Añade animación blink
}

function closeSOSModal() {
    const modal = document.getElementById('modal_sos');
    modal.classList.remove('active');
}

// Sistema de Toasts (Notificaciones)
function showToast(message, isError = false) {
    let toast = document.getElementById('app-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'app-toast';
        toast.className = 'toast-container';
        document.body.appendChild(toast);
    }
    
    toast.textContent = message;
    if (isError) toast.classList.add('error');
    else toast.classList.remove('error');
    
    toast.classList.add('show');
    
    // Vibración haptic dependiente de si es error
    if (navigator.vibrate) navigator.vibrate(isError ? [100, 50, 100] : [50]);

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Login Validador
function doLogin(btn) {
    const loginScreen = document.getElementById('screen_login');
    const inputs = loginScreen.querySelectorAll('input');
    const email = inputs[0].value;
    const pwd = inputs[1].value;
    
    // Validar Email básico
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    let hasError = false;
    
    if (!emailRegex.test(email)) {
        inputs[0].parentElement.classList.add('error', 'shake');
        setTimeout(() => inputs[0].parentElement.classList.remove('shake'), 400);
        hasError = true;
    } else {
        inputs[0].parentElement.classList.remove('error');
    }
    
    if (pwd.length < 6) {
        inputs[1].parentElement.classList.add('error', 'shake');
        setTimeout(() => inputs[1].parentElement.classList.remove('shake'), 400);
        hasError = true;
    } else {
        inputs[1].parentElement.classList.remove('error');
    }
    
    if (hasError) {
        showToast("Revisa los campos en rojo", true);
        return;
    }
    
    // Simular Carga
    const originalText = btn.textContent;
    btn.innerHTML = '<span class="spinner"></span>';
    
    setTimeout(() => {
        btn.innerHTML = originalText;
        navTo('screen_home_logged', 'push');
        
        // Reset inputs
        inputs[0].value = '';
        inputs[1].value = '';
    }, 1000);
}

// Inicialización de Animaciones Splash
function initSplash() {
    const splash = document.getElementById('screen_splash');
    if (!splash) return;
    
    splash.querySelector('.header-curvo').classList.add('splash-header');
    splash.querySelector('.fa-robot').parentElement.classList.add('splash-logo');
    splash.querySelector('.p-24').classList.add('splash-text');
    splash.querySelector('.btn').parentElement.classList.add('splash-btns');
}

// Añadir función a los botones HTML
document.addEventListener('DOMContentLoaded', () => {
    // Configurar Splash
    initSplash();
    
    // Actualizar botón de Iniciar Sesión en index.html dinámicamente para que llame doLogin()
    const loginBtn = document.querySelector('#screen_login .btn-primary');
    if (loginBtn) {
        loginBtn.onclick = function() { doLogin(this); };
    }
    
    // Toggle Password Visibility
    const eyeIcons = document.querySelectorAll('.fa-eye');
    eyeIcons.forEach(icon => {
        icon.addEventListener('click', function() {
            const input = this.previousElementSibling;
            if (input.type === 'password') {
                input.type = 'text';
                this.classList.replace('fa-eye', 'fa-eye-slash');
            } else {
                input.type = 'password';
                this.classList.replace('fa-eye-slash', 'fa-eye');
            }
        });
    });
});
