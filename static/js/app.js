// Búsqueda, filtro de categorías, menú móvil y confirmación de borrado.
document.addEventListener("DOMContentLoaded", function () {
    const buscador = document.getElementById("buscar");
    const filtroCategoria = document.getElementById("filtro-categoria");
    const tarjetas = Array.from(document.querySelectorAll(".tarjeta-contacto"));
    const mensajeVacio = document.getElementById("sin-resultados");
    const botonMenu = document.querySelector(".menu-movil");
    const superposicionMenu = document.querySelector(".superposicion-menu");
    const barraLateral = document.querySelector(".barra-lateral");
    const enlacesMenu = Array.from(document.querySelectorAll(".enlace-menu"));

    function actualizarEnlaceActivo() {
        if (window.location.pathname !== "/") return;
        const hash = window.location.hash || "#inicio";
        enlacesMenu.forEach(function (enlace) {
            enlace.classList.toggle("activo", enlace.hash === hash);
        });
    }

    actualizarEnlaceActivo();
    window.addEventListener("hashchange", actualizarEnlaceActivo);

    function filtrarContactos() {
        const texto = buscador ? buscador.value.toLocaleLowerCase().trim() : "";
        const categoria = filtroCategoria ? filtroCategoria.value : "";
        let visibles = 0;

        tarjetas.forEach(function (tarjeta) {
            const coincideTexto = tarjeta.textContent.toLocaleLowerCase().includes(texto);
            const coincideCategoria = !categoria || tarjeta.dataset.categoria === categoria;
            const visible = coincideTexto && coincideCategoria;
            tarjeta.classList.toggle("oculto", !visible);
            if (visible) visibles++;
        });

        if (mensajeVacio) {
            mensajeVacio.classList.toggle("oculto", visibles > 0);
        }
    }

    if (buscador) {
        buscador.addEventListener("input", filtrarContactos);
    }

    if (filtroCategoria) {
        const categorias = Array.from(new Set(tarjetas.map(function (tarjeta) {
            return tarjeta.dataset.categoria;
        }))).sort(function (a, b) {
            return a.localeCompare(b, "es");
        });

        categorias.forEach(function (categoria) {
            const opcion = document.createElement("option");
            opcion.value = categoria;
            opcion.textContent = categoria;
            filtroCategoria.appendChild(opcion);
        });
        filtroCategoria.addEventListener("change", filtrarContactos);
    }

    if (botonMenu && barraLateral) {
        function cerrarMenu() {
            barraLateral.classList.remove("abierto");
            document.body.classList.remove("menu-abierto");
            botonMenu.setAttribute("aria-expanded", "false");
        }

        botonMenu.addEventListener("click", function () {
            const abierto = barraLateral.classList.toggle("abierto");
            document.body.classList.toggle("menu-abierto", abierto);
            botonMenu.setAttribute("aria-expanded", String(abierto));
        });

        if (superposicionMenu) {
            superposicionMenu.addEventListener("click", cerrarMenu);
        }

        enlacesMenu.forEach(function (enlace) {
            enlace.addEventListener("click", cerrarMenu);
        });

        document.addEventListener("keydown", function (evento) {
            if (evento.key === "Escape") cerrarMenu();
        });
    }

    document.querySelectorAll(".form-eliminar").forEach(function (formulario) {
        formulario.addEventListener("submit", function (evento) {
            if (!window.confirm("¿Seguro que deseas eliminar este contacto?")) {
                evento.preventDefault();
            }
        });
    });
});
