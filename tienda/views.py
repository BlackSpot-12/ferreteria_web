import os
import random
import requests
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages


API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8001/api")

CATEGORIAS_SISTEMA = [
    "Plomería",
    "Electricidad",
    "Pinturas",
    "Herramientas",
    "Materiales de construcción",
    "Artículos para el hogar",
    "Muebles",
    "Maquinaria",
    "Tornillería y accesorios",
]


def obtener_imagen_articulo(articulo_wiki, url_respaldo="", lang="es"):
    try:
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{articulo_wiki}"
        respuesta = requests.get(
            url, headers={"User-Agent": "BimetalicaWeb/1.0"}, timeout=3)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            if "originalimage" in datos and "source" in datos["originalimage"]:
                return datos["originalimage"]["source"]
            if "thumbnail" in datos and "source" in datos["thumbnail"]:
                return datos["thumbnail"]["source"]
    except requests.RequestException:
        pass
    return url_respaldo


PRODUCTOS_MEMORIA = [
    {
        "id": 1,
        "codigo": "HER-001",
        "nombre": "Martillo de Acero Forjado",
        "marca": "Truper",
        "medida": "16 oz",
        "categoria": "Herramientas",
        "descripcion": "Martillo de uña curva con cabeza de acero pulido y mango ergonómico.",
        "especificaciones": "Cabeza de acero al carbono forjado con acabado pulido anticorrosión y mango ergonómico antideslizante que reduce la vibración al golpear.",
        "precio_compra": 8.00,
        "precio": 12.50,
        "precio_mayoreo": 10.50,
        "stock": 45,
        "stock_minimo": 10,
        "pasillo": "Pasillo 1",
        "estanteria": "Estante A-2",
        "estado": "Activo",
        "imagen": "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?auto=format&fit=crop&w=700&q=80"
    },
    {
        "id": 2,
        "codigo": "PLO-014",
        "nombre": "Llave Mezcladora Cromada con Ducha",
        "marca": "Helvex",
        "medida": "Conexión 1/2 pulgada",
        "categoria": "Plomería",
        "descripcion": "Grifo mezclador de doble comando en acero inoxidable cromado con regadera manual.",
        "especificaciones": "Cuerpo sólido de latón con recubrimiento de cromo brillante resistente al sarro y la corrosión. Incluye manguera flexible y ducha telefónica.",
        "precio_compra": 22.00,
        "precio": 34.50,
        "precio_mayoreo": 29.90,
        "stock": 28,
        "stock_minimo": 8,
        "pasillo": "Pasillo 3",
        "estanteria": "Estante B-1",
        "estado": "Activo",
        "imagen": "https://tse1.mm.bing.net/th?q=Grifo+mezclador+cromado+con+ducha+regadera+manual+fondo+blanco&w=600&h=600&c=7"
    },
    {
        "id": 3,
        "codigo": "ELE-008",
        "nombre": "Foco LED Alta Eficiencia",
        "marca": "Sylvania",
        "medida": "12W Rosca E27",
        "categoria": "Electricidad",
        "descripcion": "Bombilla LED de luz blanca fría con ahorro de energía del 85%.",
        "especificaciones": "Temperatura de color 6500K (Luz de día), rosca estándar E27, encendido instantáneo y vida útil de 25,000 horas.",
        "precio_compra": 1.60,
        "precio": 2.95,
        "precio_mayoreo": 2.40,
        "stock": 8,
        "stock_minimo": 15,
        "pasillo": "Pasillo 2",
        "estanteria": "Estante C-4",
        "estado": "Activo",
        "imagen": obtener_imagen_articulo("Lámpara_LED", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/LED_bulbs.jpg/640px-LED_bulbs.jpg")
    },
    {
        "id": 4,
        "codigo": "MAQ-005",
        "nombre": "Taladro Percutor Inalámbrico",
        "marca": "DeWalt",
        "medida": "1/2 pulgada - 20V Max",
        "categoria": "Maquinaria",
        "descripcion": "Taladro rotomartillo inalámbrico DeWalt de velocidad variable y reversible.",
        "especificaciones": "Motor sin escobillas de alto rendimiento, batería de ion de litio de 20V, mandril de ajuste rápido de 1/2 pulgada y luz LED integrada.",
        "precio_compra": 95.00,
        "precio": 135.00,
        "precio_mayoreo": 122.00,
        "stock": 4,
        "stock_minimo": 5,
        "pasillo": "Pasillo 1",
        "estanteria": "Vitrina V-2",
        "estado": "Activo",
        "imagen": "https://images.unsplash.com/photo-1572981779307-38b8cabb2407?auto=format&fit=crop&w=700&q=80"
    },
    {
        "id": 5,
        "codigo": "TOR-012",
        "nombre": "Juego de Llaves Combinadas",
        "marca": "Stanley",
        "medida": "Set 12 piezas (8mm a 19mm)",
        "categoria": "Tornillería y accesorios",
        "descripcion": "Juego de llaves mecánicas combinadas forjadas en acero cromo vanadio.",
        "especificaciones": "Extremo abierto y extremo de corona de 12 puntas para mayor torque sin barrer las tuercas. Acabado cromado satinado resistente al óxido.",
        "precio_compra": 18.50,
        "precio": 27.90,
        "precio_mayoreo": 24.50,
        "stock": 19,
        "stock_minimo": 6,
        "pasillo": "Pasillo 1",
        "estanteria": "Estante A-5",
        "estado": "Activo",
        "imagen": "https://tse1.mm.bing.net/th?q=Juego+de+Llaves+Combinadas+Stanley+12+piezas+cromo+vanadio&w=600&h=600&c=7"
    },
    {
        "id": 6,
        "codigo": "PIN-010",
        "nombre": "Brocha Profesional de Cerda Natural",
        "marca": "Sherwin-Williams",
        "medida": "4 pulgadas - Uso General",
        "categoria": "Pinturas",
        "descripcion": "Brocha de alta retención para aplicación uniforme de pinturas acrílicas y esmaltes.",
        "especificaciones": "Cerdas 100% naturales seleccionadas con virola de acero inoxidable y mango ergonómico de madera barnizada.",
        "precio_compra": 3.50,
        "precio": 6.50,
        "precio_mayoreo": 5.25,
        "stock": 0,
        "stock_minimo": 6,
        "pasillo": "Pasillo 4",
        "estanteria": "Estante P-3",
        "estado": "Agotado",
        "imagen": "https://tse1.mm.bing.net/th?q=Brocha+Profesional+Sherwin+Williams+4+pulgadas&w=600&h=600&c=7"
    },
    {
        "id": 7,
        "codigo": "CON-002",
        "nombre": "Rodillo Profesional para Construcción",
        "marca": "Truper",
        "medida": "9 pulgadas - Felpa 3/4\"",
        "categoria": "Materiales de construcción",
        "descripcion": "Rodillo antigoteo de alta densidad para superficies rugosas, concreto y block.",
        "especificaciones": "Armazón metálico reforzado con mango ergonómico roscado para extensión y felpa tejida de alta retención para acabados en obra.",
        "precio_compra": 3.20,
        "precio": 5.75,
        "precio_mayoreo": 4.80,
        "stock": 65,
        "stock_minimo": 15,
        "pasillo": "Pasillo 4",
        "estanteria": "Estante P-1",
        "estado": "Activo",
        "imagen": "https://images.unsplash.com/photo-1562259949-e8e7689d7828?auto=format&fit=crop&w=700&q=80"
    },
    {
        "id": 8,
        "codigo": "HOG-004",
        "nombre": "Cinta Métrica Profesional Flexómetro",
        "marca": "Pretul",
        "medida": "5 metros (16 pies) - Cinta 3/4\"",
        "categoria": "Artículos para el hogar",
        "descripcion": "Flexómetro con carcasa resistente a impactos, freno de seguro y clip para cinturón.",
        "especificaciones": "Cinta metálica graduada en centímetros y pulgadas con recubrimiento de laca para evitar el desgaste de la numeración.",
        "precio_compra": 2.80,
        "precio": 4.90,
        "precio_mayoreo": 3.95,
        "stock": 30,
        "stock_minimo": 8,
        "pasillo": "Pasillo 2",
        "estanteria": "Estante H-2",
        "estado": "Activo",
        "imagen": obtener_imagen_articulo("Cinta_métrica", "https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Tape_measure_colored.jpeg/640px-Tape_measure_colored.jpeg")
    },
    {
        "id": 9,
        "codigo": "MUE-001",
        "nombre": "Banco de Trabajo Industrial para Taller",
        "marca": "Urrea",
        "medida": "150 x 75 x 85 cm (Capacidad 500 kg)",
        "categoria": "Muebles",
        "descripcion": "Mesa de trabajo reforzada con cubierta de madera sólida y estructura de acero.",
        "especificaciones": "Cubierta de madera de alta densidad tratada contra humedad e impactos, estructura metálica con pintura electrostática y repisa inferior organizadora.",
        "precio_compra": 110.00,
        "precio": 165.00,
        "precio_mayoreo": 149.00,
        "stock": 6,
        "stock_minimo": 3,
        "pasillo": "Bodega Central",
        "estanteria": "Área Muebles M-1",
        "estado": "Activo",
        "imagen": "https://tse1.mm.bing.net/th?q=Mesa+banco+de+trabajo+industrial+Urrea+cubierta+madera+estructura+acero&w=600&h=600&c=7"
    }
]
USUARIOS_MEMORIA = [
    {"id": 1, "usuario": "david", "correo": "david@ferreteria.com",
        "password": "123", "nombre": "David", "rol": "cliente"},
    {"id": 2, "usuario": "empleado", "correo": "empleado@bimetalica.com",
        "password": "123", "nombre": "Carlos Rivas", "rol": "empleado"},
    {"id": 3, "usuario": "admin", "correo": "admin@bimetalica.com",
        "password": "123", "nombre": "Roberto Gómez", "rol": "admin"},
]

VENTAS_PEDIDOS_MEMORIA = []


def obtener_productos_api():
    try:
        respuesta = requests.get(f"{API_BASE_URL}/productos/", timeout=1)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            if isinstance(datos, list) and len(datos) > 0:
                return datos
    except requests.RequestException:
        pass
    return PRODUCTOS_MEMORIA


def contar_items_carrito(request):
    carrito = request.session.get('carrito', {})
    return sum(item['cantidad'] for item in carrito.values())


def inicio(request):
    usuario = request.session.get('usuario')
    if usuario and usuario.get('rol') in ['empleado', 'admin']:
        return redirect('panel')

    productos = obtener_productos_api()
    busqueda = request.GET.get('q', '').strip()
    categoria_actual = request.GET.get('categoria', '').strip()

    if categoria_actual:
        productos = [p for p in productos if p.get(
            'categoria', '').lower() == categoria_actual.lower()]

    if busqueda:
        q_lower = busqueda.lower()
        productos = [
            p for p in productos
            if q_lower in p.get('nombre', '').lower()
            or q_lower in p.get('descripcion', '').lower()
            or q_lower in p.get('codigo', '').lower()
            or q_lower in p.get('marca', '').lower()
            or q_lower in p.get('medida', '').lower()
            or q_lower in p.get('categoria', '').lower()
        ]

    contexto = {
        'productos': productos,
        'categorias': CATEGORIAS_SISTEMA,
        'busqueda': busqueda,
        'categoria_actual': categoria_actual,
        'cantidad_carrito': contar_items_carrito(request),
    }
    return render(request, 'tienda/index.html', contexto)


def detalle_producto(request, producto_id):
    usuario = request.session.get('usuario')
    if usuario and usuario.get('rol') in ['empleado', 'admin']:
        return redirect('panel')

    productos = obtener_productos_api()
    producto = next((p for p in productos if p['id'] == producto_id), None)

    if not producto:
        return redirect('inicio')

    contexto = {
        'producto': producto,
        'cantidad_carrito': contar_items_carrito(request),
    }
    return render(request, 'tienda/detalle.html', contexto)


def agregar_al_carrito(request, producto_id):
    productos = obtener_productos_api()
    producto = next((p for p in productos if p['id'] == producto_id), None)

    if producto:
        if producto.get('stock', 0) <= 0:
            messages.error(
                request, f"El producto {producto['nombre']} está agotado actualmente.")
        else:
            carrito = request.session.get('carrito', {})
            pid_str = str(producto_id)
            cantidad_agregar = int(request.POST.get('cantidad', 1))

            if pid_str in carrito:
                nueva_cantidad = carrito[pid_str]['cantidad'] + \
                    cantidad_agregar
                carrito[pid_str]['cantidad'] = min(
                    nueva_cantidad, producto['stock'])
                carrito[pid_str]['imagen'] = producto.get('imagen', '')
            else:
                carrito[pid_str] = {
                    'id': producto['id'],
                    'codigo': producto['codigo'],
                    'nombre': producto['nombre'],
                    'marca': producto.get('marca', 'General'),
                    'medida': producto.get('medida', 'Estándar'),
                    'categoria': producto['categoria'],
                    'precio': float(producto['precio']),
                    'precio_mayoreo': float(producto.get('precio_mayoreo', producto['precio'])),
                    'stock': producto['stock'],
                    'imagen': producto.get('imagen', ''),
                    'cantidad': min(cantidad_agregar, producto['stock']),
                }

            request.session['carrito'] = carrito
            request.session.modified = True
            messages.success(
                request, f"Se agregó {cantidad_agregar}x {producto['nombre']}.")

    pagina_anterior = request.META.get('HTTP_REFERER')
    if pagina_anterior:
        return redirect(pagina_anterior)
    return redirect('inicio')


def actualizar_carrito(request, producto_id):
    if request.method == 'POST':
        carrito = request.session.get('carrito', {})
        pid_str = str(producto_id)

        if pid_str in carrito:
            nueva_cantidad = int(request.POST.get('cantidad', 1))
            if nueva_cantidad > 0:
                carrito[pid_str]['cantidad'] = min(
                    nueva_cantidad, carrito[pid_str]['stock'])
            else:
                del carrito[pid_str]
            request.session['carrito'] = carrito
            request.session.modified = True

    pagina_anterior = request.META.get('HTTP_REFERER')
    if pagina_anterior:
        return redirect(pagina_anterior)
    return redirect('ver_carrito')


def eliminar_del_carrito(request, producto_id):
    carrito = request.session.get('carrito', {})
    pid_str = str(producto_id)

    if pid_str in carrito:
        del carrito[pid_str]
        request.session['carrito'] = carrito
        request.session.modified = True

    pagina_anterior = request.META.get('HTTP_REFERER')
    if pagina_anterior:
        return redirect(pagina_anterior)
    return redirect('ver_carrito')


def vaciar_carrito(request):
    request.session['carrito'] = {}
    request.session.modified = True

    pagina_anterior = request.META.get('HTTP_REFERER')
    if pagina_anterior:
        return redirect(pagina_anterior)

    usuario = request.session.get('usuario')
    if usuario and usuario.get('rol') in ['empleado', 'admin']:
        return redirect('panel')
    return redirect('ver_carrito')


def calcular_totales_carrito(carrito, descuento_adicional=0.0):
    items_procesados = []
    total_bruto = 0.0
    ahorro_mayoreo = 0.0

    for item in carrito.values():
        cantidad = item['cantidad']
        es_mayoreo = cantidad >= 12
        precio_aplicado = item['precio_mayoreo'] if es_mayoreo else item['precio']
        subtotal = cantidad * precio_aplicado

        if es_mayoreo:
            ahorro_mayoreo += cantidad * \
                (item['precio'] - item['precio_mayoreo'])

        items_procesados.append({
            **item,
            'es_mayoreo': es_mayoreo,
            'precio_aplicado': precio_aplicado,
            'subtotal': subtotal,
        })
        total_bruto += subtotal

    total_pagar = max(0.0, total_bruto - descuento_adicional)
    subtotal_sin_iva = total_pagar / 1.13 if total_pagar > 0 else 0.0
    iva = total_pagar - subtotal_sin_iva

    return {
        'items': items_procesados,
        'subtotal_sin_iva': subtotal_sin_iva,
        'iva': iva,
        'descuento_adicional': descuento_adicional,
        'total_pagar': total_pagar,
        'ahorro_mayoreo': ahorro_mayoreo + descuento_adicional,
    }


def ver_carrito(request):
    usuario = request.session.get('usuario')
    if usuario and usuario.get('rol') in ['empleado', 'admin']:
        return redirect('panel')

    carrito = request.session.get('carrito', {})
    resumen = calcular_totales_carrito(carrito)

    contexto = {
        **resumen,
        'cantidad_carrito': contar_items_carrito(request),
    }
    return render(request, 'tienda/carrito.html', contexto)


def generar_factura(request):
    carrito = request.session.get('carrito', {})

    if request.method == 'POST' and carrito:
        cliente_nombre = request.POST.get('cliente_nombre', '').strip()
        cliente_documento = request.POST.get('cliente_documento', '').strip()

        if not cliente_nombre or not cliente_documento:
            messages.error(
                request, "Por favor completa el Nombre del Cliente y su DUI / NIT para emitir la factura.")
            pagina_anterior = request.META.get('HTTP_REFERER')
            if pagina_anterior:
                return redirect(pagina_anterior)
            return redirect('panel')

        descuento_extra = float(request.POST.get(
            'descuento_extra', 0.0) or 0.0)
        resumen = calcular_totales_carrito(carrito, descuento_extra)

        cliente_giro = request.POST.get('cliente_giro', '').strip()
        cliente_direccion = request.POST.get(
            'cliente_direccion', 'San Salvador').strip()
        tipo_cliente = request.POST.get('tipo_cliente', 'Cliente Natural')
        tipo_comprobante = "Crédito Fiscal" if tipo_cliente == "Cliente Jurídico" else "Consumidor Final"
        metodo_pago = request.POST.get('metodo_pago', 'Efectivo')
        origen_operacion = request.POST.get(
            'origen_operacion', 'Pedido en Línea')

        numero_factura = f"FAC-2026-{random.randint(10000, 99999)}"
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")

        usuario_sesion = request.session.get('usuario', {})
        rol_actual = usuario_sesion.get('rol', 'cliente')

        estado_inicial = "Entregado / Completado" if rol_actual in [
            'empleado', 'admin'] and origen_operacion == 'Punto de Venta' else "Pendiente de preparación"

        for item in carrito.values():
            for p in PRODUCTOS_MEMORIA:
                if p['id'] == item['id']:
                    p['stock'] = max(0, p['stock'] - item['cantidad'])
                    p['estado'] = "Agotado" if p['stock'] == 0 else "Activo"

        datos_factura = {
            'numero_factura': numero_factura,
            'fecha': fecha_actual,
            'cliente_nombre': cliente_nombre,
            'cliente_documento': cliente_documento,
            'cliente_giro': cliente_giro,
            'cliente_direccion': cliente_direccion,
            'tipo_cliente': tipo_cliente,
            'tipo_comprobante': tipo_comprobante,
            'metodo_pago': metodo_pago,
            'origen_operacion': origen_operacion,
            'estado_pedido': estado_inicial,
            'usuario_correo': usuario_sesion.get('correo', 'invitado'),
            'atendido_por': usuario_sesion.get('nombre', 'Autoservicio Web'),
            **resumen,
        }

        VENTAS_PEDIDOS_MEMORIA.insert(0, datos_factura)

        try:
            requests.post(f"{API_BASE_URL}/ventas/",
                          json=datos_factura, timeout=1)
        except requests.RequestException:
            pass

        request.session['ultima_factura'] = datos_factura
        request.session['carrito'] = {}
        request.session.modified = True

        return render(request, 'tienda/factura.html', {'factura': datos_factura})

    ultima_factura = request.session.get('ultima_factura')
    if ultima_factura:
        return render(request, 'tienda/factura.html', {'factura': ultima_factura})

    return redirect('inicio')


def ver_factura_guardada(request, numero_factura):
    factura = next(
        (f for f in VENTAS_PEDIDOS_MEMORIA if f['numero_factura'] == numero_factura), None)
    if factura:
        return render(request, 'tienda/factura.html', {'factura': factura})
    return redirect('panel')


def panel_view(request):
    usuario = request.session.get('usuario')
    if not usuario:
        return redirect('login')

    rol = usuario.get('rol', 'cliente')
    productos = obtener_productos_api()
    seccion = request.GET.get('seccion', '')

    if rol == 'admin' and seccion == 'pos':
        seccion = 'inventario'

    if not seccion:
        if rol == 'cliente':
            seccion = 'mis_pedidos'
        elif rol == 'empleado':
            seccion = 'pos'
        else:
            seccion = 'inventario'

    busqueda_inv = request.GET.get('q_inv', '').strip()
    filtro_stock = request.GET.get('filtro_stock', '').strip()
    productos_filtrados = productos

    if busqueda_inv:
        q_l = busqueda_inv.lower()
        productos_filtrados = [
            p for p in productos_filtrados
            if q_l in p.get('codigo', '').lower()
            or q_l in p.get('nombre', '').lower()
            or q_l in p.get('marca', '').lower()
            or q_l in p.get('categoria', '').lower()
            or q_l in p.get('medida', '').lower()
        ]

    if filtro_stock == 'agotados':
        productos_filtrados = [
            p for p in productos_filtrados if p.get('stock', 0) <= 0]
    elif filtro_stock == 'bajo_stock':
        productos_filtrados = [p for p in productos_filtrados if 0 < p.get(
            'stock', 0) <= p.get('stock_minimo', 5)]

    productos_agotados = [p for p in productos if p.get('stock', 0) == 0]
    productos_bajo_stock = [p for p in productos if 0 <
                            p.get('stock', 0) <= p.get('stock_minimo', 5)]
    total_por_reabastecer = len(productos_agotados) + len(productos_bajo_stock)

    valor_inventario_costo = sum(
        p.get('stock', 0) * p.get('precio_compra', 0) for p in productos)
    valor_inventario_venta = sum(
        p.get('stock', 0) * p.get('precio', 0) for p in productos)
    total_ingresos_ventas = sum(v.get('total_pagar', 0)
                                for v in VENTAS_PEDIDOS_MEMORIA)

    # 1. Reporte de Inventario por Categoría
    reporte_categorias = []
    for cat in CATEGORIAS_SISTEMA:
        prods_cat = [p for p in productos if p.get('categoria') == cat]
        unidades_cat = sum(p.get('stock', 0) for p in prods_cat)
        valor_cat = sum(p.get('stock', 0) * p.get('precio', 0)
                        for p in prods_cat)
        reporte_categorias.append({
            'categoria': cat,
            'cantidad_productos': len(prods_cat),
            'unidades_stock': unidades_cat,
            'valor_total': valor_cat,
        })

    # 2. Reporte de Maquinaria y Productos de Mayor Valor
    productos_alto_valor = [
        p for p in productos
        if p.get('categoria') in ['Maquinaria', 'Muebles'] or p.get('precio', 0) >= 25.0
    ]

    # 3. Reporte de Productos Más Vendidos / Solicitados
    conteo_vendidos = {}
    for venta in VENTAS_PEDIDOS_MEMORIA:
        for item in venta.get('items', []):
            cid = item['codigo']
            if cid not in conteo_vendidos:
                conteo_vendidos[cid] = {
                    'codigo': item['codigo'],
                    'nombre': item['nombre'],
                    'categoria': item.get('categoria', ''),
                    'unidades_vendidas': 0,
                    'ingresos_generados': 0.0,
                }
            conteo_vendidos[cid]['unidades_vendidas'] += item['cantidad']
            conteo_vendidos[cid]['ingresos_generados'] += item['subtotal']
    productos_mas_vendidos = sorted(
        conteo_vendidos.values(),
        key=lambda x: x['unidades_vendidas'],
        reverse=True
    )

    mis_pedidos = [
        v for v in VENTAS_PEDIDOS_MEMORIA
        if v.get('usuario_correo') == usuario.get('correo') or v.get('cliente_nombre', '').lower() == usuario.get('nombre', '').lower()
    ]

    carrito = request.session.get('carrito', {})
    resumen_carrito = calcular_totales_carrito(carrito)

    producto_editar = None
    editar_id = request.GET.get('editar_id')
    if editar_id and rol == 'admin':
        producto_editar = next(
            (p for p in productos if str(p['id']) == str(editar_id)), None)

    contexto = {
        'usuario': usuario,
        'rol': rol,
        'seccion': seccion,
        'productos': productos_filtrados,
        'todos_productos': productos,
        'categorias': CATEGORIAS_SISTEMA,
        'busqueda_inv': busqueda_inv,
        'filtro_stock': filtro_stock,
        'productos_agotados': productos_agotados,
        'productos_bajo_stock': productos_bajo_stock,
        'total_por_reabastecer': total_por_reabastecer,
        'valor_inventario_costo': valor_inventario_costo,
        'valor_inventario_venta': valor_inventario_venta,
        'total_ingresos_ventas': total_ingresos_ventas,
        'reporte_categorias': reporte_categorias,
        'productos_alto_valor': productos_alto_valor,
        'productos_mas_vendidos': productos_mas_vendidos,
        'ventas_pedidos': VENTAS_PEDIDOS_MEMORIA,
        'mis_pedidos': mis_pedidos,
        'usuarios_sistema': USUARIOS_MEMORIA,
        'resumen_carrito': resumen_carrito,
        'cantidad_carrito': contar_items_carrito(request),
        'producto_editar': producto_editar,
    }
    return render(request, 'tienda/panel.html', contexto)


def guardar_producto(request):
    usuario = request.session.get('usuario', {})
    if request.method == 'POST' and usuario.get('rol') == 'admin':
        prod_id = request.POST.get('producto_id', '').strip()
        codigo = request.POST.get('codigo', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        marca = request.POST.get('marca', '').strip()
        medida = request.POST.get('medida', '').strip()
        categoria = request.POST.get('categoria', 'Herramientas').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        precio_compra = float(request.POST.get('precio_compra', 0) or 0)
        precio = float(request.POST.get('precio', 0) or 0)
        precio_mayoreo = float(request.POST.get(
            'precio_mayoreo', precio) or precio)
        stock = int(request.POST.get('stock', 0) or 0)
        stock_minimo = int(request.POST.get('stock_minimo', 5) or 5)
        pasillo = request.POST.get('pasillo', '').strip()
        estanteria = request.POST.get('estanteria', '').strip()
        imagen = request.POST.get('imagen', '').strip(
        ) or "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?auto=format&fit=crop&w=700&q=80"
        estado = "Agotado" if stock <= 0 else "Activo"

        datos_prod = {
            "codigo": codigo,
            "nombre": nombre,
            "marca": marca,
            "medida": medida,
            "categoria": categoria,
            "descripcion": descripcion,
            "especificaciones": descripcion,
            "precio_compra": precio_compra,
            "precio": precio,
            "precio_mayoreo": precio_mayoreo,
            "stock": stock,
            "stock_minimo": stock_minimo,
            "pasillo": pasillo,
            "estanteria": estanteria,
            "estado": estado,
            "imagen": imagen,
        }

        if prod_id:
            for p in PRODUCTOS_MEMORIA:
                if str(p['id']) == str(prod_id):
                    p.update(datos_prod)
                    break
            try:
                requests.put(f"{API_BASE_URL}/productos/{prod_id}/",
                             json=datos_prod, timeout=1)
            except requests.RequestException:
                pass
            messages.success(
                request, f"Producto {nombre} actualizado correctamente.")
        else:
            nuevo_id = max([p['id'] for p in PRODUCTOS_MEMORIA], default=0) + 1
            datos_prod['id'] = nuevo_id
            PRODUCTOS_MEMORIA.append(datos_prod)
            try:
                requests.post(f"{API_BASE_URL}/productos/",
                              json=datos_prod, timeout=1)
            except requests.RequestException:
                pass
            messages.success(
                request, f"Producto {nombre} registrado en el inventario.")

    return redirect('/panel/?seccion=inventario')


def eliminar_producto(request, producto_id):
    usuario = request.session.get('usuario', {})
    if request.method == 'POST' and usuario.get('rol') == 'admin':
        producto = next(
            (p for p in PRODUCTOS_MEMORIA if p['id'] == producto_id), None)
        if producto:
            nombre_prod = producto['nombre']
            PRODUCTOS_MEMORIA[:] = [
                p for p in PRODUCTOS_MEMORIA if p['id'] != producto_id]
            try:
                requests.delete(
                    f"{API_BASE_URL}/productos/{producto_id}/", timeout=1)
            except requests.RequestException:
                pass
            messages.success(
                request, f"Producto '{nombre_prod}' eliminado correctamente del inventario.")
    return redirect('/panel/?seccion=inventario')


def agregar_categoria(request):
    usuario = request.session.get('usuario', {})
    if request.method == 'POST' and usuario.get('rol') == 'admin':
        nueva_cat = request.POST.get('nombre_categoria', '').strip()
        if nueva_cat and nueva_cat not in CATEGORIAS_SISTEMA:
            CATEGORIAS_SISTEMA.append(nueva_cat)
            try:
                requests.post(f"{API_BASE_URL}/categorias/",
                              json={"nombre": nueva_cat}, timeout=1)
            except requests.RequestException:
                pass
            messages.success(
                request, f"Categoría '{nueva_cat}' agregada al sistema.")
    return redirect('/panel/?seccion=inventario')


def cambiar_estado_pedido(request, numero_factura):
    usuario = request.session.get('usuario', {})
    if request.method == 'POST' and usuario.get('rol') in ['empleado', 'admin']:
        nuevo_estado = request.POST.get('estado_pedido', 'En preparación')
        for pedido in VENTAS_PEDIDOS_MEMORIA:
            if pedido['numero_factura'] == numero_factura:
                pedido['estado_pedido'] = nuevo_estado
                try:
                    requests.put(f"{API_BASE_URL}/ventas/{numero_factura}/",
                                 json={"estado_pedido": nuevo_estado}, timeout=1)
                except requests.RequestException:
                    pass
                messages.success(
                    request, f"Estado de {numero_factura} actualizado a: {nuevo_estado}.")
                break
    return redirect('/panel/?seccion=pedidos')


def guardar_usuario(request):
    usuario = request.session.get('usuario', {})
    if request.method == 'POST' and usuario.get('rol') == 'admin':
        nombre = request.POST.get('nombre', '').strip()
        correo = request.POST.get('correo', '').strip()
        username = request.POST.get('usuario', '').strip()
        password = request.POST.get('password', '123').strip()
        rol = request.POST.get('rol', 'empleado').strip()

        nuevo_id = max([u['id'] for u in USUARIOS_MEMORIA], default=0) + 1
        nuevo_usr = {
            "id": nuevo_id,
            "usuario": username or correo.split('@')[0],
            "correo": correo,
            "password": password,
            "nombre": nombre,
            "rol": rol,
        }
        USUARIOS_MEMORIA.append(nuevo_usr)
        try:
            requests.post(f"{API_BASE_URL}/usuarios/",
                          json=nuevo_usr, timeout=1)
        except requests.RequestException:
            pass
        messages.success(
            request, f"Usuario {nombre} ({rol}) registrado exitosamente.")
    return redirect('/panel/?seccion=usuarios')


def login_view(request):
    next_url = request.GET.get('next') or request.POST.get('next') or ''

    if request.method == 'POST':
        credencial = request.POST.get('credencial', '').strip()
        password = request.POST.get('password', '').strip()

        usuario_autenticado = None

        try:
            respuesta = requests.post(
                f"{API_BASE_URL}/login/",
                json={"correo": credencial,
                      "usuario": credencial, "password": password},
                timeout=1
            )
            if respuesta.status_code == 200:
                datos_api = respuesta.json()
                usuario_autenticado = {
                    'id': datos_api.get('id', 1),
                    'nombre': datos_api.get('nombre', credencial.split('@')[0].capitalize()),
                    'correo': datos_api.get('correo', credencial),
                    'rol': datos_api.get('rol', 'cliente'),
                }
        except requests.RequestException:
            pass

        if not usuario_autenticado:
            for u in USUARIOS_MEMORIA:
                if (credencial.lower() == u['correo'].lower() or credencial.lower() == u['usuario'].lower()) and password == u['password']:
                    usuario_autenticado = {
                        'id': u['id'],
                        'nombre': u['nombre'],
                        'correo': u['correo'],
                        'rol': u['rol'],
                    }
                    break

        if usuario_autenticado:
            request.session['carrito'] = {}
            request.session['usuario'] = usuario_autenticado
            request.session.modified = True
            messages.success(
                request, f"Bienvenido, {usuario_autenticado['nombre']}.")
            if usuario_autenticado['rol'] in ['empleado', 'admin']:
                return redirect('panel')
            if next_url:
                return redirect(next_url)
            return redirect('inicio')
        else:
            messages.error(
                request, "Credenciales incorrectas. Verifica tu usuario y contraseña.")

    return render(request, 'tienda/login.html', {'next': next_url})


def logout_view(request):
    if 'usuario' in request.session:
        del request.session['usuario']
    request.session['carrito'] = {}
    request.session.modified = True
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('inicio')


def registro_view(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        correo = request.POST.get('correo', '').strip()
        usuario = request.POST.get(
            'usuario', '').strip() or correo.split('@')[0]
        password = request.POST.get('password', '').strip()

        existe = any(
            u['correo'].lower() == correo.lower(
            ) or u['usuario'].lower() == usuario.lower()
            for u in USUARIOS_MEMORIA
        )
        if existe:
            messages.error(
                request, "Ese correo o nombre de usuario ya está registrado.")
            return render(request, 'tienda/registro.html')

        nuevo_id = max([u['id'] for u in USUARIOS_MEMORIA], default=0) + 1
        nuevo_cliente = {
            "id": nuevo_id,
            "usuario": usuario,
            "correo": correo,
            "password": password,
            "nombre": nombre,
            "rol": "cliente",
        }
        USUARIOS_MEMORIA.append(nuevo_cliente)

        try:
            requests.post(f"{API_BASE_URL}/usuarios/",
                          json=nuevo_cliente, timeout=1)
        except requests.RequestException:
            pass

        request.session['usuario'] = {
            'id': nuevo_cliente['id'],
            'nombre': nuevo_cliente['nombre'],
            'correo': nuevo_cliente['correo'],
            'rol': 'cliente',
        }
        request.session.modified = True
        messages.success(
            request, f"¡Cuenta creada con éxito! Bienvenido, {nombre}.")
        return redirect('inicio')

    return render(request, 'tienda/registro.html')
