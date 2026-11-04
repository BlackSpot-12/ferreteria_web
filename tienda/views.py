import logging
import os

import requests
from django.contrib import messages
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.utils.http import url_has_allowed_host_and_scheme


logger = logging.getLogger(__name__)
API_BASE_URL = os.environ.get(
    "API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ROLES_WEB = {1: "admin", 2: "empleado", 3: "cliente"}
IMAGEN_PRODUCTO_DEFAULT = "tienda/producto-generico.svg"
METODOS_PAGO = ("Efectivo", "Tarjeta", "Transferencia")


def headers_api(request, extra=None):
    headers = {}
    usuario = request.session.get("usuario", {})
    token = usuario.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra:
        headers.update(extra)
    return headers


def api_request(
    request,
    method,
    path,
    *,
    authenticated=False,
    params=None,
    json_data=None,
    form_data=None,
    extra_headers=None,
):
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            params=params,
            json=json_data,
            data=form_data,
            headers=headers_api(request, extra_headers),
            timeout=10,
        )
    except requests.RequestException:
        logger.exception("Error de conexión con la API: %s %s", method, path)
        messages.error(
            request,
            "No fue posible conectarse con el servicio. Inténtalo de nuevo.",
        )
        return None

    if response.status_code == 401 and authenticated:
        request.session.pop("usuario", None)
        request.session["_api_session_expired"] = True
        request.session.modified = True
        messages.error(request, "Tu sesión expiró. Inicia sesión nuevamente.")
        logger.warning("La API rechazó la sesión: %s %s", method, path)
        return None

    if not response.ok:
        detail = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("detail")
        except ValueError:
            logger.warning(
                "La API devolvió una respuesta no JSON: %s %s",
                method,
                path,
            )
        detail = detail or f"La API respondió con estado {response.status_code}."
        logger.warning(
            "Error de API %s %s (%s): %s",
            method,
            path,
            response.status_code,
            detail,
        )
        messages.error(request, str(detail))
        return None
    return response


def api_failure(request, fallback):
    if request.session.pop("_api_session_expired", False):
        return redirect("login")
    return fallback


def _json_response(request, response, description):
    try:
        return response.json()
    except ValueError:
        logger.exception("Respuesta JSON inválida al %s", description)
        messages.error(request, "El servicio devolvió una respuesta inválida.")
        return None


def _api_list(request, path, *, authenticated=True):
    response = api_request(
        request,
        "GET",
        path,
        authenticated=authenticated,
    )
    if response is None:
        return None
    payload = _json_response(request, response, f"consultar {path}")
    if payload is None:
        return None
    if not isinstance(payload, list):
        logger.error("La API devolvió una lista inválida para %s", path)
        messages.error(request, "El servicio devolvió datos con formato inválido.")
        return None
    return payload


def _api_object(request, path, *, authenticated=True):
    response = api_request(
        request,
        "GET",
        path,
        authenticated=authenticated,
    )
    if response is None:
        return None
    payload = _json_response(request, response, f"consultar {path}")
    if payload is None:
        return None
    if not isinstance(payload, dict):
        logger.error("La API devolvió un objeto inválido para %s", path)
        messages.error(request, "El servicio devolvió datos con formato inválido.")
        return None
    return payload


def _es_sesion_expirada(request):
    return bool(request.session.get("_api_session_expired"))


def _respuesta_sesion_expirada(request):
    if _es_sesion_expirada(request):
        return api_failure(request, redirect("login"))
    return None


def _require_roles(request, allowed_roles):
    usuario = request.session.get("usuario")
    if not usuario or not usuario.get("access_token"):
        if usuario:
            request.session.pop("usuario", None)
            messages.error(request, "Inicia sesión nuevamente para continuar.")
        return redirect("login")
    if usuario.get("id_rol") not in allowed_roles:
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("inicio")
    return None


def adaptar_producto(producto, *, categoria=None, ubicacion=None):
    stock = producto.get("stock_actual")
    adaptado = {
        **producto,
        "id": producto.get("id_producto"),
        "precio": producto.get("precio_venta"),
        "medida": producto.get("medida_presentacion"),
        "descripcion": producto.get("descripcion") or "",
        "categoria": categoria,
        "categoria_id": producto.get("categoria_id"),
        "imagen": producto.get("fotografia_url") or static(IMAGEN_PRODUCTO_DEFAULT),
        "stock": stock,
        "stock_disponible": stock is not None,
        "stock_minimo": producto.get("stock_minimo"),
        "pasillo": (ubicacion or {}).get("pasillo"),
        "estanteria": (ubicacion or {}).get("estante"),
        "ubicacion_id": producto.get("ubicacion_id"),
        "precio_compra": producto.get("precio_compra"),
    }
    if stock is not None:
        adaptado["estado"] = producto.get("estado", False)
    return adaptado


def obtener_productos_api(request, *, categoria=None):
    productos = []
    offset = 0
    limite = 100
    while True:
        params = {"offset": offset, "limit": limite}
        if categoria:
            params["categoria"] = categoria
        respuesta = api_request(
            request,
            "GET",
            "/catalogo/productos",
            params=params,
        )
        if respuesta is None:
            return None
        pagina = _json_response(request, respuesta, "consultar el catálogo")
        if pagina is None:
            return None
        if not isinstance(pagina, list):
            logger.error("La API devolvió un catálogo con formato inesperado")
            messages.error(request, "El servicio devolvió un catálogo inválido.")
            return None
        productos.extend(adaptar_producto(item) for item in pagina)
        if len(pagina) < limite:
            return productos
        offset += limite


def contar_items_carrito(request):
    carrito = request.session.get("carrito", {})
    return sum(item.get("cantidad", 0) for item in carrito.values())


def inicio(request):
    usuario = request.session.get("usuario")
    if usuario and usuario.get("rol") in ("empleado", "admin"):
        return redirect("panel")

    categoria_actual = request.GET.get("categoria", "").strip()
    productos = obtener_productos_api(request, categoria=categoria_actual or None)
    if productos is None:
        productos = []
    busqueda = request.GET.get("q", "").strip()
    if busqueda:
        consulta = busqueda.casefold()
        productos = [
            producto for producto in productos
            if consulta in (producto.get("nombre") or "").casefold()
            or consulta in (producto.get("codigo") or "").casefold()
            or consulta in (producto.get("marca") or "").casefold()
            or consulta in (producto.get("medida") or "").casefold()
        ]
    return render(
        request,
        "tienda/index.html",
        {
            "productos": productos,
            "categorias": [],
            "busqueda": busqueda,
            "categoria_actual": categoria_actual,
            "cantidad_carrito": contar_items_carrito(request),
        },
    )


def detalle_producto(request, producto_id):
    usuario = request.session.get("usuario")
    if usuario and usuario.get("rol") in ("empleado", "admin"):
        return redirect("panel")
    productos = obtener_productos_api(request)
    if productos is None:
        return api_failure(request, redirect("inicio"))
    producto = next(
        (item for item in productos if item["id"] == producto_id),
        None,
    )
    if producto is None:
        messages.error(request, "El producto no está disponible.")
        return redirect("inicio")
    return render(
        request,
        "tienda/detalle.html",
        {
            "producto": producto,
            "cantidad_carrito": contar_items_carrito(request),
        },
    )


def agregar_al_carrito(request, producto_id):
    if request.method != "POST":
        return redirect("inicio")
    productos = obtener_productos_api(request)
    if productos is None:
        return api_failure(request, redirect("ver_carrito"))
    producto = next(
        (item for item in productos if item["id"] == producto_id),
        None,
    )
    if producto is None:
        messages.error(request, "El producto ya no está disponible en el catálogo.")
        return redirect("inicio")
    try:
        cantidad = int(request.POST.get("cantidad", 1))
    except (TypeError, ValueError):
        cantidad = 0
    if cantidad <= 0:
        messages.error(request, "La cantidad debe ser un entero positivo.")
    else:
        carrito = request.session.get("carrito", {})
        clave = str(producto_id)
        actual = carrito.get(clave, {}).get("cantidad", 0)
        carrito[clave] = {"cantidad": actual + cantidad}
        request.session["carrito"] = carrito
        request.session.modified = True
        messages.success(request, f"Se agregó {cantidad}x {producto['nombre']}.")
    pagina_anterior = request.META.get("HTTP_REFERER")
    return redirect(pagina_anterior or "inicio")


def actualizar_carrito(request, producto_id):
    if request.method == "POST":
        carrito = request.session.get("carrito", {})
        clave = str(producto_id)
        if clave in carrito:
            try:
                cantidad = int(request.POST.get("cantidad", 1))
            except (TypeError, ValueError):
                cantidad = -1
            if cantidad == 0:
                del carrito[clave]
            elif cantidad > 0:
                carrito[clave]["cantidad"] = cantidad
            else:
                messages.error(
                    request,
                    "La cantidad debe ser un entero positivo o cero.",
                )
            request.session["carrito"] = carrito
            request.session.modified = True
    return redirect(request.META.get("HTTP_REFERER") or "ver_carrito")


def eliminar_del_carrito(request, producto_id):
    carrito = request.session.get("carrito", {})
    carrito.pop(str(producto_id), None)
    request.session["carrito"] = carrito
    request.session.modified = True
    return redirect(request.META.get("HTTP_REFERER") or "ver_carrito")


def vaciar_carrito(request):
    request.session["carrito"] = {}
    request.session.modified = True
    return redirect(request.META.get("HTTP_REFERER") or "ver_carrito")


def calcular_totales_carrito(request, carrito):
    productos = obtener_productos_api(request)
    if productos is None:
        return None
    productos_por_id = {str(item["id"]): item for item in productos}
    items = []
    subtotal_estimado = 0
    for producto_id, carrito_item in carrito.items():
        producto = productos_por_id.get(str(producto_id))
        cantidad = carrito_item.get("cantidad", 0)
        if producto is None:
            items.append({
                "id": producto_id,
                "cantidad": cantidad,
                "disponible": False,
            })
            continue
        subtotal = producto["precio"] * cantidad
        subtotal_estimado += subtotal
        items.append({
            **producto,
            "cantidad": cantidad,
            "subtotal": subtotal,
            "disponible": True,
        })
    return {"items": items, "subtotal_estimado": subtotal_estimado}


def ver_carrito(request):
    usuario = request.session.get("usuario")
    if usuario and usuario.get("rol") in ("empleado", "admin"):
        return redirect("panel")
    resumen = calcular_totales_carrito(
        request,
        request.session.get("carrito", {}),
    )
    if resumen is None:
        resumen = {"items": [], "subtotal_estimado": None}
    return render(
        request,
        "tienda/carrito.html",
        {
            **resumen,
            "cantidad_carrito": contar_items_carrito(request),
        },
    )


def _adaptar_factura(respuesta, venta):
    datos = None
    if respuesta is not None:
        try:
            datos = respuesta.json()
        except ValueError:
            logger.exception("Respuesta JSON inválida al consultar factura POS")
    if datos is None:
        datos = {
            "id_factura": venta.get("id_venta"),
            "fecha_hora": venta.get("fecha_hora"),
            "detalles": venta.get("detalles", []),
            "subtotal": venta.get("subtotal"),
            "iva": venta.get("iva"),
            "total_pagar": venta.get("total_pagar"),
        }
    return {
        "emisor": datos.get("emisor"),
        "numero_factura": datos.get("id_factura"),
        "fecha": datos.get("fecha_hora"),
        "tipo_cliente": datos.get("tipo_cliente"),
        "cliente_nombre": datos.get("nombre_razon_social"),
        "cliente_documento": datos.get("numero_documento"),
        "cliente_correo": datos.get("correo"),
        "cliente_telefono": datos.get("telefono"),
        "cliente_direccion": datos.get("direccion"),
        "metodo_pago": datos.get("metodo_pago"),
        "items": [
            {
                "codigo": item.get("codigo"),
                "nombre": item.get("nombre"),
                "cantidad": item.get("cantidad"),
                "precio_unitario": item.get("precio_unitario"),
                "subtotal": item.get("subtotal"),
            }
            for item in datos.get("detalles", [])
        ],
        "subtotal": datos.get("subtotal"),
        "iva": datos.get("iva"),
        "total_pagar": datos.get("total_pagar"),
    }


def generar_factura(request):
    if request.method != "POST":
        return redirect("ver_carrito")
    carrito = request.session.get("carrito", {})
    if not carrito:
        messages.error(request, "El carrito está vacío.")
        return redirect("ver_carrito")
    try:
        items = [
            {"producto_id": int(producto_id), "cantidad": int(item["cantidad"])}
            for producto_id, item in carrito.items()
        ]
    except (KeyError, TypeError, ValueError):
        logger.exception("El carrito de sesión tiene un formato inválido")
        messages.error(request, "El carrito contiene productos inválidos.")
        return redirect("ver_carrito")

    usuario = request.session.get("usuario", {})
    es_pos = request.POST.get("origen_operacion") == "Punto de Venta"
    cliente = {
        "tipo_cliente": request.POST.get("tipo_cliente", "Natural"),
        "nombre_razon_social": request.POST.get("cliente_nombre", "").strip(),
        "correo": request.POST.get(
            "cliente_correo",
            usuario.get("correo", ""),
        ).strip(),
        "telefono": request.POST.get("cliente_telefono", "").strip(),
        "numero_documento": request.POST.get("cliente_documento", "").strip(),
        "direccion": request.POST.get("cliente_direccion", "").strip(),
    }
    if any(not value for value in cliente.values()):
        messages.error(
            request,
            "Completa todos los datos del cliente para continuar.",
        )
        return redirect("panel" if es_pos else "ver_carrito")

    if es_pos:
        if usuario.get("id_rol") not in (1, 2):
            messages.error(
                request,
                "Solo el personal puede registrar ventas de mostrador.",
            )
            return redirect("login")
        datos_facturacion = {
            **cliente,
            "metodo_pago": request.POST.get("metodo_pago", "Efectivo"),
        }
        respuesta = api_request(
            request,
            "POST",
            "/ventas",
            authenticated=True,
            json_data={
                "items": items,
                "datos_facturacion": datos_facturacion,
            },
        )
        if respuesta is None:
            return api_failure(request, redirect("panel"))
        venta = _json_response(request, respuesta, "registrar venta POS")
        if not isinstance(venta, dict) or not venta.get("id_venta"):
            logger.error("La API no confirmó el registro de la venta POS")
            messages.error(request, "El servicio no confirmó la venta.")
            return redirect("panel")
        request.session["carrito"] = {}
        request.session.modified = True
        factura_response = api_request(
            request,
            "GET",
            f"/ventas/{venta['id_venta']}/factura",
            authenticated=True,
        )
        sesion_expirada = _respuesta_sesion_expirada(request)
        if sesion_expirada:
            return sesion_expirada
        return render(
            request,
            "tienda/factura.html",
            {"factura": _adaptar_factura(factura_response, venta)},
        )

    if usuario and usuario.get("id_rol") != 3:
        messages.error(request, "El personal debe usar el punto de venta.")
        return redirect("panel")
    es_invitado = not usuario
    respuesta = api_request(
        request,
        "POST",
        "/pedidos/invitado" if es_invitado else "/pedidos",
        authenticated=not es_invitado,
        json_data={"items": items, "datos_cliente": cliente},
    )
    if respuesta is None:
        return api_failure(request, redirect("ver_carrito"))
    datos = _json_response(request, respuesta, "crear pedido")
    if not isinstance(datos, dict):
        return redirect("ver_carrito")
    pedido = datos.get("pedido", datos)
    pedido_id = pedido.get("id_pedido")
    if not pedido_id:
        logger.error("La API no devolvió el identificador del pedido")
        messages.error(request, "El servicio no confirmó el pedido.")
        return redirect("ver_carrito")
    if es_invitado:
        access_code = datos.get("codigo_acceso")
        if not access_code:
            logger.error("La API no devolvió el código privado del pedido invitado")
            messages.error(
                request,
                "El servicio no devolvió el código privado de consulta.",
            )
            return redirect("ver_carrito")
        codigos = request.session.get("codigos_pedido_invitado", {})
        codigos[str(pedido_id)] = access_code
        request.session["codigos_pedido_invitado"] = codigos
    request.session["carrito"] = {}
    request.session.modified = True
    messages.success(request, f"Pedido #{pedido_id} registrado.")
    return redirect("ver_factura_guardada", numero_factura=pedido_id)


def _render_comprobante_pedido(request, datos, codigo_acceso=None):
    pedido = datos.get("pedido", datos)
    return render(
        request,
        "tienda/factura.html",
        {
            "pedido": pedido,
            "items": datos.get("detalles", pedido.get("detalles") or []),
            "codigo_acceso": codigo_acceso,
            "instrucciones": datos.get("instrucciones"),
            "iva_estimado": datos.get("iva_estimado"),
            "total_estimado": datos.get("total_estimado"),
        },
    )


def ver_factura_guardada(request, numero_factura):
    usuario = request.session.get("usuario", {})
    codigos = request.session.get("codigos_pedido_invitado", {})
    codigo_acceso = codigos.get(str(numero_factura))
    if codigo_acceso:
        respuesta = api_request(
            request,
            "GET",
            "/pedidos/consulta",
            extra_headers={"X-Order-Access-Code": codigo_acceso},
        )
    elif usuario.get("access_token"):
        try:
            pedido_id = int(numero_factura)
        except (TypeError, ValueError):
            messages.error(request, "Identificador de pedido inválido.")
            return redirect("panel")
        pedido = _api_object(
            request,
            f"/pedidos/{pedido_id}",
            authenticated=True,
        )
        if pedido is None:
            return api_failure(request, redirect("panel"))
        detalles = _api_list(
            request,
            f"/pedidos/{pedido_id}/detalles",
            authenticated=True,
        )
        if detalles is None:
            return api_failure(request, redirect("panel"))
        return _render_comprobante_pedido(
            request,
            {"pedido": pedido, "detalles": detalles},
        )
    else:
        messages.error(
            request,
            "No se encontró el código privado para consultar este pedido.",
        )
        return redirect("inicio")

    if respuesta is None:
        return api_failure(
            request,
            redirect("panel" if usuario else "inicio"),
        )
    datos = _json_response(request, respuesta, "consultar pedido invitado")
    if not isinstance(datos, dict):
        return redirect("inicio")
    return _render_comprobante_pedido(request, datos, codigo_acceso)


def consultar_pedido_invitado(request):
    if request.method == "POST":
        codigo_acceso = request.POST.get("codigo_acceso", "").strip()
        if not codigo_acceso:
            messages.error(request, "Ingresa el código privado de consulta.")
        else:
            respuesta = api_request(
                request,
                "GET",
                "/pedidos/consulta",
                extra_headers={"X-Order-Access-Code": codigo_acceso},
            )
            if respuesta is None:
                return api_failure(
                    request,
                    redirect("consultar_pedido_invitado"),
                )
            datos = _json_response(
                request,
                respuesta,
                "consultar comprobante de invitado",
            )
            if not isinstance(datos, dict):
                return redirect("consultar_pedido_invitado")
            pedido_id = datos.get("pedido", {}).get("id_pedido")
            if pedido_id:
                codigos = request.session.get("codigos_pedido_invitado", {})
                codigos[str(pedido_id)] = codigo_acceso
                request.session["codigos_pedido_invitado"] = codigos
            return _render_comprobante_pedido(request, datos, codigo_acceso)
    return render(request, "tienda/consulta_pedido.html")


def _productos_panel(request, categorias, ubicaciones):
    productos = _api_list(request, "/productos")
    if productos is None:
        return None
    categorias_por_id = {
        categoria["id_categoria"]: categoria["nombre"]
        for categoria in categorias
    }
    ubicaciones_por_id = {
        ubicacion["id_ubicacion"]: ubicacion
        for ubicacion in ubicaciones
    }
    return [
        adaptar_producto(
            producto,
            categoria=categorias_por_id.get(producto.get("categoria_id")),
            ubicacion=ubicaciones_por_id.get(producto.get("ubicacion_id")),
        )
        for producto in productos
    ]


def _resumen_carrito_panel(carrito, productos):
    productos_por_id = {str(producto["id"]): producto for producto in productos}
    items = []
    subtotal_estimado = 0
    for producto_id, carrito_item in carrito.items():
        producto = productos_por_id.get(str(producto_id))
        cantidad = carrito_item.get("cantidad", 0)
        if producto is None or not producto.get("estado"):
            items.append({"id": producto_id, "cantidad": cantidad, "disponible": False})
            continue
        subtotal = producto["precio"] * cantidad
        subtotal_estimado += subtotal
        items.append({
            **producto,
            "cantidad": cantidad,
            "precio_aplicado": producto["precio"],
            "subtotal": subtotal,
            "disponible": True,
        })
    return {"items": items, "subtotal_estimado": subtotal_estimado}


def panel_view(request):
    usuario = request.session.get("usuario")
    if not usuario or not usuario.get("access_token"):
        if usuario:
            request.session.pop("usuario", None)
            messages.error(request, "Inicia sesión nuevamente para continuar.")
        return redirect("login")
    rol = usuario.get("rol")
    permisos = {
        "cliente": {"mis_pedidos"},
        "empleado": {"pos", "inventario", "pedidos"},
        "admin": {"pos", "inventario", "pedidos", "reportes", "usuarios"},
    }
    if rol not in permisos:
        request.session.pop("usuario", None)
        messages.error(request, "La sesión contiene un rol inválido. Inicia sesión.")
        return redirect("login")
    seccion = request.GET.get("seccion", "")
    if not seccion:
        seccion = "mis_pedidos" if rol == "cliente" else (
            "pos" if rol == "empleado" else "inventario"
        )
    if seccion not in permisos[rol]:
        messages.error(request, "No tienes permisos para abrir esa sección.")
        return redirect("panel")

    contexto = {
        "usuario": usuario,
        "rol": rol,
        "seccion": seccion,
        "productos": [],
        "todos_productos": [],
        "categorias": [],
        "ubicaciones": [],
        "busqueda_inv": request.GET.get("q_inv", "").strip(),
        "filtro_stock": request.GET.get("filtro_stock", "").strip(),
        "productos_agotados": [],
        "productos_bajo_stock": [],
        "productos_alto_valor": [],
        "total_por_reabastecer": 0,
        "valor_inventario_costo": 0,
        "valor_inventario_venta": 0,
        "total_ingresos_ventas": 0,
        "reporte_categorias": [],
        "productos_mas_vendidos": [],
        "ventas_pedidos": [],
        "mis_pedidos": [],
        "resumen_carrito": {"items": [], "subtotal_estimado": 0},
        "cantidad_carrito": contar_items_carrito(request),
        "producto_editar": None,
    }

    if rol == "cliente":
        pedidos = _api_list(request, "/pedidos")
        if pedidos is None:
            expired = _respuesta_sesion_expirada(request)
            if expired:
                return expired
        else:
            contexto["mis_pedidos"] = pedidos
        return render(request, "tienda/panel.html", contexto)

    categorias = _api_list(request, "/categorias")
    if categorias is None:
        expired = _respuesta_sesion_expirada(request)
        if expired:
            return expired
        categorias = []
    ubicaciones = _api_list(request, "/ubicaciones")
    if ubicaciones is None:
        expired = _respuesta_sesion_expirada(request)
        if expired:
            return expired
        ubicaciones = []
    productos = _productos_panel(request, categorias, ubicaciones)
    if productos is None:
        expired = _respuesta_sesion_expirada(request)
        if expired:
            return expired
        productos = []

    contexto["categorias"] = categorias
    contexto["ubicaciones"] = ubicaciones
    contexto["todos_productos"] = productos
    contexto["resumen_carrito"] = _resumen_carrito_panel(
        request.session.get("carrito", {}),
        productos,
    )
    productos_visibles = [
        producto for producto in productos
        if seccion != "pos" or producto.get("estado")
    ]
    busqueda = contexto["busqueda_inv"].casefold()
    if busqueda:
        productos_visibles = [
            producto for producto in productos_visibles
            if busqueda in (producto.get("codigo") or "").casefold()
            or busqueda in (producto.get("nombre") or "").casefold()
            or busqueda in (producto.get("marca") or "").casefold()
            or busqueda in (producto.get("categoria") or "").casefold()
            or busqueda in (producto.get("medida") or "").casefold()
        ]
    if contexto["filtro_stock"] == "agotados":
        productos_visibles = [
            producto for producto in productos_visibles
            if producto.get("estado") and producto.get("stock", 0) <= 0
        ]
    elif contexto["filtro_stock"] == "bajo_stock":
        productos_visibles = [
            producto for producto in productos_visibles
            if producto.get("estado")
            and 0 < producto.get("stock", 0) <= producto.get("stock_minimo", 0)
        ]
    contexto["productos"] = productos_visibles
    contexto["productos_agotados"] = [
        producto for producto in productos
        if producto.get("estado") and producto.get("stock", 0) <= 0
    ]
    contexto["productos_bajo_stock"] = [
        producto for producto in productos
        if producto.get("estado")
        and 0 < producto.get("stock", 0) <= producto.get("stock_minimo", 0)
    ]
    contexto["total_por_reabastecer"] = (
        len(contexto["productos_agotados"])
        + len(contexto["productos_bajo_stock"])
    )
    contexto["valor_inventario_costo"] = sum(
        producto.get("stock", 0) * (producto.get("precio_compra") or 0)
        for producto in productos
        if producto.get("estado")
    )
    contexto["valor_inventario_venta"] = sum(
        producto.get("stock", 0) * (producto.get("precio") or 0)
        for producto in productos
        if producto.get("estado")
    )
    contexto["productos_alto_valor"] = [
        producto for producto in productos
        if producto.get("estado") and (producto.get("precio") or 0) >= 25
    ]
    editar_id = request.GET.get("editar_id")
    if editar_id:
        contexto["producto_editar"] = next(
            (producto for producto in productos if str(producto["id"]) == editar_id),
            None,
        )

    if seccion == "pedidos":
        pedidos = _api_list(request, "/pedidos")
        if pedidos is None:
            expired = _respuesta_sesion_expirada(request)
            if expired:
                return expired
        else:
            contexto["ventas_pedidos"] = pedidos

    if seccion == "reportes":
        inventario = _api_object(request, "/reportes/inventario")
        if inventario is None:
            expired = _respuesta_sesion_expirada(request)
            if expired:
                return expired
        else:
            contexto["valor_inventario_costo"] = inventario.get(
                "valor_inventario_compra", 0
            )
            contexto["valor_inventario_venta"] = inventario.get(
                "valor_inventario_venta", 0
            )
            contexto["reporte_categorias"] = [
                {
                    "categoria": fila.get("categoria"),
                    "cantidad_productos": fila.get("productos"),
                    "unidades_stock": fila.get("unidades"),
                    "valor_total": fila.get("valor_venta"),
                }
                for fila in inventario.get("por_categoria", [])
            ]
        ventas = _api_object(request, "/reportes/ventas")
        if ventas is None:
            expired = _respuesta_sesion_expirada(request)
            if expired:
                return expired
        else:
            contexto["total_ingresos_ventas"] = ventas.get("ingresos", 0)
            contexto["productos_mas_vendidos"] = [
                {
                    "codigo": fila.get("codigo"),
                    "nombre": fila.get("nombre"),
                    "categoria": None,
                    "unidades_vendidas": fila.get("cantidad_vendida"),
                    "ingresos_generados": fila.get("ingresos"),
                }
                for fila in ventas.get("productos_mas_vendidos", [])
            ]

    return render(request, "tienda/panel.html", contexto)


def guardar_producto(request):
    denegado = _require_roles(request, (1, 2))
    if denegado:
        return denegado
    if request.method != "POST":
        return redirect("/panel/?seccion=inventario")
    producto_id = request.POST.get("producto_id", "").strip()
    try:
        payload = {
            "codigo": request.POST.get("codigo", "").strip(),
            "nombre": request.POST.get("nombre", "").strip(),
            "marca": request.POST.get("marca", "").strip() or None,
            "medida_presentacion": request.POST.get("medida", "").strip() or None,
            "descripcion": request.POST.get("descripcion", "").strip() or None,
            "precio_compra": request.POST.get("precio_compra", "").strip(),
            "precio_venta": request.POST.get("precio_venta", "").strip(),
            "stock_actual": int(request.POST.get("stock_actual", "0")),
            "stock_minimo": int(request.POST.get("stock_minimo", "0")),
            "estado": request.POST.get("estado") == "on",
            "fotografia_url": request.POST.get("fotografia_url", "").strip() or None,
            "categoria_id": int(request.POST.get("categoria_id", "")),
            "ubicacion_id": int(request.POST.get("ubicacion_id", "")),
        }
        if producto_id:
            int(producto_id)
    except (TypeError, ValueError):
        messages.error(request, "Revisa los valores numéricos del producto.")
        return redirect("/panel/?seccion=inventario")

    method = "PUT" if producto_id else "POST"
    path = f"/productos/{producto_id}" if producto_id else "/productos"
    response = api_request(
        request,
        method,
        path,
        authenticated=True,
        json_data=payload,
    )
    if response is None:
        return api_failure(request, redirect("/panel/?seccion=inventario"))
    messages.success(
        request,
        "Producto guardado correctamente en la API.",
    )
    return redirect("/panel/?seccion=inventario")


def eliminar_producto(request, producto_id):
    denegado = _require_roles(request, (1, 2))
    if denegado:
        return denegado
    if request.method != "POST":
        return redirect("/panel/?seccion=inventario")
    response = api_request(
        request,
        "DELETE",
        f"/productos/{producto_id}",
        authenticated=True,
    )
    if response is None:
        return api_failure(request, redirect("/panel/?seccion=inventario"))
    messages.success(request, "Producto eliminado del inventario.")
    return redirect("/panel/?seccion=inventario")


def agregar_categoria(request):
    denegado = _require_roles(request, (1, 2))
    if denegado:
        return denegado
    if request.method != "POST":
        return redirect("/panel/?seccion=inventario")
    nombre = request.POST.get("nombre_categoria", "").strip()
    response = api_request(
        request,
        "POST",
        "/categorias",
        authenticated=True,
        json_data={"nombre": nombre},
    )
    if response is None:
        return api_failure(request, redirect("/panel/?seccion=inventario"))
    messages.success(request, f"Categoría '{nombre}' agregada.")
    return redirect("/panel/?seccion=inventario")


def cambiar_estado_pedido(request, numero_factura):
    denegado = _require_roles(request, (1, 2))
    if denegado:
        return denegado
    if request.method != "POST":
        return redirect("/panel/?seccion=pedidos")
    try:
        pedido_id = int(numero_factura)
    except (TypeError, ValueError):
        messages.error(request, "Identificador de pedido inválido.")
        return redirect("/panel/?seccion=pedidos")
    estado = request.POST.get("estado_pedido", "")
    if estado == "Entregado":
        metodo_pago = request.POST.get("metodo_pago", "")
        if metodo_pago not in METODOS_PAGO:
            messages.error(request, "Selecciona un método de pago válido.")
            return redirect("/panel/?seccion=pedidos")
        method = "POST"
        path = f"/pedidos/{pedido_id}/entregar"
        payload = {"metodo_pago": metodo_pago}
    elif estado in ("En preparacion", "Listo"):
        method = "PUT"
        path = f"/pedidos/{pedido_id}"
        payload = {"estado": estado}
    else:
        messages.error(request, "Selecciona una transición de pedido válida.")
        return redirect("/panel/?seccion=pedidos")
    response = api_request(
        request,
        method,
        path,
        authenticated=True,
        json_data=payload,
    )
    if response is None:
        return api_failure(request, redirect("/panel/?seccion=pedidos"))
    if estado == "Entregado":
        venta = _json_response(request, response, "cobrar y entregar pedido")
        if isinstance(venta, dict):
            messages.success(
                request,
                f"Pedido entregado. Venta #{venta.get('id_venta')} por "
                f"${venta.get('total_pagar')}.",
            )
    else:
        messages.success(request, f"Estado del pedido #{pedido_id} actualizado.")
    return redirect("/panel/?seccion=pedidos")


def guardar_usuario(request):
    denegado = _require_roles(request, (1,))
    if denegado:
        return denegado
    if request.method != "POST":
        return redirect("/panel/?seccion=usuarios")
    payload = {
        "Nombres": request.POST.get("Nombres", "").strip(),
        "apellidos": request.POST.get("apellidos", "").strip(),
        "correo": request.POST.get("correo", "").strip(),
        "password": request.POST.get("password", ""),
        "rol_id": 2,
    }
    response = api_request(
        request,
        "POST",
        "/usuarios",
        authenticated=True,
        json_data=payload,
    )
    if response is None:
        return api_failure(request, redirect("/panel/?seccion=usuarios"))
    messages.success(request, "Empleado creado correctamente.")
    return redirect("/panel/?seccion=usuarios")


def login_view(request):
    next_url = request.GET.get("next") or request.POST.get("next") or ""
    if request.method == "POST":
        correo = request.POST.get("correo", "").strip()
        password = request.POST.get("password", "")
        respuesta = api_request(
            request,
            "POST",
            "/auth/login",
            form_data={"username": correo, "password": password},
        )
        if respuesta is not None:
            datos_api = _json_response(request, respuesta, "iniciar sesión")
            if not isinstance(datos_api, dict):
                return render(request, "tienda/login.html", {"next": next_url})
            rol_id = datos_api.get("id_rol")
            token = datos_api.get("access_token")
            if rol_id not in ROLES_WEB or not token:
                logger.error("La API devolvió datos incompletos al iniciar sesión")
                messages.error(request, "El servicio no devolvió una sesión válida.")
                return render(request, "tienda/login.html", {"next": next_url})
            usuario = {
                "access_token": token,
                "token_type": datos_api.get("token_type", "bearer"),
                "id_rol": rol_id,
                "nombre": datos_api.get("nombre", ""),
                "correo": datos_api.get("correo", correo),
                "rol": ROLES_WEB[rol_id],
            }
            request.session.cycle_key()
            request.session["usuario"] = usuario
            request.session.modified = True
            messages.success(request, f"Bienvenido, {usuario['nombre']}.")
            if usuario["rol"] in ("empleado", "admin"):
                return redirect("panel")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("inicio")
    return render(request, "tienda/login.html", {"next": next_url})


def logout_view(request):
    request.session.pop("usuario", None)
    request.session.pop("_api_session_expired", None)
    request.session.modified = True
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect("inicio")


def registro_view(request):
    if request.method == "POST":
        payload = {
            "Nombres": request.POST.get("Nombres", "").strip(),
            "apellidos": request.POST.get("apellidos", "").strip(),
            "correo": request.POST.get("correo", "").strip(),
            "password": request.POST.get("password", ""),
        }
        respuesta = api_request(
            request,
            "POST",
            "/usuarios/registro",
            json_data=payload,
        )
        if respuesta is not None:
            messages.success(
                request,
                "Cuenta creada. Inicia sesión con tu correo.",
            )
            return redirect("login")
    return render(request, "tienda/registro.html")
