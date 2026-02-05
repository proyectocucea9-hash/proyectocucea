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
       NAVBAR - EFECTO DE REDIMENSIONAMIENTO AL HACER SCROLL
       =========================================================================
       Lógica:
       - Estado inicial (arriba): Navbar más ancha con más padding vertical
       - Al bajar la página: detectamos scroll > umbral y añadimos clase
         navbar--scrolled que reduce altura y padding (CSS hace la transición)
       - Al volver arriba: quitamos la clase y recupera tamaño original
       - La transición suave se logra con CSS: transition: all 0.3s ease;
       ========================================================================= */
    const navbar = document.getElementById('main-navbar');
    const scrollThreshold = 50; // Píxeles de scroll para activar el cambio

    if (navbar) {
        function updateNavbarScroll() {
            if (window.scrollY > scrollThreshold) {
                navbar.classList.add('navbar--scrolled');
            } else {
                navbar.classList.remove('navbar--scrolled');
            }
        }

        // Ejecutar al cargar (por si la página ya tiene scroll)
        updateNavbarScroll();

        // Ejecutar cada vez que el usuario hace scroll
        window.addEventListener('scroll', updateNavbarScroll, { passive: true });
    }


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
});
