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
    if not correo or len(correo) > 254 or correo.count("@") != 1:
        return False
    local, dominio = correo.split("@")
    return bool(local and dominio and "." in dominio and not re.search(r"\s", correo))


@app.route("/")
@login_requerido
def inicio():
    """READ: consultar y mostrar solo los contactos de la cuenta."""
    contactos = obtener_contactos(g.usuario["id"])
    return render_template("index.html", contactos=contactos)


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
    nombre = request.form.get("nombre", "").strip()
    telefono = request.form.get("telefono", "").strip()
    correo = request.form.get("correo", "").strip()
    categoria = request.form.get("categoria", "").strip()

    if not nombre or not telefono or not categoria:
        flash("Nombre, teléfono y categoría son obligatorios.", "error")
        return redirect(url_for("inicio"))

    agregar_contacto(nombre, telefono, correo, categoria, g.usuario["id"])
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
        nombre = request.form.get("nombre", "").strip()
        telefono = request.form.get("telefono", "").strip()
        correo = request.form.get("correo", "").strip()
        categoria = request.form.get("categoria", "").strip()

        if not nombre or not telefono or not categoria:
            flash("Nombre, teléfono y categoría son obligatorios.", "error")
            return render_template("editar.html", contacto=contacto)

        actualizar_contacto(
            contacto_id,
            nombre,
            telefono,
            correo,
            categoria,
            usuario_id,
        )
        flash("Contacto actualizado correctamente.", "success")
        return redirect(url_for("inicio"))

    return render_template("editar.html", contacto=contacto)


@app.route("/eliminar/<int:contacto_id>", methods=["POST"])
@login_requerido
def eliminar(contacto_id):
    """DELETE: elimina únicamente un contacto de la cuenta."""
    eliminar_contacto(contacto_id, g.usuario["id"])
    flash("Contacto eliminado.", "success")
    return redirect(url_for("inicio"))


if __name__ == "__main__":
    app.run(debug=True)
