# models.py
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Numeric
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    telefono = Column(String(20))
    correo = Column(String(100))
    direccion = Column(String(150))
    comuna = Column(String(100))

    pedidos = relationship("Pedido", back_populates="cliente", cascade="all, delete-orphan")

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero_pedido = Column(String(30), unique=True, nullable=False)
    fecha_pedido = Column(DateTime, default=datetime.now)
    canal_venta = Column(String(50))
    forma_pago = Column(String(50))
    tipo_documento = Column(String(50))
    monto_pagado = Column(Numeric(12,2))
    saldo = Column(Numeric(12,2))
    despacho = Column(String(100))
    estado = Column(String(50))
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)

    cliente = relationship("Cliente", back_populates="pedidos")
    items = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")

class ItemPedido(Base):
    __tablename__ = "items_pedido"

    id = Column(Integer, primary_key=True, autoincrement=True)
    producto = Column(String(200), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(12,2))
    total_item = Column(Numeric(12,2))
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)

    pedido = relationship("Pedido", back_populates="items")
