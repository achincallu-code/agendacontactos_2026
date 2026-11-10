"""
Agenda de Contactos
Aplicación web con cuentas individuales y contactos aislados por propietario.

Rutas principales:
  GET  /                 -> READ: muestra los contactos de la cuenta
  POST /agregar          -> CREATE: guarda un contacto nuevo
  GET  /editar/<id>      -> muestra el formulario de edición
  POST /editar/<id>      -> UPDATE: actualiza un contacto propio
  POST /eliminar/<id>    -> DELETE: elimina un contacto propio
"""

import os
import re
import sqlite3
from datetime import timedelta
from functools import wraps

import psycopg
from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

from database import (
    agregar_contacto,
    asignar_contactos_sin_dueno,
    actualizar_contacto,
    crear_tabla,
    crear_usuario,
    eliminar_contacto,
    obtener_contacto,
    obtener_contactos,
    obtener_usuario,
    obtener_usuario_por_correo,
    verificar_conexion,
)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "clave-local-solo-para-desarrollo"),
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
    CONTACTS_OWNER_EMAIL=os.environ.get("CONTACTS_OWNER_EMAIL", "").strip().lower(),
)
csrf = CSRFProtect(app)
CATEGORIAS_CONTACTO = ("Familia", "Amigos", "Escuela", "Trabajo", "Otros")

if os.environ.get("RENDER") and not os.environ.get("DATABASE_URL"):
    raise RuntimeError("Configura DATABASE_URL en Render para usar una base persistente.")

crear_tabla()


def login_requerido(vista):
    """Redirige a la pantalla de acceso si no hay una cuenta autenticada."""
    @wraps(vista)
    def vista_protegida(*args, **kwargs):
        if g.usuario is None:
            return redirect(url_for("iniciar_sesion"))
        return vista(*args, **kwargs)

    return vista_protegida


@app.before_request
def cargar_usuario():
    usuario_id = session.get("usuario_id")
    g.usuario = obtener_usuario(usuario_id) if usuario_id is not None else None
    if usuario_id is not None and g.usuario is None:
        session.clear()


def asignar_contactos_legacy(usuario):
    """Asigna registros antiguos solo a la cuenta autorizada por configuración."""
    correo_propietario = app.config["CONTACTS_OWNER_EMAIL"]
    if correo_propietario and usuario["correo"] == correo_propietario:
        asignar_contactos_sin_dueno(usuario["id"])


def correo_valido(correo):
    if not correo or len(correo) > 254:
        return False
    partes = correo.split("@")
    if len(partes) != 2 or len(partes[0]) > 64 or len(partes[1]) > 253:
        return False
    patron = (
        r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
        r"(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@"
        r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
        r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    )
    return re.fullmatch(patron, correo) is not None


def validar_contacto(nombre, telefono, correo, categoria, categoria_actual=None):
    if not nombre or len(nombre) > 100:
        return "Escribe un nombre de hasta 100 caracteres."
    if not telefono or len(telefono) > 30:
        return "Escribe un teléfono de hasta 30 caracteres."
    if not re.fullmatch(r"\+?[0-9().\-\s]+", telefono):
        return "El teléfono solo puede contener números, espacios y + ( ) . -."
    digitos_telefono = re.sub(r"\D", "", telefono)
    if not 7 <= len(digitos_telefono) <= 15:
        return "El teléfono debe contener entre 7 y 15 dígitos."
    if correo and not correo_valido(correo):
        return "Escribe un correo electrónico válido (máximo 254 caracteres)."
    if (
        categoria not in CATEGORIAS_CONTACTO
        and categoria != categoria_actual
    ):
        return "Selecciona una categoría válida."
    return None


def datos_contacto_formulario():
    return {
        "nombre": " ".join(request.form.get("nombre", "").split()),
        "telefono": request.form.get("telefono", "").strip(),
        "correo": request.form.get("correo", "").strip(),
        "categoria": request.form.get("categoria", "").strip(),
    }


def mostrar_error_base_datos(operacion):
    app.logger.exception("Error de base de datos al %s.", operacion)
    flash(
        "No se pudo completar la operación. Inténtalo de nuevo más tarde.",
        "error",
    )


@app.route("/")
@login_requerido
def inicio():
    """READ: consultar y mostrar solo los contactos de la cuenta."""
    contactos = obtener_contactos(g.usuario["id"])
    return render_template(
        "index.html",
        contactos=contactos,
        categorias=CATEGORIAS_CONTACTO,
        formulario={},
    )


@app.route("/health")
def salud():
    """Endpoint para comprobar que la aplicación y su base de datos responden."""
    verificar_conexion()
    return {"estado": "ok"}


@app.route("/iniciar-sesion", methods=["GET", "POST"])
def iniciar_sesion():
    if g.usuario is not None:
        return redirect(url_for("inicio"))

    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        contrasena = request.form.get("contrasena", "")
        usuario = obtener_usuario_por_correo(correo)

        if (
            usuario is None
            or len(contrasena) > 128
            or not check_password_hash(usuario["password_hash"], contrasena)
        ):
            flash("El correo o la contraseña no son correctos.", "error")
        else:
            session.clear()
            session["usuario_id"] = usuario["id"]
            session.permanent = request.form.get("recordarme") == "on"
            asignar_contactos_legacy(usuario)
            return redirect(url_for("inicio"))

    return render_template("iniciar_sesion.html")


@app.route("/crear-cuenta", methods=["GET", "POST"])
def crear_cuenta():
    if g.usuario is not None:
        return redirect(url_for("inicio"))

    if request.method == "POST":
        nombre = " ".join(request.form.get("nombre", "").split())
        correo = request.form.get("correo", "").strip().lower()
        contrasena = request.form.get("contrasena", "")

        if not nombre or len(nombre) > 80:
            flash("Escribe tu nombre (máximo 80 caracteres).", "error")
        elif not correo_valido(correo):
            flash("Escribe un correo electrónico válido.", "error")
        elif len(contrasena) < 8 or len(contrasena) > 128:
            flash("La contraseña debe tener entre 8 y 128 caracteres.", "error")
        else:
            try:
                usuario_id = crear_usuario(
                    nombre,
                    correo,
                    generate_password_hash(contrasena),
                )
            except (sqlite3.IntegrityError, psycopg.errors.UniqueViolation):
                flash("Ya existe una cuenta con ese correo. Prueba iniciar sesión.", "error")
            else:
                session.clear()
                session["usuario_id"] = usuario_id
                session.permanent = True
                usuario = obtener_usuario(usuario_id)
                asignar_contactos_legacy(usuario)
                flash("Tu cuenta está lista. ¡Bienvenido a la parrilla!", "success")
                return redirect(url_for("inicio"))

    return render_template("crear_cuenta.html")


@app.route("/cerrar-sesion", methods=["POST"])
def cerrar_sesion():
    session.clear()
    flash("Cerraste sesión. ¡Hasta pronto!", "success")
    return redirect(url_for("iniciar_sesion"))


@app.route("/agregar", methods=["POST"])
@login_requerido
def agregar():
    """CREATE: validar y guardar un contacto para la cuenta."""
    formulario = datos_contacto_formulario()
    error = validar_contacto(**formulario)
    if error:
        flash(error, "error")
        return render_template(
            "index.html",
            contactos=obtener_contactos(g.usuario["id"]),
            categorias=CATEGORIAS_CONTACTO,
            formulario=formulario,
        )

    try:
        agregar_contacto(
            formulario["nombre"],
            formulario["telefono"],
            formulario["correo"],
            formulario["categoria"],
            g.usuario["id"],
        )
    except (sqlite3.Error, psycopg.Error):
        mostrar_error_base_datos("guardar un contacto")
        return redirect(url_for("inicio"))
    flash("Contacto agregado correctamente.", "success")
    return redirect(url_for("inicio"))


@app.route("/editar/<int:contacto_id>", methods=["GET", "POST"])
@login_requerido
def editar(contacto_id):
    """GET muestra el formulario y POST actualiza un contacto propio."""
    usuario_id = g.usuario["id"]
    contacto = obtener_contacto(contacto_id, usuario_id)

    if contacto is None:
        flash("No se encontró ese contacto.", "error")
        return redirect(url_for("inicio"))

    if request.method == "POST":
        formulario = datos_contacto_formulario()
        error = validar_contacto(
            **formulario,
            categoria_actual=contacto["categoria"],
        )
        if error:
            flash(error, "error")
            return render_template("editar.html", contacto=contacto)

        try:
            actualizado = actualizar_contacto(
                contacto_id,
                formulario["nombre"],
                formulario["telefono"],
                formulario["correo"],
                formulario["categoria"],
                usuario_id,
            )
        except (sqlite3.Error, psycopg.Error):
            mostrar_error_base_datos("actualizar un contacto")
            return render_template("editar.html", contacto=contacto), 500
        if not actualizado:
            flash("El contacto ya no existe o fue eliminado.", "error")
            return redirect(url_for("inicio"))
        flash("Contacto actualizado correctamente.", "success")
        return redirect(url_for("inicio"))

    return render_template("editar.html", contacto=contacto)


@app.route("/eliminar/<int:contacto_id>", methods=["POST"])
@login_requerido
def eliminar(contacto_id):
    """DELETE: elimina únicamente un contacto de la cuenta."""
    try:
        eliminado = eliminar_contacto(contacto_id, g.usuario["id"])
    except (sqlite3.Error, psycopg.Error):
        mostrar_error_base_datos("eliminar un contacto")
        return redirect(url_for("inicio"))
    if not eliminado:
        flash("El contacto ya no existe o fue eliminado.", "error")
        return redirect(url_for("inicio"))
    flash("Contacto eliminado.", "success")
    return redirect(url_for("inicio"))


if __name__ == "__main__":
    app.run(debug=True)
