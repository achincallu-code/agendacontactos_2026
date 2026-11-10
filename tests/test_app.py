import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database

_directorio_temporal = tempfile.TemporaryDirectory(prefix="agenda-test-")
database.DATABASE_URL = None
database.RUTA_DB = Path(_directorio_temporal.name) / "contactos-test.db"

import app as aplicacion

aplicacion.app.config.update(
    TESTING=True,
    SECRET_KEY="clave-de-prueba",
    SESSION_COOKIE_SECURE=False,
    CONTACTS_OWNER_EMAIL="",
)


class PruebasAgenda(unittest.TestCase):
    def setUp(self):
        database._ejecutar("DELETE FROM contactos")
        database._ejecutar("DELETE FROM usuarios")
        self.cliente = aplicacion.app.test_client()

    def csrf(self, cliente, ruta):
        respuesta = cliente.get(ruta)
        self.assertEqual(respuesta.status_code, 200)
        coincidencia = re.search(
            rb'name="csrf_token" value="([^"]+)"',
            respuesta.data,
        )
        self.assertIsNotNone(coincidencia)
        return coincidencia.group(1).decode()

    def crear_cuenta(self, cliente, nombre, correo):
        token = self.csrf(cliente, "/crear-cuenta")
        return cliente.post(
            "/crear-cuenta",
            data={
                "csrf_token": token,
                "nombre": nombre,
                "correo": correo,
                "contrasena": "FormulaUno2026!",
            },
        )

    def crear_contacto(self, cliente, **datos):
        token = self.csrf(cliente, "/")
        return cliente.post(
            "/agregar",
            data={"csrf_token": token, **datos},
            follow_redirects=True,
        )

    def test_autenticacion_crud_validaciones_y_aislamiento(self):
        respuesta = self.crear_cuenta(
            self.cliente, "Piloto Uno", "piloto1@example.test"
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.cliente.get("/").status_code, 200)
        with self.cliente.session_transaction() as sesion:
            usuario_id = sesion["usuario_id"]

        respuesta = self.crear_contacto(
            self.cliente,
            nombre="Ana García",
            telefono="+52 (55) 1234-5678",
            correo="ana@example.com",
            categoria="Amigos",
        )
        self.assertIn(b"Ana Garc", respuesta.data)
        contacto_id = re.search(rb'href="/editar/(\d+)"', respuesta.data)
        self.assertIsNotNone(contacto_id)
        contacto_id = int(contacto_id.group(1))

        casos_invalidos = (
            {
                "nombre": "",
                "telefono": "5512345678",
                "correo": "",
                "categoria": "Amigos",
            },
            {
                "nombre": "Nombre",
                "telefono": "123",
                "correo": "",
                "categoria": "Amigos",
            },
            {
                "nombre": "Nombre",
                "telefono": "123456789",
                "correo": "correo-invalido",
                "categoria": "Amigos",
            },
            {
                "nombre": "Nombre",
                "telefono": "123456789",
                "correo": "",
                "categoria": "Administración",
            },
        )
        for datos in casos_invalidos:
            with self.subTest(datos=datos):
                respuesta = self.crear_contacto(self.cliente, **datos)
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn("alerta error".encode(), respuesta.data)
                self.assertEqual(len(database.obtener_contactos(usuario_id)), 1)

        token = self.csrf(self.cliente, f"/editar/{contacto_id}")
        respuesta = self.cliente.post(
            f"/editar/{contacto_id}",
            data={
                "csrf_token": token,
                "nombre": "Ana García Actualizada",
                "telefono": "5512345678",
                "correo": "ana.actualizada@example.com",
                "categoria": "Trabajo",
            },
            follow_redirects=True,
        )
        self.assertIn("Ana García Actualizada".encode(), respuesta.data)
        contacto = database.obtener_contacto(contacto_id, usuario_id)
        self.assertEqual(contacto["categoria"], "Trabajo")
        self.assertEqual(contacto["correo"], "ana.actualizada@example.com")

        otro_cliente = aplicacion.app.test_client()
        self.assertEqual(
            self.crear_cuenta(
                otro_cliente, "Piloto Dos", "piloto2@example.test"
            ).status_code,
            302,
        )
        self.assertEqual(otro_cliente.get(f"/editar/{contacto_id}").status_code, 302)
        token = self.csrf(otro_cliente, "/")
        respuesta = otro_cliente.post(
            f"/eliminar/{contacto_id}",
            data={"csrf_token": token},
            follow_redirects=True,
        )
        self.assertIn("alerta error".encode(), respuesta.data)
        self.assertIsNotNone(database.obtener_contacto(contacto_id, usuario_id))

        token = self.csrf(self.cliente, "/")
        respuesta = self.cliente.post(
            f"/eliminar/{contacto_id}",
            data={"csrf_token": token},
            follow_redirects=True,
        )
        self.assertIn("Contacto eliminado".encode(), respuesta.data)
        self.assertIsNone(database.obtener_contacto(contacto_id, usuario_id))

        self.cliente.post(
            "/cerrar-sesion",
            data={"csrf_token": self.csrf(self.cliente, "/")},
        )
        respuesta = self.cliente.post(
            "/iniciar-sesion",
            data={
                "csrf_token": self.csrf(self.cliente, "/iniciar-sesion"),
                "correo": "piloto1@example.test",
                "contrasena": "FormulaUno2026!",
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.cliente.get("/").status_code, 200)

    def test_sql_falla_con_mensaje_explicito_y_datos_aislados(self):
        self.crear_cuenta(self.cliente, "Piloto", "piloto@example.test")
        with self.cliente.session_transaction() as sesion:
            usuario_id = sesion["usuario_id"]
        with patch(
            "app.agregar_contacto",
            side_effect=sqlite3.OperationalError("fallo de prueba"),
        ):
            respuesta = self.crear_contacto(
                self.cliente,
                nombre="Contacto",
                telefono="5512345678",
                correo="",
                categoria="Familia",
            )
        self.assertIn("No se pudo completar".encode(), respuesta.data)
        self.assertEqual(database.obtener_contactos(usuario_id), [])

    def test_fallos_de_actualizacion_y_eliminacion_muestran_error(self):
        self.crear_cuenta(self.cliente, "Piloto", "piloto@example.test")
        with self.cliente.session_transaction() as sesion:
            usuario_id = sesion["usuario_id"]
        self.crear_contacto(
            self.cliente,
            nombre="Contacto",
            telefono="5512345678",
            correo="",
            categoria="Familia",
        )
        contacto_id = database.obtener_contactos(usuario_id)[0]["id"]

        with patch(
            "app.actualizar_contacto",
            side_effect=sqlite3.OperationalError("fallo de prueba"),
        ):
            respuesta = self.cliente.post(
                f"/editar/{contacto_id}",
                data={
                    "csrf_token": self.csrf(self.cliente, f"/editar/{contacto_id}"),
                    "nombre": "Contacto actualizado",
                    "telefono": "5512345678",
                    "correo": "",
                    "categoria": "Familia",
                },
            )
        self.assertEqual(respuesta.status_code, 500)
        self.assertIn("No se pudo completar".encode(), respuesta.data)

        with patch(
            "app.eliminar_contacto",
            side_effect=sqlite3.OperationalError("fallo de prueba"),
        ):
            respuesta = self.cliente.post(
                f"/eliminar/{contacto_id}",
                data={"csrf_token": self.csrf(self.cliente, "/")},
                follow_redirects=True,
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("No se pudo completar".encode(), respuesta.data)
        self.assertIsNotNone(database.obtener_contacto(contacto_id, usuario_id))

    def test_csrf_se_requiere_en_operaciones_post(self):
        self.crear_cuenta(self.cliente, "Piloto", "piloto@example.test")
        respuesta = self.cliente.post(
            "/agregar",
            data={
                "nombre": "Contacto",
                "telefono": "5512345678",
                "correo": "",
                "categoria": "Familia",
            },
        )
        self.assertEqual(respuesta.status_code, 400)


if __name__ == "__main__":
    unittest.main()
