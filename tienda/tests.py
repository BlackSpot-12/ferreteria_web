from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse


class AutenticacionAPITests(TestCase):
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
            "codigo_acceso": "a" * 32,
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
            "a" * 32,
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
        session["codigos_pedido_invitado"] = {"78": "a" * 32}
        session.save()

        response = self.client.get(
            reverse("ver_factura_guardada", kwargs={"numero_factura": 78})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Código privado de consulta")
        self.assertContains(response, "Total estimado por la API")
        self.assertEqual(
            request_api.call_args.kwargs["headers"]["X-Order-Access-Code"],
            "a" * 32,
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

    @patch("tienda.views.requests.request")
    def test_guardar_producto_envia_campos_api_y_bearer(self, request_api):
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
                    "categoria_id": 4,
                    "ubicacion_id": 8,
                    "descripcion": "Taladro eléctrico",
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
