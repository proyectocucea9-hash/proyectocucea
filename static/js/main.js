/**
 * =============================================================================
 * PLATAFORMA DE TRANSPARENCIA PRESUPUESTARIA - CUCEA
 * Script principal: Navbar scroll, Carruseles, Modal
 * =============================================================================
 *
 * Contiene la lógica para:
 * 1. Efecto de redimensionamiento del Navbar al hacer scroll
 * 2. Carrusel de imágenes (Franja 1 - Presentación)
 * 3. Carrusel de cards con flechas de navegación
 * 4. Modal Bootstrap (preparado, se dispara al hacer click en una card)
 */

document.addEventListener('DOMContentLoaded', function () {

    /* =========================================================================
       CARRUSEL DE IMÁGENES - FRANJA 1 (Presentación)
       =========================================================================
       Lógica:
       - 3 slides que rotan automáticamente cada 5 segundos
       - Los indicadores (dots) permiten cambio manual
       - Al hacer click en un dot: va a ese slide y reinicia el intervalo
       - goToSlide(index): quita clase --active de todos, la añade al actual
       ========================================================================= */
    const carouselIntro = document.querySelector('.carousel-intro');
    if (carouselIntro) {
        const slides = carouselIntro.querySelectorAll('.carousel-intro__slide');
        const dots = carouselIntro.querySelectorAll('.carousel-intro__dot');
        const totalSlides = slides.length;
        let currentSlide = 0;

        function goToSlide(index) {
            currentSlide = (index + totalSlides) % totalSlides;
            slides.forEach(s => s.classList.remove('carousel-intro__slide--active'));
            dots.forEach(d => d.classList.remove('carousel-intro__dot--active'));
            slides[currentSlide].classList.add('carousel-intro__slide--active');
            if (dots[currentSlide]) dots[currentSlide].classList.add('carousel-intro__dot--active');
        }

        let carouselInterval = setInterval(() => goToSlide(currentSlide + 1), 5000);

        dots.forEach((dot, i) => {
            dot.addEventListener('click', () => {
                clearInterval(carouselInterval);
                goToSlide(i);
                carouselInterval = setInterval(() => goToSlide(currentSlide + 1), 5000);
            });
        });
    }


    /* =========================================================================
       CARRUSEL DE CARDS - FRANJA 3
       =========================================================================
       Lógica:
       - Contenedor horizontal con scroll suave (overflow-x: auto)
       - Flecha izquierda: desplaza el track hacia la izquierda
       - Flecha derecha: desplaza el track hacia la derecha
       - scrollBy({ left: ±offset }) mueve el contenido
       - Cada card tiene data-bs-toggle="modal" data-bs-target="#detalleModal"
         para abrir el modal de Bootstrap al hacer click
       ========================================================================= */
    const cardsTrack = document.getElementById('cards-track');
    const cardsPrev = document.getElementById('cards-prev');
    const cardsNext = document.getElementById('cards-next');

    if (cardsTrack && (cardsPrev || cardsNext)) {
        const scrollAmount = 320; // Aprox. ancho de una card + gap

        if (cardsPrev) {
            cardsPrev.addEventListener('click', () => {
                cardsTrack.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
            });
        }

        if (cardsNext) {
            cardsNext.addEventListener('click', () => {
                cardsTrack.scrollBy({ left: scrollAmount, behavior: 'smooth' });
            });
        }
    }


    /* =========================================================================
       MODAL BOOTSTRAP - Al hacer click en una card
       =========================================================================
       Bootstrap abre el modal automáticamente con data-bs-toggle y data-bs-target.
       Aquí preparamos el contenido: cuando se abre el modal, mostramos el título
       del proyecto en el placeholder (el modal está vacío por ahora).
       Si la card tiene data-id, podemos usarlo para cargar detalle vía AJAX después.
       ========================================================================= */
    const detalleModal = document.getElementById('detalleModal');
    const modalPlaceholder = document.getElementById('modal-content-placeholder');

    if (detalleModal && modalPlaceholder) {
        detalleModal.addEventListener('show.bs.modal', function (event) {
            // event.relatedTarget es el elemento que disparó el modal (la card)
            const card = event.relatedTarget;
            if (card && card.classList.contains('card-budget')) {
                const projectId = card.getAttribute('data-id') || '';
                const projectTitle = card.querySelector('.card-budget__title');
                const title = projectTitle ? projectTitle.textContent.trim() : 'Proyecto';
                const detailLink = projectId ? '/presupuesto/' + projectId : '/presupuestos';
                modalPlaceholder.innerHTML = '<p class="text-muted">Detalle del proyecto: <strong>' + escapeHtml(title) + '</strong></p>' +
                    '<p class="text-muted small">Próximamente se cargará el contenido completo aquí.</p>' +
                    '<a href="' + detailLink + '" class="btn btn-primary mt-3">Ver detalle completo</a>';
            } else {
                modalPlaceholder.innerHTML = '<p class="text-muted">Cargando...</p>';
            }
        });
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }


    /* =========================================================================
       NAVBAR MÓVIL - Toggle del menú hamburguesa
       ========================================================================= */
    const navbarToggle = document.getElementById('navbar-toggle');
    const navbarMenu = document.querySelector('.navbar__menu');
    if (navbarToggle && navbarMenu) {
        navbarToggle.addEventListener('click', () => {
            navbarMenu.classList.toggle('navbar__menu--open');
        });
    }


    /* =========================================================================
       FLASH MESSAGES - Auto-ocultar después de 5 segundos
       ========================================================================= */
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.3s';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });


    /* =========================================================================
       CHATBOT ROBOTSITO - Bienvenida → ícono flotante → ventana chat con FAQ
       ========================================================================= */
    const chatbotWelcome = document.getElementById('chatbot-welcome');
    const chatbotToggle = document.getElementById('chatbot-toggle');
    const chatbotPanel = document.getElementById('chatbot-panel');
    const chatbotClose = document.getElementById('chatbot-close');
    const chatbotMessages = document.getElementById('chatbot-messages');
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotSend = document.getElementById('chatbot-send');
    const FAQ_RESPONSES = {
        presupuesto: 'Para subir un presupuesto debes iniciar sesión con una cuenta de administrador. Luego ve a "Presupuesto" en el menú y haz clic en "Agregar". Completa el formulario con los datos del proyecto y guarda.',
        superadmin: 'El Super Admin es un usuario con permisos especiales que puede gestionar a otros usuarios (dar de alta, editar roles, etc.). Solo hay uno o pocos Super Admins por seguridad. Accede desde "Gestionar Usuarios" en la barra de navegación.',
        sede: 'En la página de Presupuesto verás filtros arriba de la lista. Usa el desplegable "Sede" para elegir la sede que desees y la lista se actualizará mostrando solo los presupuestos de esa sede.'
    };
    const WELCOME_DURATION_MS = 5000;
    const BUBBLE_POP_MS = 350;
    const VORTEX_MS = 600;

    function appendBotMessage(text) {
        const div = document.createElement('div');
        div.className = 'chatbot-msg chatbot-msg--bot';
        div.innerHTML = '<span class="chatbot-msg__bubble">' + escapeHtml(text) + '</span>';
        chatbotMessages.appendChild(div);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }

    function appendUserMessage(text) {
        const div = document.createElement('div');
        div.className = 'chatbot-msg chatbot-msg--user';
        div.innerHTML = '<span class="chatbot-msg__bubble">' + escapeHtml(text) + '</span>';
        chatbotMessages.appendChild(div);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }

    function getFaqResponse(userText) {
        const t = userText.toLowerCase().trim();
        if (t.includes('presupuesto') && (t.includes('subir') || t.includes('agregar') || t.includes('cómo'))) return FAQ_RESPONSES.presupuesto;
        if (t.includes('super admin') || t.includes('superadmin')) return FAQ_RESPONSES.superadmin;
        if (t.includes('sede') && t.includes('filtrar')) return FAQ_RESPONSES.sede;
        return null;
    }

    function answerFaq(faqKey) {
        const question = {
            presupuesto: '¿Cómo subir un presupuesto?',
            superadmin: '¿Quién es el Super Admin?',
            sede: '¿Cómo filtrar por sede?'
        }[faqKey];
        if (question) {
            appendUserMessage(question);
            appendBotMessage(FAQ_RESPONSES[faqKey] || 'No tengo esa información.');
        }
    }

    const chatbotWidget = document.getElementById('chatbot-widget');
    const chatbotBubble = document.getElementById('chatbot-bubble');
    const chatbotRobotBig = document.getElementById('chatbot-robot-big');
    if (chatbotWelcome && chatbotToggle && chatbotPanel && chatbotWidget) {
        setTimeout(function () {
            if (chatbotBubble) chatbotBubble.classList.add('chatbot-bubble--pop');
            setTimeout(function () {
                if (chatbotRobotBig) chatbotRobotBig.classList.add('chatbot-robot--vortex');
                setTimeout(function () {
                    if (chatbotRobotBig) chatbotRobotBig.classList.add('chatbot-robot--vortex-done');
                    chatbotWelcome.classList.add('chatbot-welcome--hidden');
                    chatbotToggle.classList.add('chatbot-toggle--visible');
                }, VORTEX_MS);
            }, BUBBLE_POP_MS);
        }, WELCOME_DURATION_MS);

        chatbotToggle.addEventListener('click', function () {
            chatbotPanel.classList.add('chatbot-panel--open');
            chatbotWidget.classList.add('chatbot-panel-open');
            if (chatbotInput) chatbotInput.focus();
        });

        chatbotClose.addEventListener('click', function () {
            chatbotPanel.classList.remove('chatbot-panel--open');
            chatbotWidget.classList.remove('chatbot-panel-open');
        });

        document.querySelectorAll('.chatbot-faq-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                const faq = this.getAttribute('data-faq');
                if (faq && FAQ_RESPONSES[faq]) {
                    answerFaq(faq);
                }
            });
        });

        function sendUserMessage() {
            const text = (chatbotInput && chatbotInput.value) ? chatbotInput.value.trim() : '';
            if (!text) return;
            appendUserMessage(text);
            chatbotInput.value = '';
            const faq = getFaqResponse(text);
            setTimeout(function () {
                appendBotMessage(faq || 'No encontré una respuesta exacta. Prueba con las preguntas frecuentes o reformula tu pregunta.');
            }, 400);
        }

        if (chatbotSend && chatbotInput) {
            chatbotSend.addEventListener('click', sendUserMessage);
            chatbotInput.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') { e.preventDefault(); sendUserMessage(); }
            });
        }
    }
});
