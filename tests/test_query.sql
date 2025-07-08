SELECT count(DISTINCT producto) AS productosdistintosvendidos
FROM flexline.vista_venta_detalle
WHERE fecha >= dateadd(MONTH, -6, getdate())
