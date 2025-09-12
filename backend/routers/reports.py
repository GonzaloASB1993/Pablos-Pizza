from fastapi import APIRouter, HTTPException, status, Response
from firebase_admin import firestore
from models.schemas import MonthlyReport
from typing import List, Dict, Any
from datetime import datetime, date, timedelta
import pandas as pd
from io import BytesIO
import calendar

router = APIRouter()
db = firestore.client()

@router.get("/monthly/{year}/{month}", response_model=MonthlyReport)
async def get_monthly_report(year: int, month: int):
    """Generar reporte mensual"""
    try:
        # Rango de fechas del mes
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # Obtener eventos del mes
        events_query = db.collection("events").where(
            "start_time", ">=", start_date
        ).where(
            "start_time", "<", end_date
        )
        
        events = list(events_query.stream())
        total_events = len(events)
        
        if total_events == 0:
            return MonthlyReport(
                month=month,
                year=year,
                total_events=0,
                total_income=0.0,
                total_expenses=0.0,
                total_profit=0.0,
                avg_participants=0.0,
                most_popular_service="N/A",
                client_retention_rate=0.0
            )
        
        # Calcular métricas financieras
        total_income = 0.0
        total_expenses = 0.0
        total_participants = 0
        service_counts = {}
        
        for event_doc in events:
            event_data = event_doc.to_dict()
            financials = event_data.get("financials", {})
            
            total_income += financials.get("income", 0.0)
            total_expenses += financials.get("total_expenses", 0.0)
            total_participants += event_data.get("actual_participants", 0)
            
            # Contar servicios (obtener del booking)
            booking_id = event_data.get("booking_id")
            if booking_id:
                booking_doc = db.collection("bookings").document(booking_id).get()
                if booking_doc.exists:
                    booking_data = booking_doc.to_dict()
                    service_type = booking_data.get("service_type", "unknown")
                    service_counts[service_type] = service_counts.get(service_type, 0) + 1
        
        total_profit = total_income - total_expenses
        avg_participants = total_participants / total_events if total_events > 0 else 0
        
        # Servicio más popular
        most_popular_service = max(service_counts.items(), key=lambda x: x[1])[0] if service_counts else "N/A"
        
        # Calcular tasa de retención (clientes que volvieron)
        client_retention_rate = await calculate_client_retention_rate(year, month)
        
        return MonthlyReport(
            month=month,
            year=year,
            total_events=total_events,
            total_income=round(total_income, 2),
            total_expenses=round(total_expenses, 2),
            total_profit=round(total_profit, 2),
            avg_participants=round(avg_participants, 1),
            most_popular_service=most_popular_service,
            client_retention_rate=round(client_retention_rate, 2)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar reporte mensual: {str(e)}"
        )

@router.get("/annual/{year}")
async def get_annual_summary(year: int):
    """Resumen anual por meses"""
    try:
        monthly_reports = []
        
        for month in range(1, 13):
            try:
                report = await get_monthly_report(year, month)
                monthly_reports.append(report)
            except:
                # Si hay error en un mes, usar valores por defecto
                monthly_reports.append(MonthlyReport(
                    month=month,
                    year=year,
                    total_events=0,
                    total_income=0.0,
                    total_expenses=0.0,
                    total_profit=0.0,
                    avg_participants=0.0,
                    most_popular_service="N/A",
                    client_retention_rate=0.0
                ))
        
        # Calcular totales anuales
        annual_summary = {
            "year": year,
            "monthly_reports": [report.model_dump() for report in monthly_reports],
            "annual_totals": {
                "total_events": sum(r.total_events for r in monthly_reports),
                "total_income": sum(r.total_income for r in monthly_reports),
                "total_expenses": sum(r.total_expenses for r in monthly_reports),
                "total_profit": sum(r.total_profit for r in monthly_reports),
                "avg_participants": sum(r.avg_participants for r in monthly_reports) / 12
            }
        }
        
        return annual_summary
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar resumen anual: {str(e)}"
        )

@router.get("/dashboard")
async def get_dashboard_stats():
    """Estadísticas para el dashboard principal"""
    try:
        now = datetime.now()
        today = now.date()
        current_month = now.month
        current_year = now.year
        
        # Estadísticas de hoy
        today_bookings = len(list(db.collection("bookings").where(
            "created_at", ">=", today
        ).where(
            "created_at", "<", today + timedelta(days=1)
        ).stream()))
        
        # Estadísticas del mes actual
        monthly_report = await get_monthly_report(current_year, current_month)
        
        # Próximos eventos (próximos 7 días)
        next_week = today + timedelta(days=7)
        upcoming_events = list(db.collection("bookings").where(
            "event_date", ">=", today
        ).where(
            "event_date", "<=", next_week
        ).where(
            "status", "==", "confirmed"
        ).stream())
        
        # Estadísticas de inventario
        low_stock_items = len(list(db.collection("inventory").where(
            "needs_restock", "==", True
        ).stream()))
        
        # Reseñas pendientes
        pending_reviews = len(list(db.collection("reviews").where(
            "is_approved", "==", False
        ).stream()))
        
        return {
            "today": {
                "new_bookings": today_bookings,
                "date": today.isoformat()
            },
            "current_month": {
                "month_name": calendar.month_name[current_month],
                "events": monthly_report.total_events,
                "income": monthly_report.total_income,
                "profit": monthly_report.total_profit
            },
            "upcoming_events": len(upcoming_events),
            "alerts": {
                "low_stock_items": low_stock_items,
                "pending_reviews": pending_reviews
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas del dashboard: {str(e)}"
        )

@router.get("/export/monthly/{year}/{month}")
async def export_monthly_report(year: int, month: int, format: str = "excel"):
    """Exportar reporte mensual a Excel o PDF"""
    try:
        report = await get_monthly_report(year, month)
        
        if format.lower() == "excel":
            # Crear Excel con pandas
            data = {
                "Métrica": [
                    "Total Eventos",
                    "Ingresos Totales",
                    "Gastos Totales", 
                    "Utilidad Total",
                    "Promedio Participantes",
                    "Servicio Más Popular",
                    "Tasa Retención Clientes"
                ],
                "Valor": [
                    report.total_events,
                    f"${report.total_income:,.2f}",
                    f"${report.total_expenses:,.2f}",
                    f"${report.total_profit:,.2f}",
                    f"{report.avg_participants:.1f}",
                    report.most_popular_service,
                    f"{report.client_retention_rate}%"
                ]
            }
            
            df = pd.DataFrame(data)
            
            # Crear archivo Excel en memoria
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=f'{calendar.month_name[month]} {year}', index=False)
            
            excel_buffer.seek(0)
            
            filename = f"reporte_mensual_{year}_{month:02d}.xlsx"
            
            return Response(
                content=excel_buffer.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato no soportado. Use: excel"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al exportar reporte: {str(e)}"
        )

@router.get("/clients/top")
async def get_top_clients(limit: int = 10):
    """Obtener clientes más frecuentes"""
    try:
        # Obtener todos los bookings
        bookings = list(db.collection("bookings").stream())
        
        client_stats = {}
        for booking_doc in bookings:
            booking_data = booking_doc.to_dict()
            client_email = booking_data.get("client_email")
            client_name = booking_data.get("client_name")
            
            if client_email not in client_stats:
                client_stats[client_email] = {
                    "name": client_name,
                    "email": client_email,
                    "total_bookings": 0,
                    "total_spent": 0.0
                }
            
            client_stats[client_email]["total_bookings"] += 1
            
            # Buscar evento asociado para obtener ingresos
            events = list(db.collection("events").where(
                "booking_id", "==", booking_data.get("id")
            ).stream())
            
            for event_doc in events:
                event_data = event_doc.to_dict()
                income = event_data.get("financials", {}).get("income", 0.0)
                client_stats[client_email]["total_spent"] += income
        
        # Ordenar por número de bookings
        top_clients = sorted(
            client_stats.values(),
            key=lambda x: x["total_bookings"],
            reverse=True
        )[:limit]
        
        return {"clients": top_clients}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener clientes top: {str(e)}"
        )

# Función auxiliar
async def calculate_client_retention_rate(year: int, month: int) -> float:
    """Calcular tasa de retención de clientes para el mes"""
    try:
        # Obtener clientes del mes actual
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        current_bookings = list(db.collection("bookings").where(
            "event_date", ">=", start_date
        ).where(
            "event_date", "<", end_date
        ).stream())
        
        if not current_bookings:
            return 0.0
        
        current_clients = set()
        for booking_doc in current_bookings:
            booking_data = booking_doc.to_dict()
            current_clients.add(booking_data.get("client_email"))
        
        # Obtener clientes de meses anteriores
        previous_bookings = list(db.collection("bookings").where(
            "event_date", "<", start_date
        ).stream())
        
        previous_clients = set()
        for booking_doc in previous_bookings:
            booking_data = booking_doc.to_dict()
            previous_clients.add(booking_data.get("client_email"))
        
        # Calcular retención
        returning_clients = current_clients.intersection(previous_clients)
        retention_rate = (len(returning_clients) / len(current_clients)) * 100
        
        return retention_rate
        
    except:
        return 0.0