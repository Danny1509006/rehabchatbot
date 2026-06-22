/**
 * app.js - Lógica Frontend y Conexión con FastAPI RehabBot v2.0
 */

const API_BASE_URL = 'http://localhost:8000/api';
let currentUser = null;
let currentScreenId = 'screen_splash';

// Cargar sesión del usuario al iniciar la página
document.addEventListener('DOMContentLoaded', () => {
    initSplash();
    checkActiveSession();

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

    // Configurar Eventos del Chat
    const chatInput = document.getElementById('chat_input');
    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }
});

// Comprobar si hay un usuario logueado en localStorage
function checkActiveSession() {
    const sessionData = localStorage.getItem('currentUser');
    if (sessionData) {
        try {
            currentUser = JSON.parse(sessionData);
            updateUserUIElements();
            navTo('screen_home_logged', 'tab');
            loadChatHistory();
            loadSOSContacts();
            loadMoodHistory();
        } catch (e) {
            console.error("Error al cargar la sesión activa:", e);
            localStorage.removeItem('currentUser');
        }
    }
}

// Actualizar los elementos de la interfaz con los datos del usuario logueado
function updateUserUIElements() {
    if (!currentUser) return;
    
    const fullName = `${currentUser.name} ${currentUser.lastname}`;
    
    // Sidebar escritorio
    document.getElementById('sidebar_username').textContent = fullName;
    document.getElementById('sidebar_email').textContent = currentUser.email;
    
    // Drawer móvil
    document.getElementById('drawer_username').textContent = fullName;
    document.getElementById('drawer_email').textContent = currentUser.email;
    
    // Pantalla de Home
    document.getElementById('home_greeting').textContent = `Hola, ${currentUser.name} 👋`;
    
    // Pantalla de Perfil
    document.getElementById('profile_fullname').textContent = fullName;
    document.getElementById('profile_name').textContent = currentUser.name;
    document.getElementById('profile_lastname').textContent = currentUser.lastname;
    document.getElementById('profile_email').textContent = currentUser.email;
}

// Navegación con animaciones adaptada para el sidebar de escritorio
function navTo(screenId, direction = 'push') {
    if (currentScreenId === screenId) return;

    const currentScreen = document.getElementById(currentScreenId);
    const targetScreen = document.getElementById(screenId);
    
    if (!targetScreen) return;

    // Control del layout responsivo: Ocultar o mostrar el sidebar de escritorio
    const guestScreens = ['screen_splash', 'screen_login', 'screen_register'];
    const appContainer = document.querySelector('.app-container');
    if (guestScreens.includes(screenId)) {
        appContainer.classList.remove('user-logged-in');
    } else {
        appContainer.classList.add('user-logged-in');
        updateUserUIElements();
    }

    // Resaltar la pestaña correcta en el menú lateral (sidebar)
    updateSidebarActiveState(screenId);

    // Limpiar clases de animación previas
    currentScreen.className = currentScreen.className.replace(/slide-left-enter|slide-left-exit|slide-right-enter|slide-right-exit/g, '').trim();
    targetScreen.className = targetScreen.className.replace(/slide-left-enter|slide-left-exit|slide-right-enter|slide-right-exit/g, '').trim();

    // Aplicar nuevas clases en función de la dirección de navegación
    if (direction === 'push') {
        currentScreen.classList.add('slide-left-exit');
        targetScreen.classList.add('active', 'slide-left-enter');
    } else if (direction === 'pop') {
        currentScreen.classList.add('slide-right-exit');
        targetScreen.classList.add('active', 'slide-right-enter');
    } else {
        // Tab (sin animación)
        currentScreen.classList.remove('active');
        targetScreen.classList.add('active');
    }

    // Resetear clases temporales al finalizar la animación
    setTimeout(() => {
        if (direction !== 'tab') {
            currentScreen.classList.remove('active', 'slide-left-exit', 'slide-right-exit');
            targetScreen.classList.remove('slide-left-enter', 'slide-right-enter');
        }
    }, 320);

    currentScreenId = screenId;
    
    // Sincronizar elementos activos en bottom-nav móvil
    updateBottomNavActiveState(screenId);

    closeMenu();
    closeSOSModal();
}

// Resalta la opción seleccionada en el menú lateral de escritorio
function updateSidebarActiveState(screenId) {
    const menuMapping = {
        'screen_home_logged': 'menu_home',
        'screen_chat': 'menu_chat',
        'screen_map_1': 'menu_map',
        'screen_add_sos_contact': 'menu_sos',
        'screen_terms': 'menu_terms'
    };

    document.querySelectorAll('.sidebar-menu li').forEach(li => li.classList.remove('active'));
    
    const activeMenuId = menuMapping[screenId];
    if (activeMenuId) {
        const activeLi = document.getElementById(activeMenuId);
        if (activeLi) activeLi.classList.add('active');
    }
}

// Sincroniza la opción seleccionada en la barra de navegación móvil
function updateBottomNavActiveState(screenId) {
    document.querySelectorAll('.bottom-nav .nav-item').forEach(item => item.classList.remove('active'));
    
    let index = -1;
    if (screenId === 'screen_home_logged') index = 1;
    else if (screenId === 'screen_chat') index = 2;
    
    if (index !== -1) {
        const activeItem = document.querySelectorAll('.bottom-nav .nav-item')[index];
        if (activeItem) activeItem.classList.add('active');
    }
}

// Menú Hamburguesa Drawer (Móvil)
function openMenu() {
    const overlay = document.getElementById('drawer_overlay');
    const panel = document.getElementById('drawer_panel');
    const listItems = panel.querySelectorAll('.drawer-list li');
    
    overlay.classList.add('active');
    
    setTimeout(() => {
        panel.classList.add('open');
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
    if (navigator.vibrate) navigator.vibrate([300, 100, 300, 100]);
    const modal = document.getElementById('modal_sos');
    modal.classList.add('active');
    modal.querySelector('h2').classList.add('sos-blink');
}

function closeSOSModal() {
    const modal = document.getElementById('modal_sos');
    modal.classList.remove('active');
}

function callSOSNumber() {
    showToast("Simulando llamada de emergencia...", false);
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
    
    if (navigator.vibrate) navigator.vibrate(isError ? [100, 50, 100] : [50]);

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// ==========================================
// CONEXIÓN CON EL BACKEND FASTAPI
// ==========================================

// Registrar nuevo usuario
async function doRegister(btn) {
    const name = document.getElementById('register_name').value.trim();
    const lastname = document.getElementById('register_lastname').value.trim();
    const email = document.getElementById('register_email').value.trim();
    const password = document.getElementById('register_password').value.trim();
    const confirmPassword = document.getElementById('register_confirm_password').value.trim();
    const termsChecked = document.getElementById('terms').checked;

    let hasError = false;

    if (!name) {
        document.getElementById('register_name').parentElement.classList.add('error', 'shake');
        setTimeout(() => document.getElementById('register_name').parentElement.classList.remove('shake'), 400);
        hasError = true;
    } else {
        document.getElementById('register_name').parentElement.classList.remove('error');
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        document.getElementById('register_email').parentElement.classList.add('error', 'shake');
        setTimeout(() => document.getElementById('register_email').parentElement.classList.remove('shake'), 400);
        hasError = true;
    } else {
        document.getElementById('register_email').parentElement.classList.remove('error');
    }

    if (password.length < 6) {
        document.getElementById('register_password').parentElement.classList.add('error', 'shake');
        setTimeout(() => document.getElementById('register_password').parentElement.classList.remove('shake'), 400);
        hasError = true;
    } else {
        document.getElementById('register_password').parentElement.classList.remove('error');
    }

    if (password !== confirmPassword) {
        document.getElementById('register_confirm_password').parentElement.classList.add('error', 'shake');
        setTimeout(() => document.getElementById('register_confirm_password').parentElement.classList.remove('shake'), 400);
        hasError = true;
    } else {
        document.getElementById('register_confirm_password').parentElement.classList.remove('error');
    }

    if (!termsChecked) {
        showToast("Debes aceptar los Términos y Condiciones", true);
        return;
    }

    if (hasError) {
        showToast("Revisa los campos en rojo", true);
        return;
    }

    // Enviar al Backend
    const originalText = btn.textContent;
    btn.innerHTML = '<span class="spinner"></span>';

    try {
        const response = await fetch(`${API_BASE_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, lastname, email, password })
        });

        const data = await response.json();

        if (response.ok) {
            showToast("¡Cuenta creada con éxito! Por favor inicia sesión.");
            // Limpiar inputs
            document.getElementById('register_name').value = '';
            document.getElementById('register_lastname').value = '';
            document.getElementById('register_email').value = '';
            document.getElementById('register_password').value = '';
            document.getElementById('register_confirm_password').value = '';
            document.getElementById('terms').checked = false;
            navTo('screen_login', 'pop');
        } else {
            showToast(data.detail || "Error en el registro de usuario", true);
        }
    } catch (error) {
        console.error("Error al registrarse:", error);
        showToast("Error de conexión con el backend", true);
    } finally {
        btn.innerHTML = originalText;
    }
}

// Iniciar sesión
async function doLogin(btn) {
    const email = document.getElementById('login_email').value.trim();
    const password = document.getElementById('login_password').value.trim();

    let hasError = false;

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        document.getElementById('login_email').parentElement.classList.add('error', 'shake');
        setTimeout(() => document.getElementById('login_email').parentElement.classList.remove('shake'), 400);
        hasError = true;
    } else {
        document.getElementById('login_email').parentElement.classList.remove('error');
    }

    if (password.length < 6) {
        document.getElementById('login_password').parentElement.classList.add('error', 'shake');
        setTimeout(() => document.getElementById('login_password').parentElement.classList.remove('shake'), 400);
        hasError = true;
    } else {
        document.getElementById('login_password').parentElement.classList.remove('error');
    }

    if (hasError) {
        showToast("Datos de inicio de sesión inválidos", true);
        return;
    }

    // Enviar al Backend
    const originalText = btn.textContent;
    btn.innerHTML = '<span class="spinner"></span>';

    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok && data.user) {
            currentUser = data.user;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            updateUserUIElements();
            
            // Cargar datos del usuario
            loadChatHistory();
            loadSOSContacts();
            loadMoodHistory();

            showToast(`¡Bienvenido/a de nuevo, ${currentUser.name}!`);
            
            // Limpiar inputs
            document.getElementById('login_email').value = '';
            document.getElementById('login_password').value = '';

            navTo('screen_home_logged', 'push');
        } else {
            showToast(data.detail || "Credenciales incorrectas", true);
        }
    } catch (error) {
        console.error("Error al iniciar sesión:", error);
        showToast("Error de conexión con el backend", true);
    } finally {
        btn.innerHTML = originalText;
    }
}

// Cerrar sesión
function doLogout() {
    currentUser = null;
    localStorage.removeItem('currentUser');
    
    // Limpiar burbujas del contenedor de chat
    const chatContainer = document.getElementById('chat_container');
    if (chatContainer) {
        chatContainer.innerHTML = `
            <div style="background-color: #FCE4EC; color: var(--c-text-main); align-self: flex-start; padding: 12px 16px; border-radius: 18px 18px 18px 0; max-width: 80%; font-size: 13px; line-height: 1.4; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                Hola 👋 Soy RehabBot. Estoy aquí para apoyarte en tu proceso de recuperación. ¿En qué puedo ayudarte hoy?
            </div>
        `;
    }

    showToast("Sesión cerrada correctamente");
    navTo('screen_splash', 'pop');
}

// Cargar Historial de Chat del usuario logueado
async function loadChatHistory() {
    if (!currentUser) return;
    
    const chatContainer = document.getElementById('chat_container');
    if (!chatContainer) return;

    try {
        const response = await fetch(`${API_BASE_URL}/chat/history?user_id=${currentUser.id}`);
        if (response.ok) {
            const history = await response.json();
            
            // Resetear chat container y poner burbuja inicial
            chatContainer.innerHTML = `
                <div style="background-color: #FCE4EC; color: var(--c-text-main); align-self: flex-start; padding: 12px 16px; border-radius: 18px 18px 18px 0; max-width: 80%; font-size: 13px; line-height: 1.4; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                    Hola 👋 Soy RehabBot. Estoy aquí para apoyarte en tu proceso de recuperación. ¿En qué puedo ayudarte hoy?
                </div>
            `;
            
            // Agregar burbujas recuperadas
            history.forEach(msg => {
                appendChatBubble(msg.message_text, msg.sender);
            });
            
            scrollToBottom(chatContainer);
        }
    } catch (error) {
        console.error("Error al cargar historial de chat:", error);
    }
}

// Enviar un mensaje de chat y guardarlo en base de datos
async function sendChatMessage() {
    if (!currentUser) {
        showToast("Debes iniciar sesión para chatear", true);
        return;
    }

    const chatInput = document.getElementById('chat_input');
    const chatContainer = document.getElementById('chat_container');
    const messageText = chatInput.value.trim();

    if (!messageText) return;

    chatInput.value = '';

    // Agregar mensaje del usuario a la pantalla
    appendChatBubble(messageText, 'user');
    scrollToBottom(chatContainer);

    // Mostrar indicador de escritura
    const typingIndicator = showTypingIndicator(chatContainer);
    scrollToBottom(chatContainer);

    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser.id, message: messageText })
        });

        const data = await response.json();
        typingIndicator.remove();

        if (response.ok && data.response) {
            appendChatBubble(data.response, 'bot');
        } else {
            appendChatBubble("Lo siento, hubo un problema al obtener la respuesta del bot.", 'bot');
        }
    } catch (error) {
        console.error("Error en chat:", error);
        typingIndicator.remove();
        appendChatBubble("Error de comunicación. Asegúrate de que el backend de RehabBot esté activo.", 'bot');
    }
    
    scrollToBottom(chatContainer);
}

// Cargar contactos SOS
async function loadSOSContacts() {
    if (!currentUser) return;

    const listContainer = document.getElementById('sos_contacts_list');
    const modalContainer = document.getElementById('sos_modal_contacts');
    
    try {
        const response = await fetch(`${API_BASE_URL}/sos-contacts?user_id=${currentUser.id}`);
        if (response.ok) {
            const contacts = await response.json();
            
            // Vaciar contenedores
            listContainer.innerHTML = '';
            modalContainer.innerHTML = '';
            
            if (contacts.length === 0) {
                listContainer.innerHTML = '<p class="body-text text-center" style="color: var(--c-text-sec);">No tienes contactos registrados.</p>';
                modalContainer.innerHTML = '<p class="body-text text-center" style="color: var(--c-alert);">Sin contactos configurados.</p>';
                return;
            }

            contacts.forEach(contact => {
                // Agregar a la lista de administración
                const contactCard = document.createElement('div');
                contactCard.className = 'card';
                contactCard.style.cssText = 'padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; border: 1.5px solid var(--c-border); margin-bottom: 8px;';
                contactCard.innerHTML = `
                    <div>
                        <h4 style="font-size: 13px; font-weight: 600; color: var(--c-primary);">${contact.name} (${contact.relationship || 'Apoyo'})</h4>
                        <p style="font-size: 11px; color: var(--c-text-sec);">${contact.phone}</p>
                    </div>
                    <i class="fa-solid fa-phone" style="color: var(--c-light); font-size: 16px;"></i>
                `;
                listContainer.appendChild(contactCard);

                // Agregar al modal de marcación SOS
                const phoneButton = document.createElement('a');
                phoneButton.href = `tel:${contact.phone}`;
                phoneButton.className = 'btn btn-outline';
                phoneButton.style.cssText = 'border-color: var(--c-alert); color: var(--c-alert); text-decoration: none; padding: 12px 24px; font-size: 13px; display: flex; align-items: center; justify-content: center; gap: 8px;';
                phoneButton.innerHTML = `<i class="fa-solid fa-phone"></i> Llamar a ${contact.name}`;
                modalContainer.appendChild(phoneButton);
            });
        }
    } catch (error) {
        console.error("Error al cargar contactos SOS:", error);
    }
}

// Guardar contacto SOS
async function saveSOSContact(btn) {
    if (!currentUser) return;

    const nameInput = document.getElementById('sos_contact_name');
    const phoneInput = document.getElementById('sos_contact_phone');
    const relInput = document.getElementById('sos_contact_relationship');

    const name = nameInput.value.trim();
    const phone = phoneInput.value.trim();
    const relationship = relInput.value.trim();

    if (!name || !phone) {
        showToast("Nombre y teléfono son campos obligatorios", true);
        return;
    }

    const originalText = btn.textContent;
    btn.innerHTML = '<span class="spinner"></span>';

    try {
        const response = await fetch(`${API_BASE_URL}/sos-contacts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.id,
                name: name,
                phone: phone,
                relationship: relationship
            })
        });

        if (response.ok) {
            showToast("Contacto SOS guardado con éxito");
            nameInput.value = '';
            phoneInput.value = '';
            relInput.value = '';
            loadSOSContacts();
        } else {
            const data = await response.json();
            showToast(data.detail || "Error al guardar contacto", true);
        }
    } catch (error) {
        console.error("Error al guardar contacto SOS:", error);
        showToast("Error de comunicación con el servidor", true);
    } finally {
        btn.innerHTML = originalText;
    }
}

// Guardar estado de ánimo diario
async function saveMood(emoji) {
    if (!currentUser) return;

    try {
        const response = await fetch(`${API_BASE_URL}/moods`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.id,
                mood_emoji: emoji
            })
        });

        if (response.ok) {
            showToast(`Estado de ánimo '${emoji}' guardado.`);
            loadMoodHistory();
        } else {
            showToast("No se pudo guardar el estado de ánimo", true);
        }
    } catch (error) {
        console.error("Error al guardar mood:", error);
    }
}

// Cargar historial de estado de ánimo
async function loadMoodHistory() {
    if (!currentUser) return;

    const historyContainer = document.getElementById('mood_history');
    if (!historyContainer) return;

    try {
        const response = await fetch(`${API_BASE_URL}/moods?user_id=${currentUser.id}`);
        if (response.ok) {
            const moods = await response.json();
            if (moods.length > 0) {
                const latest = moods[0];
                const dateObj = new Date(latest.timestamp);
                const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                historyContainer.innerHTML = `Último estado registrado: <strong style="font-size: 16px;">${latest.mood_emoji}</strong> hoy a las ${timeStr}`;
            } else {
                historyContainer.innerHTML = 'Aún no registras estados de ánimo hoy.';
            }
        }
    } catch (error) {
        console.error("Error al cargar historial de moods:", error);
    }
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

// Renderizar burbujas en el contenedor de chat
function appendChatBubble(text, sender) {
    const chatContainer = document.getElementById('chat_container');
    const bubble = document.createElement('div');
    
    if (sender === 'user') {
        bubble.style.cssText = 'background-color: var(--c-primary); color: white; align-self: flex-end; padding: 12px 16px; border-radius: 18px 18px 0 18px; max-width: 80%; font-size: 13px; line-height: 1.4; box-shadow: 0 1px 2px rgba(0,0,0,0.1); margin-top: 8px; word-break: break-word;';
    } else {
        bubble.style.cssText = 'background-color: #FCE4EC; color: var(--c-text-main); align-self: flex-start; padding: 12px 16px; border-radius: 18px 18px 18px 0; max-width: 80%; font-size: 13px; line-height: 1.4; box-shadow: 0 1px 2px rgba(0,0,0,0.1); margin-top: 8px; word-break: break-word;';
    }
    
    bubble.innerHTML = text.replace(/\n/g, '<br>');
    chatContainer.appendChild(bubble);
}

// Renderizar el indicador de escritura (Cargando respuesta...)
function showTypingIndicator(chatContainer) {
    const indicator = document.createElement('div');
    indicator.style.cssText = 'background-color: #E0E0E0; color: var(--c-text-main); align-self: flex-start; padding: 12px 16px; border-radius: 18px 18px 18px 0; font-size: 18px; letter-spacing: 2px; margin-top: 8px;';
    indicator.innerHTML = '<span style="color: #757575;">● ● ●</span>';
    chatContainer.appendChild(indicator);
    return indicator;
}

function scrollToBottom(container) {
    container.scrollTop = container.scrollHeight;
}
