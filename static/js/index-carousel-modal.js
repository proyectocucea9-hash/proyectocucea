/**
 * =============================================================================
 * CARRUSEL DE 3 TARJETAS (centro resaltado) + MODAL DETALLADO
 * - Carrusel: solo 3 cards visibles; la del centro tiene scale(1.1) y sombra.
 * - Modal: tamaño mediano, scroll del body bloqueado, scroll interno.
 * - Contenido del modal vía API; Like/Dislike y comentarios estilo Facebook.
 * =============================================================================
 */

(function () {
    'use strict';

    const track = document.getElementById('cards-track');
    const cards = track ? track.querySelectorAll('.card-budget--in-carousel') : [];
    const prevBtn = document.getElementById('cards-prev');
    const nextBtn = document.getElementById('cards-next');
    const modalEl = document.getElementById('detalleModal');
    const modalPlaceholder = document.getElementById('modal-content-placeholder');

    let currentCenterIndex = 0;
    const totalCards = cards.length;

    /* -------------------------------------------------------------------------
     * CARRUSEL: centrar la tarjeta en el índice dado y aplicar resalte al centro
     * ------------------------------------------------------------------------- */
    function setCenterCard(index) {
        if (totalCards === 0) return;
        currentCenterIndex = Math.max(0, Math.min(index, totalCards - 1));

        cards.forEach(function (card, i) {
            card.classList.toggle('card-budget--center', i === currentCenterIndex);
        });

        // Mover el track para que la tarjeta actual quede centrada en el viewport
        const cardWidth = 320;
        const gap = 20;
        const viewport = track ? track.parentElement : null;
        if (viewport) {
            const viewportWidth = viewport.offsetWidth;
            const offset = currentCenterIndex * (cardWidth + gap) - (viewportWidth / 2 - cardWidth / 2);
            track.style.transform = 'translateX(-' + Math.max(0, offset) + 'px)';
        }
    }

    if (track && totalCards > 0) {
        setCenterCard(0);

        if (prevBtn) {
            prevBtn.addEventListener('click', function () {
                setCenterCard(currentCenterIndex - 1);
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', function () {
                setCenterCard(currentCenterIndex + 1);
            });
        }
    }

    /* -------------------------------------------------------------------------
     * MODAL: al abrir, cargar detalle por API y renderizar Like/Dislike + comentarios
     * Bloquear scroll del body mientras el modal está abierto (Bootstrap ya hace algo;
     * aseguramos con clase en body).
     * ------------------------------------------------------------------------- */
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function renderModalContent(data) {
        const imgUrl = data.imagen_url ? (data.imagen_url.indexOf('http') === 0 ? data.imagen_url : '/static/' + data.imagen_url) : '';
        const imgHtml = imgUrl
            ? '<img src="' + escapeHtml(imgUrl) + '" alt="' + escapeHtml(data.concepto) + '" class="modal-detalle__img">'
            : '<div class="modal-detalle__noimg">Sin imagen</div>';

        const esAdmin = data.es_admin === true;
        let comentariosHtml = (data.comentarios || []).map(function (c) {
            const fecha = c.fecha ? new Date(c.fecha).toLocaleDateString('es-MX') : '';
            var eliminarBtn = esAdmin ? ' <button type="button" class="btn-comentario-eliminar btn-link btn-link--danger btn-sm" data-comentario-id="' + c.id + '" title="Eliminar">Eliminar</button>' : '';
            return '<div class="modal-comentario" data-comentario-id="' + c.id + '"><strong>' + escapeHtml(c.autor) + '</strong> <span class="modal-comentario__fecha">' + escapeHtml(fecha) + '</span>' + eliminarBtn + '<p>' + escapeHtml(c.contenido) + '</p></div>';
        }).join('');

        return (
            '<div class="modal-detalle">' +
            '  <div class="modal-detalle__main">' +
            '    <div class="modal-detalle__left">' +
            '      <div class="modal-detalle__media">' + imgHtml + '</div>' +
            '      <div class="modal-detalle__reacciones">' +
            '        <button type="button" class="btn-reaccion btn-reaccion--like" data-id="' + data.id + '" aria-label="Like"><i class="fas fa-thumbs-up"></i> <span class="btn-reaccion__count">' + (data.likes || 0) + '</span></button>' +
            '        <button type="button" class="btn-reaccion btn-reaccion--dislike" data-id="' + data.id + '" aria-label="Dislike"><i class="fas fa-thumbs-down"></i> <span class="btn-reaccion__count">' + (data.dislikes || 0) + '</span></button>' +
            '      </div>' +
            '      <div class="modal-comentarios">' +
            '        <h4>Comentarios</h4>' +
            '        <div class="modal-comentarios__list">' + comentariosHtml + '</div>' +
            '        <div class="modal-comentarios__form">' +
            '          <input type="text" class="modal-comentarios__autor" placeholder="Tu nombre (opcional)">' +
            '          <textarea class="modal-comentarios__texto" placeholder="Escribe un comentario..." rows="2"></textarea>' +
            '          <button type="button" class="btn btn--primary btn-sm modal-comentarios__submit" data-id="' + data.id + '">Comentar</button>' +
            '        </div>' +
            '      </div>' +
            '    </div>' +
            '    <div class="modal-detalle__right">' +
            '      <h3 class="modal-detalle__titulo">' + escapeHtml(data.concepto) + '</h3>' +
            '      <p class="modal-detalle__meta">' + escapeHtml(data.fecha) + ' · ' + escapeHtml(data.categoria) + '</p>' +
            '      <p class="modal-detalle__monto">$' + (data.monto != null ? Number(data.monto).toLocaleString('es-MX', { minimumFractionDigits: 2 }) : '') + '</p>' +
            (data.cantidad_gasto != null && data.cantidad_gasto > 0 ? '<p class="modal-detalle__gasto">Gasto: $' + Number(data.cantidad_gasto).toLocaleString('es-MX', { minimumFractionDigits: 0 }) + '</p>' : '') +
            '      <div class="modal-detalle__descripcion">' + escapeHtml(data.descripcion || 'Sin descripción.') + '</div>' +
            '    </div>' +
            '  </div>' +
            '</div>'
        );
    }

    if (modalEl && modalPlaceholder) {
        // Bloquear scroll del fondo cuando el modal está abierto
        modalEl.addEventListener('show.bs.modal', function () {
            document.body.classList.add('modal-open-scroll-lock');
        });
        modalEl.addEventListener('hidden.bs.modal', function () {
            document.body.classList.remove('modal-open-scroll-lock');
        });

        modalEl.addEventListener('show.bs.modal', function (event) {
            // Al abrir por JS, el id puede estar en data-current-id; si no, en la card relacionada o la centrada
            let id = modalEl.getAttribute('data-current-id');
            if (!id) {
                const card = event.relatedTarget || (track && track.querySelector('.card-budget--center'));
                id = card && card.getAttribute ? card.getAttribute('data-id') : null;
            }
            modalEl.removeAttribute('data-current-id');
            if (!id) {
                modalPlaceholder.innerHTML = '<p class="text-muted">Selecciona un proyecto.</p>';
                return;
            }
            modalPlaceholder.innerHTML = '<p class="text-muted">Cargando...</p>';

            fetch('/api/presupuesto/' + id)
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    modalPlaceholder.innerHTML = renderModalContent(data);

                    var csrfToken = (document.querySelector('meta[name="csrf-token"]') && document.querySelector('meta[name="csrf-token"]').getAttribute('content')) || '';
                    function updateCounts(d) {
                        var likeSpan = modalPlaceholder.querySelector('.btn-reaccion--like .btn-reaccion__count');
                        var dislikeSpan = modalPlaceholder.querySelector('.btn-reaccion--dislike .btn-reaccion__count');
                        if (likeSpan) likeSpan.textContent = d.likes;
                        if (dislikeSpan) dislikeSpan.textContent = d.dislikes;
                    }
                    // Like (requiere login; un voto por usuario - tabla VotoPresupuesto)
                    modalPlaceholder.querySelectorAll('.btn-reaccion--like').forEach(function (btn) {
                        btn.addEventListener('click', function () {
                            const pid = this.getAttribute('data-id');
                            fetch('/api/presupuesto/' + pid + '/like', { method: 'POST', headers: { 'X-CSRFToken': csrfToken } })
                                .then(function (r) {
                                    if (r.status === 401) { alert('Inicia sesión para votar.'); return null; }
                                    return r.json();
                                })
                                .then(function (d) { if (d) updateCounts(d); });
                        });
                    });
                    // Dislike
                    modalPlaceholder.querySelectorAll('.btn-reaccion--dislike').forEach(function (btn) {
                        btn.addEventListener('click', function () {
                            const pid = this.getAttribute('data-id');
                            fetch('/api/presupuesto/' + pid + '/dislike', { method: 'POST', headers: { 'X-CSRFToken': csrfToken } })
                                .then(function (r) {
                                    if (r.status === 401) { alert('Inicia sesión para votar.'); return null; }
                                    return r.json();
                                })
                                .then(function (d) { if (d) updateCounts(d); });
                        });
                    });
                    // Eliminar comentario (solo Admin)
                    modalPlaceholder.querySelectorAll('.btn-comentario-eliminar').forEach(function (btn) {
                        btn.addEventListener('click', function () {
                            var cid = this.getAttribute('data-comentario-id');
                            if (!cid || !confirm('¿Eliminar este comentario?')) return;
                            fetch('/api/comentario/' + cid + '/eliminar', { method: 'POST', headers: { 'X-CSRFToken': csrfToken } })
                                .then(function (r) { return r.json(); })
                                .then(function () {
                                    var div = modalPlaceholder.querySelector('.modal-comentario[data-comentario-id="' + cid + '"]');
                                    if (div) div.remove();
                                });
                        });
                    });
                    // Comentar
                    modalPlaceholder.querySelectorAll('.modal-comentarios__submit').forEach(function (btn) {
                        btn.addEventListener('click', function () {
                            const pid = this.getAttribute('data-id');
                            const autor = (modalPlaceholder.querySelector('.modal-comentarios__autor') && modalPlaceholder.querySelector('.modal-comentarios__autor').value) || 'Anónimo';
                            const contenido = modalPlaceholder.querySelector('.modal-comentarios__texto') && modalPlaceholder.querySelector('.modal-comentarios__texto').value;
                            if (!contenido || !contenido.trim()) return;
                            var formData = new FormData();
                            formData.append('autor', autor);
                            formData.append('contenido', contenido);
                            var csrfMeta = document.querySelector('meta[name="csrf-token"]');
                            formData.append('csrf_token', csrfMeta ? csrfMeta.getAttribute('content') : '');
                            fetch('/api/presupuesto/' + pid + '/comentarios', {
                                method: 'POST',
                                body: formData,
                                headers: { 'X-Requested-With': 'XMLHttpRequest' }
                            })
                                .then(function (r) { return r.json(); })
                                .then(function (c) {
                                    var list = modalPlaceholder.querySelector('.modal-comentarios__list');
                                    if (list) {
                                        var div = document.createElement('div');
                                        div.className = 'modal-comentario';
                                        div.setAttribute('data-comentario-id', c.id);
                                        div.innerHTML = '<strong>' + escapeHtml(c.autor) + '</strong> <span class="modal-comentario__fecha">' + escapeHtml(c.fecha ? new Date(c.fecha).toLocaleDateString('es-MX') : '') + '</span><p>' + escapeHtml(c.contenido) + '</p>';
                                        list.appendChild(div);
                                    }
                                    var ta = modalPlaceholder.querySelector('.modal-comentarios__texto');
                                    if (ta) ta.value = '';
                                });
                        });
                    });
                })
                .catch(function () {
                    modalPlaceholder.innerHTML = '<p class="text-muted">Error al cargar el detalle.</p>';
                });
        });
    }

    /* Abrir modal al hacer click en una card del carrusel */
    if (cards.length) {
        cards.forEach(function (card) {
            card.addEventListener('click', function (e) {
                if (e.target.closest('.card-budget__edit-link') || e.target.closest('.card-budget__actions')) return;
                var modal = document.getElementById('detalleModal');
                if (!modal) return;
                modal.setAttribute('data-current-id', card.getAttribute('data-id'));
                modal.relatedTarget = card;
                var bsModal = bootstrap.Modal.getOrCreateInstance(modal);
                bsModal.show();
            });
        });
    }
})();
