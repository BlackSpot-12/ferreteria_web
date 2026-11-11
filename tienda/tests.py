from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from tienda.views import a_decimal


class AutenticacionAPITests(TestCase):
    @patch("tienda.views.requests.request")
    def test_login_rechaza_correo_invalido_sin_llamar_a_la_api(self, request_api):
        response = self.client.post(
            reverse("login"),
            {"correo": "no-es-correo", "password": "password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ingresa un correo electrónico válido.")
        request_api.assert_not_called()

    @patch("tienda.views.requests.request")
    def test_registro_rechaza_correo_invalido_sin_llamar_a_la_api(self, request_api):
        response = self.client.post(
            reverse("registro"),
            {
                "Nombres": "Ana",
                "apellidos": "Pérez",
                "correo": "correo-invalido",
                "password": "password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ingresa un correo electrónico válido.")
        request_api.assert_not_called()

    @patch("tienda.views.requests.request")
    def test_registro_exige_ocho_caracteres_sin_llamar_a_la_api(self, request_api):
        response = self.client.post(
            reverse("registro"),
            {
                "Nombres": "Ana",
                "apellidos": "Pérez",
                "correo": "ana@example.com",
                "password": "short",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "entre 8 y 255 caracteres")
        request_api.assert_not_called()

    @patch("tienda.views.requests.request")
    def test_login_envia_formulario_y_guarda_solo_token_y_datos_basicos(self, request_api):
        response_api = Mock(status_code=200, ok=True)
        response_api.json.return_value = {
            "access_token": "token-prueba",
            "token_type": "bearer",
            "id_rol": 2,
            "nombre": "Ana",
            "correo": "ana@example.com",
        }
        request_api.return_value = response_api

        response = self.client.post(
            reverse("login"),
            {"correo": "ana@example.com", "password": "no-guardar"},
        )

        self.assertRedirects(response, reverse("panel"), fetch_redirect_response=False)
        request_api.assert_called_once()
        call = request_api.call_args.kwargs
        self.assertEqual(call["data"], {"username": "ana@example.com", "password": "no-guardar"})
        self.assertIsNone(call["json"])
        self.assertEqual(call["timeout"], 10)
        usuario = self.client.session["usuario"]
        self.assertEqual(usuario["rol"], "empleado")
        self.assertEqual(usuario["access_token"], "token-prueba")
        self.assertNotIn("password", usuario)

    @patch("tienda.views.requests.request")
    def test_registro_envia_esquema_de_cliente_y_no_inicia_sesion(self, request_api):
        response_api = Mock(status_code=201, ok=True)
        response_api.json.return_value = {
            "id_usuario": 12,
            "Nombres": "Ana",
            "apellidos": "Pérez",
            "correo": "ana@example.com",
            "rol_id": 3,
        }
        request_api.return_value = response_api

        response = self.client.post(
            reverse("registro"),
            {
                "Nombres": "Ana",
                "apellidos": "Pérez",
                "correo": "ana@example.com",
                "password": "no-guardar",
            },
        )

        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        request_api.assert_called_once()
        self.assertEqual(
            request_api.call_args.kwargs["json"],
            {
                "Nombres": "Ana",
                "apellidos": "Pérez",
                "correo": "ana@example.com",
                "password": "no-guardar",
            },
        )
        self.assertNotIn("usuario", self.client.session)

    @patch("tienda.views.requests.request")
    def test_registro_confirma_guia_de_verificacion_sin_auto_login(self, request_api):
        response_api = Mock(status_code=201, ok=True)
        response_api.json.return_value = {"id_usuario": 12}
        request_api.return_value = response_api

        response = self.client.post(
            reverse("registro"),
            {
                "Nombres": "Ana",
                "apellidos": "Pérez",
                "correo": "ana@example.com",
                "password": "clave-segura",
            },
            follow=True,
        )

        self.assertContains(response, "verifica la dirección antes de iniciar sesión")
        self.assertNotIn("usuario", self.client.session)

    @patch("tienda.views.requests.request")
    def test_registro_muestra_detail_de_api(self, request_api):
        response_api = Mock(status_code=400, ok=False)
        response_api.json.return_value = {"detail": "El correo ya está registrado"}
        request_api.return_value = response_api

        response = self.client.post(
            reverse("registro"),
            {
                "Nombres": "Ana",
                "apellidos": "Pérez",
                "correo": "ana@example.com",
                "password": "no-guardar",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El correo ya está registrado")

    @patch("tienda.views.requests.request")
    def test_recuperacion_password_no_revela_si_existe_el_correo(self, request_api):
        response_api = Mock(status_code=200, ok=True)
        response_api.json.return_value = {
            "detail": "Si el correo está registrado, recibirás instrucciones"
        }
        request_api.return_value = response_api
        url = reverse("recuperar_password")

        existente = self.client.post(url, {"correo": "ana@example.com"})
        no_registrado = self.client.post(url, {"correo": "nadie@example.com"})

        self.assertEqual(existente.status_code, 200)
        self.assertEqual(no_registrado.status_code, 200)
        self.assertEqual(existente.content, no_registrado.content)
        self.assertContains(existente, "Si el correo está registrado")
        self.assertNotContains(existente, "ana@example.com")
        self.assertNotContains(no_registrado, "nadie@example.com")
        self.assertEqual(request_api.call_count, 2)
        for call in request_api.call_args_list:
            self.assertEqual(call.args[0], "POST")
            self.assertTrue(call.args[1].endswith("/auth/olvide-password"))
            self.assertIn(call.kwargs["json"]["correo"], {
                "ana@example.com",
                "nadie@example.com",
            })

    @patch("tienda.views.requests.request")
    def test_restablecer_password_envia_token_y_muestra_exito(self, request_api):
        response_api = Mock(status_code=200, ok=True)
        response_api.json.return_value = {
            "detail": "La contraseña se restableció correctamente"
        }
        request_api.return_value = response_api

        response = self.client.post(
            reverse("restablecer_password"),
            {"token": "token-prueba", "password": "nueva-clave-segura"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contraseña actualizada")
        request_api.assert_called_once()
        self.assertTrue(
            request_api.call_args.args[1].endswith("/auth/restablecer-password")
        )
        self.assertEqual(
            request_api.call_args.kwargs["json"],
            {"token": "token-prueba", "password": "nueva-clave-segura"},
        )

    @patch("tienda.views.requests.request")
    def test_restablecer_password_muestra_error_de_api(self, request_api):
        response_api = Mock(status_code=400, ok=False)
        response_api.json.return_value = {"detail": "Token inválido o expirado"}
        request_api.return_value = response_api

        response = self.client.post(
            reverse("restablecer_password"),
            {"token": "token-caducado", "password": "nueva-clave-segura"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Token inválido o expirado")

    @patch("tienda.views.requests.request")
    def test_verificacion_correo_muestra_form_y_reenvia_token_al_api(self, request_api):
        response_api = Mock(status_code=200, ok=True)
        response_api.json.return_value = {"detail": "Correo verificado"}
        request_api.return_value = response_api
        url = reverse("verificar_correo")

        page = self.client.get(url, {"token": "token-email"})
        response = self.client.post(url, {"token": "token-email"})

        self.assertContains(page, 'name="token"')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Correo verificado")
        request_api.assert_called_once()
        self.assertEqual(
            request_api.call_args.kwargs["json"],
            {"token": "token-email"},
        )
        self.assertTrue(
            request_api.call_args.args[1].endswith("/usuarios/verificar-correo")
        )


class CatalogoAPITests(TestCase):
    @patch("tienda.views.requests.request")
    def test_catalogo_usa_endpoint_publico_y_adapta_producto(self, request_api):
        response_api = Mock(status_code=200, ok=True)
        response_api.json.return_value = [
            {
                "id_producto": 4,
                "codigo": "FER-004",
                "nombre": "Llave inglesa",
                "marca": "Acero",
                "medida_presentacion": "10 pulgadas",
                "precio_venta": 12.5,
                "fotografia_url": None,
            }
        ]
        request_api.return_value = response_api

        response = self.client.get(reverse("inicio"))

        self.assertEqual(response.status_code, 200)
        request_api.assert_called_once()
        call = request_api.call_args.kwargs
        self.assertTrue(request_api.call_args.args[1].endswith("/catalogo/productos"))
        self.assertEqual(call["params"], {"offset": 0, "limit": 100})
        producto = response.context["productos"][0]
        self.assertEqual(producto["id"], 4)
        self.assertEqual(producto["precio"], 12.5)
        self.assertEqual(producto["medida"], "10 pulgadas")
        self.assertIsNone(producto["categoria"])
        self.assertFalse(producto["stock_disponible"])
        self.assertIn("producto-generico.svg", producto["imagen"])

    @patch("tienda.views.requests.request")
    def test_catalogo_filtra_con_slider_y_pagina_resultados(self, request_api):
        response_api = Mock(status_code=200, ok=True)
        response_api.json.return_value = [
            {
                "id_producto": product_id,
                "codigo": f"FER-{product_id:03}",
                "nombre": f"Producto {product_id}",
                "precio_venta": str(product_id),
                "fotografia_url": None,
            }
            for product_id in range(1, 26)
        ]
        request_api.return_value = response_api

        response = self.client.get(
            reverse("inicio"),
            {"max_price": "15", "page": "2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 15)
        self.assertEqual(response.context["total_paginas"], 2)
        self.assertEqual(response.context["pagina_actual"], 2)
        self.assertEqual(
            [producto["id"] for producto in response.context["productos"]],
            [13, 14, 15],
        )
        self.assertContains(response, 'value="15"')
        self.assertContains(response, "?max_price=15&amp;page=1")

    @patch("tienda.views.requests.request")
    def test_carrito_muestra_estimado_sin_reglas_de_mayoreo_ni_iva_local(self, request_api):
        response_api = Mock(status_code=200, ok=True)
        response_api.json.return_value = [
            {
                "id_producto": 4,
                "codigo": "FER-004",
                "nombre": "Llave inglesa",
                "marca": None,
                "medida_presentacion": None,
                "precio_venta": 12.5,
                "fotografia_url": None,
            }
        ]
        request_api.return_value = response_api
        session = self.client.session
        session["carrito"] = {"4": {"cantidad": 2}}
        session.save()

        response = self.client.get(reverse("ver_carrito"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Subtotal estimado de productos")
        self.assertContains(response, "$25.00")
        self.assertNotContains(response, "Mayoreo")
        self.assertNotContains(response, "IVA (13%)")


class PedidoAPITests(TestCase):
    def setUp(self):
        session = self.client.session
        session["usuario"] = {
            "access_token": "token-cliente",
            "id_rol": 3,
            "nombre": "Ana Pérez",
            "correo": "ana@example.com",
            "rol": "cliente",
        }
        session["carrito"] = {"5": {"cantidad": 2}}
        session.save()

    @patch("tienda.views.requests.request")
    def test_cliente_crea_pedido_con_token_y_payload_de_api(self, request_api):
        response_api = Mock(status_code=201, ok=True)
        response_api.json.return_value = {
            "id_pedido": 77,
            "estado": "Pendiente",
            "total_pedido": 25,
        }
        request_api.return_value = response_api

        response = self.client.post(
            reverse("generar_factura"),
            {
                "tipo_cliente": "Natural",
                "cliente_nombre": "Ana Pérez",
                "cliente_documento": "00000000-0",
                "cliente_correo": "ana@example.com",
                "cliente_telefono": "2222-2222",
                "cliente_direccion": "San Salvador",
            },
        )

        self.assertRedirects(
            response,
            reverse("ver_factura_guardada", kwargs={"numero_factura": 77}),
            fetch_redirect_response=False,
        )
        self.assertTrue(request_api.call_args.args[1].endswith("/pedidos"))
        self.assertEqual(
            request_api.call_args.kwargs["headers"],
            {"Authorization": "Bearer token-cliente"},
        )
        self.assertEqual(
            request_api.call_args.kwargs["json"],
            {
                "items": [{"producto_id": 5, "cantidad": 2}],
                "datos_cliente": {
                    "tipo_cliente": "Natural",
                    "nombre_razon_social": "Ana Pérez",
                    "correo": "ana@example.com",
                    "telefono": "2222-2222",
                    "numero_documento": "00000000-0",
                    "direccion": "San Salvador",
                },
            },
        )
        self.assertEqual(self.client.session["carrito"], {})

    @patch("tienda.views.requests.request")
    def test_invitado_crea_pedido_y_se_guarda_codigo_privado(self, request_api):
        response_api = Mock(status_code=201, ok=True)
        response_api.json.return_value = {
            "pedido": {"id_pedido": 78, "estado": "Pendiente"},
            "codigo_acceso": "a" * 12,
            "instrucciones": "Guarda el comprobante.",
            "detalles": [],
        }
        request_api.return_value = response_api
        session = self.client.session
        session.pop("usuario", None)
        session["carrito"] = {"5": {"cantidad": 1}}
        session.save()

        response = self.client.post(
            reverse("generar_factura"),
            {
                "tipo_cliente": "Natural",
                "cliente_nombre": "Cliente",
                "cliente_documento": "00000000-0",
                "cliente_correo": "cliente@example.com",
                "cliente_telefono": "2222-2222",
                "cliente_direccion": "San Salvador",
            },
        )

        self.assertRedirects(
            response,
            reverse("ver_factura_guardada", kwargs={"numero_factura": 78}),
            fetch_redirect_response=False,
        )
        self.assertTrue(request_api.call_args.args[1].endswith("/pedidos/invitado"))
        self.assertEqual(request_api.call_args.kwargs["headers"], {})
        self.assertEqual(
            self.client.session["codigos_pedido_invitado"]["78"],
            "a" * 12,
        )

    @patch("tienda.views.requests.request")
    def test_comprobante_invitado_consulta_api_con_codigo_privado(self, request_api):
        response_api = Mock(status_code=200, ok=True)
        response_api.json.return_value = {
            "pedido": {
                "id_pedido": 78,
                "estado": "Pendiente",
                "fecha_hora": "2026-11-03T10:00:00Z",
                "nombre_cliente": "Cliente",
                "correo_cliente": "cliente@example.com",
                "telefono_cliente": "2222-2222",
                "direccion_cliente": "San Salvador",
                "total_pedido": 25,
            },
            "detalles": [],
            "iva_estimado": 3.25,
            "total_estimado": 28.25,
        }
        request_api.return_value = response_api
        session = self.client.session
        session["codigos_pedido_invitado"] = {"78": "a" * 12}
        session.save()

        response = self.client.get(
            reverse("ver_factura_guardada", kwargs={"numero_factura": 78})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Código privado de consulta")
        self.assertContains(response, "Total estimado por la API")
        self.assertEqual(
            request_api.call_args.kwargs["headers"]["X-Order-Access-Code"],
            "a" * 12,
        )


class PanelAPITests(TestCase):
    def setUp(self):
        session = self.client.session
        session["usuario"] = {
            "access_token": "token-empleado",
            "id_rol": 2,
            "nombre": "Empleado",
            "correo": "empleado@example.com",
            "rol": "empleado",
        }
        session.save()

    def hacer_propietario(self):
        session = self.client.session
        session["usuario"].update({
            "access_token": "token-propietario",
            "id_rol": 1,
            "nombre": "Propietario",
            "correo": "propietario@example.com",
            "rol": "admin",
        })
        session.save()

    @staticmethod
    def respuesta_api(datos=None, status_code=200):
        respuesta = Mock(status_code=status_code, ok=True)
        respuesta.json.return_value = datos
        return respuesta

    @patch("tienda.views.requests.request")
    def test_guardar_producto_envia_campos_api_y_bearer(self, request_api):
        session = self.client.session
        session["usuario"]["id_rol"] = 1
        session["usuario"]["rol"] = "admin"
        session.save()
        request_api.return_value = Mock(status_code=201, ok=True)

        response = self.client.post(
            reverse("guardar_producto"),
            {
                "codigo": "FER-100",
                "nombre": "Taladro",
                "marca": "Marca",
                "medida": "12V",
                "precio_compra": "20.00",
                "precio_venta": "30.00",
                "stock_actual": "5",
                "stock_minimo": "1",
                "estado": "on",
                "categoria_id": "4",
                "ubicacion_id": "8",
                "fotografia_url": "",
                "descripcion": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        call = request_api.call_args
        self.assertEqual(call.args[0], "POST")
        self.assertTrue(call.args[1].endswith("/productos"))
        self.assertEqual(
            call.kwargs["headers"],
            {"Authorization": "Bearer token-empleado"},
        )
        self.assertEqual(
            call.kwargs["json"],
            {
                "codigo": "FER-100",
                "nombre": "Taladro",
                "marca": "Marca",
                "medida_presentacion": "12V",
                "descripcion": None,
                "precio_compra": "20.00",
                "precio_venta": "30.00",
                "stock_actual": 5,
                "stock_minimo": 1,
                "estado": True,
                "fotografia_url": None,
                "categoria_id": 4,
                "ubicacion_id": 8,
            },
        )

    @patch("tienda.views.requests.request")
    def test_cliente_no_puede_eliminar_producto(self, request_api):
        session = self.client.session
        session["usuario"]["id_rol"] = 3
        session["usuario"]["rol"] = "cliente"
        session.save()

        response = self.client.post(
            reverse("eliminar_producto", kwargs={"producto_id": 22})
        )

        self.assertRedirects(response, reverse("inicio"), fetch_redirect_response=False)
        request_api.assert_not_called()

    @patch("tienda.views.requests.request")
    def test_empleado_no_puede_escribir_producto_ni_categoria(self, request_api):
        respuesta = self.client.post(
            reverse("guardar_producto"),
            {},
        )
        self.assertRedirects(
            respuesta,
            reverse("inicio"),
            fetch_redirect_response=False,
        )
        respuesta = self.client.post(
            reverse("agregar_categoria"),
            {"nombre_categoria": "Herramientas"},
        )
        self.assertRedirects(
            respuesta,
            reverse("inicio"),
            fetch_redirect_response=False,
        )
        request_api.assert_not_called()

    @patch("tienda.views.requests.request")
    def test_empleado_no_accede_a_reportes_usuarios_ni_pagos(self, request_api):
        for seccion in ("reportes", "usuarios", "pagos"):
            response = self.client.get(
                reverse("panel"),
                {"seccion": seccion},
            )
            self.assertRedirects(
                response,
                reverse("panel"),
                fetch_redirect_response=False,
            )
        request_api.assert_not_called()

    @patch("tienda.views.requests.request")
    def test_propietario_inactiva_y_reactiva_producto_con_rutas_api_correctas(
        self,
        request_api,
    ):
        self.hacer_propietario()
        request_api.side_effect = [
            self.respuesta_api({"estado": False}),
            self.respuesta_api({"estado": True}),
        ]

        self.client.post(
            reverse("eliminar_producto", kwargs={"producto_id": 22}),
        )
        self.client.post(
            reverse("eliminar_producto", kwargs={"producto_id": 22}),
            {"accion": "reactivar"},
        )

        self.assertEqual(request_api.call_args_list[0].args[0], "DELETE")
        self.assertTrue(request_api.call_args_list[0].args[1].endswith("/productos/22"))
        self.assertEqual(request_api.call_args_list[1].args[0], "PUT")
        self.assertEqual(
            request_api.call_args_list[1].kwargs["json"],
            {"estado": True},
        )

    @patch("tienda.views.requests.request")
    def test_401_cierra_sesion_y_redirige_a_login(self, request_api):
        response_api = Mock(status_code=401, ok=False)
        response_api.json.return_value = {"detail": "Token expirado"}
        request_api.return_value = response_api

        response = self.client.get(reverse("panel"))

        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.assertNotIn("usuario", self.client.session)

    @patch("tienda.views.requests.request")
    def test_panel_pos_renderiza_datos_api(self, request_api):
        responses = []
        for data in (
            [{"id_categoria": 4, "nombre": "Herramientas"}],
            [{"id_ubicacion": 8, "pasillo": "A", "estante": "2", "nivel": "1"}],
            [
                {
                    "id_producto": 31,
                    "codigo": "FER-031",
                    "nombre": "Taladro",
                    "marca": "Marca",
                    "medida_presentacion": "12V",
                    "precio_compra": 20,
                    "precio_venta": 30,
                    "stock_actual": 5,
                    "stock_minimo": 1,
                    "estado": True,
                    "fotografia_url": None,
                    "categoria": "Herramientas",
                    "pasillo": "A",
                    "estante": "2",
                    "nivel": "1",
                }
            ],
        ):
            api_response = Mock(status_code=200, ok=True)
            api_response.json.return_value = data
            responses.append(api_response)
        request_api.side_effect = responses

        response = self.client.get(reverse("panel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Taladro")
        self.assertContains(response, "A / 2")
        self.assertEqual(request_api.call_count, 3)
        self.assertTrue(request_api.call_args_list[2].args[1].endswith("/productos/buscar"))
        self.assertNotContains(response, "Guardar Producto")

    @patch("tienda.views.requests.request")
    def test_panel_empleado_normaliza_cadenas_none_e_invalidos(self, request_api):
        responses = []
        for data in (
            [{"id_categoria": 4, "nombre": "Herramientas"}],
            [{"id_ubicacion": 8, "pasillo": "A", "estante": "2", "nivel": "1"}],
            [
                {
                    "id_producto": 31,
                    "codigo": "FER-031",
                    "nombre": "Taladro",
                    "precio_compra": "5.25",
                    "precio_venta": "30.00",
                    "stock_actual": "4",
                    "stock_minimo": "2",
                    "categoria": "Herramientas",
                    "pasillo": "A",
                    "estante": "2",
                    "nivel": "1",
                },
                {
                    "id_producto": 32,
                    "codigo": "FER-032",
                    "nombre": "Producto sin cifras",
                    "precio_compra": None,
                    "precio_venta": None,
                    "stock_actual": None,
                    "stock_minimo": None,
                    "categoria": "Herramientas",
                },
                {
                    "id_producto": 33,
                    "codigo": "FER-033",
                    "nombre": "Producto con cifras inválidas",
                    "precio_compra": "inválido",
                    "precio_venta": "no es precio",
                    "stock_actual": "desconocido",
                    "stock_minimo": "desconocido",
                    "categoria": "Herramientas",
                },
            ],
        ):
            api_response = Mock(status_code=200, ok=True)
            api_response.json.return_value = data
            responses.append(api_response)
        request_api.side_effect = responses
        session = self.client.session
        session["carrito"] = {"31": {"cantidad": "2"}}
        session.save()

        response = self.client.get(reverse("panel"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["valor_inventario_costo"], Decimal("21.00"))
        self.assertEqual(response.context["valor_inventario_venta"], Decimal("120.00"))
        self.assertEqual(
            response.context["resumen_carrito"]["subtotal_estimado"],
            Decimal("60.00"),
        )
        self.assertEqual(
            {producto["id"] for producto in response.context["productos_alto_valor"]},
            {31},
        )
        self.assertEqual(request_api.call_count, 3)

    @patch("tienda.views.requests.request")
    def test_panel_pedidos_envia_filtros_a_cola_compartida(self, request_api):
        request_api.side_effect = [
            self.respuesta_api([]),
            self.respuesta_api([]),
            self.respuesta_api([]),
            self.respuesta_api([]),
        ]

        response = self.client.get(
            reverse("panel"),
            {
                "seccion": "pedidos",
                "estado": "Listo",
                "fecha_inicio": "2026-11-01",
                "fecha_fin": "2026-11-10",
                "cliente": "Ana",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            request_api.call_args.kwargs["params"],
            {
                "estado": "Listo",
                "fecha_inicio": "2026-11-01",
                "fecha_fin": "2026-11-10",
                "cliente": "Ana",
            },
        )
        self.assertContains(response, "Cola compartida de pedidos WEB")
        self.assertContains(response, 'name="cliente"')

    @patch("tienda.views.requests.request")
    def test_panel_propietario_lista_usuarios_sin_contraseñas(self, request_api):
        self.hacer_propietario()
        cuenta = {
            "id_usuario": 14,
            "Nombres": "Empleado",
            "apellidos": "Ejemplo",
            "correo": "empleado@example.com",
            "rol_id": 2,
            "activo": False,
        }
        request_api.side_effect = [
            self.respuesta_api([]),
            self.respuesta_api([]),
            self.respuesta_api([]),
            self.respuesta_api([cuenta]),
        ]

        response = self.client.get(reverse("panel"), {"seccion": "usuarios"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["usuarios"], [cuenta])
        self.assertContains(response, "empleado@example.com")
        self.assertContains(response, "Revocar sesiones")
        self.assertNotContains(response, "password_hash")
        self.assertTrue(request_api.call_args.args[1].endswith("/usuarios"))

    @patch("tienda.views.requests.request")
    def test_propietario_actualiza_estado_y_revoca_sesiones_de_usuario(
        self,
        request_api,
    ):
        self.hacer_propietario()
        request_api.return_value = self.respuesta_api({"activo": False})

        response = self.client.post(
            reverse("cambiar_estado_usuario", kwargs={"usuario_id": 14}),
            {"activo": "false"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(request_api.call_args.args[0], "PUT")
        self.assertTrue(request_api.call_args.args[1].endswith("/usuarios/14/estado"))
        self.assertEqual(request_api.call_args.kwargs["json"], {"activo": False})

        request_api.return_value = self.respuesta_api({"detail": "sesiones revocadas"})
        self.client.post(
            reverse("revocar_sesiones_usuario", kwargs={"usuario_id": 14}),
        )
        self.assertEqual(request_api.call_args.args[0], "POST")
        self.assertTrue(request_api.call_args.args[1].endswith("/usuarios/14/logout-all"))

    @patch("tienda.views.requests.request")
    def test_propietario_revoca_sus_sesiones_y_sale_de_la_web(self, request_api):
        self.hacer_propietario()
        request_api.return_value = self.respuesta_api({"detail": "revocadas"})

        response = self.client.post(reverse("revocar_mis_sesiones"))

        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.assertTrue(request_api.call_args.args[1].endswith("/auth/logout-all"))
        self.assertNotIn("usuario", self.client.session)

    @patch("tienda.views.requests.request")
    def test_panel_pagos_filtra_y_muestra_auditoria(self, request_api):
        self.hacer_propietario()
        pago = {
            "id_pago": 4,
            "venta_id": 8,
            "usuario_id": 2,
            "metodo_pago": "Tarjeta",
            "referencia": "REF-01",
            "monto": "45.25",
            "fecha_hora": "2026-11-10T12:00:00Z",
        }
        request_api.side_effect = [
            self.respuesta_api([]),
            self.respuesta_api([]),
            self.respuesta_api([]),
            self.respuesta_api([pago]),
        ]

        response = self.client.get(
            reverse("panel"),
            {
                "seccion": "pagos",
                "fecha_inicio": "2026-11-01",
                "fecha_fin": "2026-11-10",
                "metodo_pago": "Tarjeta",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auditoría de pagos")
        self.assertContains(response, "REF-01")
        self.assertEqual(
            request_api.call_args.kwargs["params"],
            {
                "fecha_inicio": "2026-11-01",
                "fecha_fin": "2026-11-10",
                "metodo_pago": "Tarjeta",
            },
        )

    @patch("tienda.views.requests.request")
    def test_pos_incluye_referencia_opcional_para_pago_no_monetario(self, request_api):
        session = self.client.session
        session["carrito"] = {"31": {"cantidad": 2}}
        session.save()
        request_api.side_effect = [
            self.respuesta_api(
                {"id_venta": 51, "subtotal": "20.00", "iva": "2.60", "total_pagar": "22.60"},
                status_code=201,
            ),
            self.respuesta_api({"id_factura": 51, "detalles": []}),
        ]

        response = self.client.post(
            reverse("generar_factura"),
            {
                "origen_operacion": "Punto de Venta",
                "tipo_cliente": "Natural",
                "cliente_nombre": "Cliente",
                "cliente_documento": "00000000-0",
                "cliente_correo": "cliente@example.com",
                "cliente_telefono": "2222-2222",
                "cliente_direccion": "Sucursal",
                "metodo_pago": "Tarjeta",
                "referencia_pago": "  TX-451 ",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            request_api.call_args_list[0].kwargs["json"]["datos_facturacion"],
            {
                "tipo_cliente": "Natural",
                "nombre_razon_social": "Cliente",
                "correo": "cliente@example.com",
                "telefono": "2222-2222",
                "numero_documento": "00000000-0",
                "direccion": "Sucursal",
                "metodo_pago": "Tarjeta",
                "referencia_pago": "TX-451",
            },
        )

    @patch("tienda.views.requests.request")
    def test_entrega_pedido_envia_referencia_opcional(self, request_api):
        request_api.return_value = self.respuesta_api(
            {"id_venta": 52, "total_pagar": "12.00"}
        )

        response = self.client.post(
            reverse(
                "cambiar_estado_pedido",
                kwargs={"numero_factura": "33"},
            ),
            {
                "estado_pedido": "Entregado",
                "metodo_pago": "Transferencia",
                "referencia_pago": "TR-1",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(request_api.call_args.args[1].endswith("/pedidos/33/entregar"))
        self.assertEqual(
            request_api.call_args.kwargs["json"],
            {
                "metodo_pago": "Transferencia",
                "referencia_pago": "TR-1",
            },
        )

    @patch("tienda.views.requests.request")
    def test_busqueda_invitado_exige_codigo_de_doce_caracteres(self, request_api):
        response = self.client.post(
            reverse("consultar_pedido_invitado"),
            {"codigo_acceso": "short"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "exactamente 12 caracteres")
        request_api.assert_not_called()

    @patch("tienda.views.requests.request")
    def test_panel_propietario_normaliza_montos_de_reportes(self, request_api):
        session = self.client.session
        session["usuario"] = {
            "access_token": "token-propietario",
            "id_rol": 1,
            "nombre": "Propietario",
            "correo": "propietario@example.com",
            "rol": "admin",
        }
        session.save()

        def api_response(data):
            response = Mock(status_code=200, ok=True)
            response.json.return_value = data
            return response

        request_api.side_effect = [
            api_response([]),
            api_response([]),
            api_response([]),
            api_response({
                "total_productos": None,
                "unidades_disponibles": "dato inválido",
                "productos_bajo_stock": "desconocido",
                "productos_sin_stock": None,
                "valor_inventario_compra": None,
                "valor_inventario_venta": "monto inválido",
                "por_categoria": [
                    {
                        "categoria": "Herramientas",
                        "productos": 1,
                        "unidades": "4",
                        "valor_venta": "12.50",
                    },
                    {
                        "categoria": "Sin datos",
                        "productos": None,
                        "unidades": None,
                        "valor_venta": None,
                    },
                ],
            }),
            api_response({
                "ingresos": "125.50",
                "productos_mas_vendidos": [
                    {
                        "codigo": "FER-031",
                        "nombre": "Taladro",
                        "cantidad_vendida": "2",
                        "ingresos": None,
                    },
                ],
            }),
        ]

        response = self.client.get(reverse("panel") + "?seccion=reportes")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["valor_inventario_costo"],
            Decimal("0"),
        )
        self.assertEqual(
            response.context["valor_inventario_venta"],
            Decimal("0"),
        )
        self.assertEqual(response.context["total_productos"], 0)
        self.assertEqual(response.context["unidades_disponibles"], 0)
        self.assertEqual(response.context["total_por_reabastecer"], 0)
        self.assertEqual(
            response.context["total_ingresos_ventas"],
            Decimal("125.50"),
        )
        self.assertEqual(
            response.context["reporte_categorias"][0]["valor_total"],
            Decimal("12.50"),
        )
        self.assertEqual(
            response.context["productos_mas_vendidos"][0]["ingresos_generados"],
            Decimal("0"),
        )
        self.assertEqual(request_api.call_count, 5)

    @patch("tienda.views.requests.request")
    def test_reporte_usa_kpis_inventario_productos_top_y_rango_de_ventas(
        self,
        request_api,
    ):
        self.hacer_propietario()
        producto = {
            "id_producto": 31,
            "codigo": "FER-031",
            "nombre": "Taladro",
            "marca": "Marca",
            "medida_presentacion": "12V",
            "precio_compra": "20.00",
            "precio_venta": "30.00",
            "stock_actual": 2,
            "stock_minimo": 1,
            "estado": True,
            "categoria_id": 4,
            "ubicacion_id": 8,
        }
        inventario = {
            "total_productos": 10,
            "unidades_disponibles": 40,
            "valor_inventario_compra": "500.00",
            "valor_inventario_venta": "900.00",
            "productos_bajo_stock": 1,
            "productos_sin_stock": 1,
            "productos_reponer": [
                {
                    "producto_id": 31,
                    "codigo": "FER-031",
                    "nombre": "Taladro",
                    "categoria": "Herramientas",
                    "stock_actual": 1,
                    "stock_minimo": 2,
                    "valor_compra": "20.00",
                    "valor_venta": "30.00",
                },
                {
                    "producto_id": 32,
                    "codigo": "FER-032",
                    "nombre": "Martillo",
                    "categoria": "Herramientas",
                    "stock_actual": 0,
                    "stock_minimo": 1,
                    "valor_compra": "0.00",
                    "valor_venta": "0.00",
                },
            ],
            "productos_mayor_valor": [
                {
                    "producto_id": 31,
                    "codigo": "FER-031",
                    "nombre": "Taladro",
                    "categoria": "Herramientas",
                    "stock_actual": 2,
                    "stock_minimo": 1,
                    "valor_compra": "40.00",
                    "valor_venta": "60.00",
                },
            ],
            "por_categoria": [
                {
                    "categoria": "Herramientas",
                    "productos": 1,
                    "unidades": 2,
                    "valor_venta": "60.00",
                },
            ],
        }
        ventas = {
            "fecha_inicio": "2026-11-01",
            "fecha_fin": "2026-11-10",
            "total_ventas": 3,
            "ingresos": "100.00",
            "productos_mas_vendidos": [
                {
                    "producto_id": 31,
                    "codigo": "FER-031",
                    "nombre": "Taladro",
                    "cantidad_vendida": 4,
                    "ingresos": "120.00",
                },
            ],
        }
        request_api.side_effect = [
            self.respuesta_api([{"id_categoria": 4, "nombre": "Herramientas"}]),
            self.respuesta_api([]),
            self.respuesta_api([producto]),
            self.respuesta_api(inventario),
            self.respuesta_api(ventas),
        ]

        response = self.client.get(
            reverse("panel"),
            {
                "seccion": "reportes",
                "fecha_inicio": "2026-11-01",
                "fecha_fin": "2026-11-10",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 10)
        self.assertEqual(response.context["unidades_disponibles"], 40)
        self.assertEqual(response.context["total_por_reabastecer"], 2)
        self.assertEqual(len(response.context["productos_agotados"]), 1)
        self.assertEqual(len(response.context["productos_bajo_stock"]), 1)
        self.assertEqual(
            response.context["productos_alto_valor"][0]["valor_inventario"],
            Decimal("60.00"),
        )
        self.assertEqual(response.context["total_ventas"], 3)
        self.assertEqual(
            response.context["productos_mas_vendidos"][0]["categoria"],
            "Herramientas",
        )
        self.assertEqual(
            request_api.call_args_list[4].kwargs["params"],
            {
                "fecha_inicio": "2026-11-01",
                "fecha_fin": "2026-11-10",
            },
        )


class EmailPanelAPITests(TestCase):
    def setUp(self):
        self.set_usuario(2, "empleado")

    def set_usuario(self, id_rol, rol):
        session = self.client.session
        session["usuario"] = {
            "access_token": "token-prueba",
            "id_rol": id_rol,
            "nombre": "Cuenta",
            "correo": "cuenta@example.com",
            "rol": rol,
        }
        session.save()

    @staticmethod
    def respuesta_api(datos=None, status_code=200):
        response = Mock(status_code=status_code, ok=status_code < 400)
        response.json.return_value = datos
        return response

    @patch("tienda.views.requests.request")
    def test_cliente_ve_banner_segun_estado_real_de_verificacion(self, request_api):
        self.set_usuario(3, "cliente")
        request_api.side_effect = [
            self.respuesta_api([]),
            self.respuesta_api({"verificado": False, "verificado_en": None}),
        ]

        response = self.client.get(reverse("panel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verifica tu correo")
        self.assertContains(response, reverse("reenviar_verificacion"))
        self.assertTrue(
            request_api.call_args_list[1].args[1].endswith(
                "/usuarios/me/verificacion"
            )
        )

    @patch("tienda.views.requests.request")
    def test_reenvio_verificacion_usa_post_y_muestra_confirmacion_api(
        self,
        request_api,
    ):
        self.set_usuario(3, "cliente")
        request_api.return_value = self.respuesta_api(
            {"detail": "Si el correo está pendiente, recibirás un mensaje"}
        )

        response = self.client.post(reverse("reenviar_verificacion"))

        self.assertRedirects(response, reverse("panel"), fetch_redirect_response=False)
        self.assertEqual(request_api.call_args.args[0], "POST")
        self.assertTrue(
            request_api.call_args.args[1].endswith(
                "/usuarios/me/reenviar-verificacion"
            )
        )
        self.assertIn(
            "Si el correo está pendiente, recibirás un mensaje",
            [str(message) for message in get_messages(response.wsgi_request)],
        )

    @patch("tienda.views.requests.request")
    def test_reenvio_verificacion_muestra_error_api(self, request_api):
        self.set_usuario(3, "cliente")
        request_api.return_value = self.respuesta_api(
            {"detail": "Espera al menos dos minutos"},
            status_code=429,
        )

        response = self.client.post(reverse("reenviar_verificacion"))

        self.assertRedirects(response, reverse("panel"), fetch_redirect_response=False)
        self.assertIn(
            "Espera al menos dos minutos",
            [str(message) for message in get_messages(response.wsgi_request)],
        )

    @patch("tienda.views.requests.request")
    def test_panel_solo_muestra_reenvio_factura_para_pedido_con_venta_id(
        self,
        request_api,
    ):
        request_api.side_effect = [
            self.respuesta_api([]),
            self.respuesta_api([]),
            self.respuesta_api([]),
            self.respuesta_api(
                [
                    {"id_pedido": 4, "estado": "Entregado", "venta_id": 81},
                    {"id_pedido": 5, "estado": "Pendiente", "venta_id": None},
                ]
            ),
        ]

        response = self.client.get(reverse("panel"), {"seccion": "pedidos"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reenviar factura por correo")
        self.assertContains(
            response,
            reverse("reenviar_factura_email", kwargs={"venta_id": 81}),
        )
        self.assertNotContains(
            response,
            reverse("reenviar_factura_email", kwargs={"venta_id": 5}),
        )

    @patch("tienda.views.requests.request")
    def test_reenvio_factura_exige_rol_y_responde_con_estado_api(
        self,
        request_api,
    ):
        request_api.return_value = self.respuesta_api(
            {"detail": "Se solicitó el reenvío de la factura"},
            status_code=202,
        )
        url = reverse("reenviar_factura_email", kwargs={"venta_id": 81})

        response = self.client.post(url)

        self.assertRedirects(response, reverse("panel"), fetch_redirect_response=False)
        self.assertEqual(request_api.call_args.args[0], "POST")
        self.assertTrue(
            request_api.call_args.args[1].endswith(
                "/ventas/81/factura/email"
            )
        )
        self.assertIn(
            "Se solicitó el reenvío de la factura",
            [str(message) for message in get_messages(response.wsgi_request)],
        )

        self.set_usuario(3, "cliente")
        request_api.reset_mock()
        forbidden = self.client.post(url)
        self.assertRedirects(forbidden, reverse("inicio"), fetch_redirect_response=False)
        request_api.assert_not_called()

    @patch("tienda.views.requests.request")
    def test_error_reenvio_factura_no_cambia_sesion(self, request_api):
        request_api.return_value = self.respuesta_api(
            {"detail": "No hay datos de facturación para esta venta"},
            status_code=404,
        )
        session_before = dict(self.client.session["usuario"])

        response = self.client.post(
            reverse("reenviar_factura_email", kwargs={"venta_id": 81})
        )

        self.assertRedirects(response, reverse("panel"), fetch_redirect_response=False)
        self.assertEqual(self.client.session["usuario"], session_before)
        self.assertIn(
            "No hay datos de facturación para esta venta",
            [str(message) for message in get_messages(response.wsgi_request)],
        )


class DecimalConversionTests(TestCase):
    def test_a_decimal_convierte_valores_y_usa_defecto_seguro(self):
        self.assertEqual(a_decimal(5), Decimal("5"))
        self.assertEqual(a_decimal(1.25), Decimal("1.25"))
        self.assertEqual(a_decimal("5.25"), Decimal("5.25"))
        self.assertEqual(a_decimal(None), Decimal("0"))
        self.assertEqual(a_decimal("no numérico"), Decimal("0"))
        self.assertEqual(a_decimal(float("nan")), Decimal("0"))
