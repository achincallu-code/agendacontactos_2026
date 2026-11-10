"""
Agenda de Contactos
Aplicación web escolar construida con Flask y SQLite.

Rutas principales:
  GET  /                 -> READ: muestra los contactos
  POST /agregar          -> CREATE: guarda un contacto nuevo
  GET  /editar/<id>      -> muestra el formulario de edición
  POST /editar/<id>      -> UPDATE: actualiza un contacto
  POST /eliminar/<id>    -> DELETE: elimina un contacto
"""

import os

from flask import Flask, render_template, request, redirect, url_for, flash

from database import (
    agregar_contacto,
    actualizar_contacto,
    crear_tabla,
    eliminar_contacto,
    obtener_contacto,
    obtener_contactos,
    verificar_conexion,
)

app = Flask(__name__)
# Flask usa esta clave para proteger los mensajes flash de la sesión.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "clave-local-solo-para-desarrollo")
app.config["SESSION_COOKIE_SECURE"] = bool(os.environ.get("RENDER"))

if os.environ.get("RENDER") and not os.environ.get("DATABASE_URL"):
    raise RuntimeError("Configura DATABASE_URL en Render para usar una base persistente.")

# Crea la tabla si todavía no existe.
crear_tabla()


@app.route("/")
def inicio():
    """READ: consultar y mostrar todos los contactos."""
    contactos = obtener_contactos()
    return render_template("index.html", contactos=contactos)


@app.route("/health")
def salud():
    """Endpoint para comprobar que la aplicación y su base de datos responden."""
    verificar_conexion()
    return {"estado": "ok"}


@app.route("/agregar", methods=["POST"])
def agregar():
    """CREATE: validar y guardar un contacto."""
    nombre = request.form.get("nombre", "").strip()
    telefono = request.form.get("telefono", "").strip()
    correo = request.form.get("correo", "").strip()
    categoria = request.form.get("categoria", "").strip()

    if not nombre or not telefono or not categoria:
        flash("Nombre, teléfono y categoría son obligatorios.", "error")
        return redirect(url_for("inicio"))

    agregar_contacto(nombre, telefono, correo, categoria)
    flash("Contacto agregado correctamente.", "success")
    return redirect(url_for("inicio"))


@app.route("/editar/<int:contacto_id>", methods=["GET", "POST"])
def editar(contacto_id):
    """GET muestra el formulario y POST ejecuta UPDATE."""
    contacto = obtener_contacto(contacto_id)

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

        actualizar_contacto(contacto_id, nombre, telefono, correo, categoria)
        flash("Contacto actualizado correctamente.", "success")
        return redirect(url_for("inicio"))

    return render_template("editar.html", contacto=contacto)


@app.route("/eliminar/<int:contacto_id>", methods=["POST"])
def eliminar(contacto_id):
    """DELETE: elimina el contacto indicado por su ID."""
    eliminar_contacto(contacto_id)
    flash("Contacto eliminado.", "success")
    return redirect(url_for("inicio"))


if __name__ == "__main__":
    # debug=True ayuda durante el desarrollo escolar. No se recomienda
    # dejarlo activado al publicar una aplicación en internet.
    app.run(debug=True)
