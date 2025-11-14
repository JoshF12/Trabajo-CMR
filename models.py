from datetime import datetime
from sqlalchemy import (
    String, Integer, DateTime, ForeignKey, Numeric, Text
)
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship


class Base(DeclarativeBase):
    pass


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(50))
    correo: Mapped[str | None] = mapped_column(String(255))
    direccion: Mapped[str | None] = mapped_column(String(255))
    comuna: Mapped[str | None] = mapped_column(String(100))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    interacciones: Mapped[list["Interaccion"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_pedido: Mapped[str | None] = mapped_column(String(100))
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"))
    fecha: Mapped[datetime | None] = mapped_column(DateTime)
    canal: Mapped[str | None] = mapped_column(String(100))
    forma_pago: Mapped[str | None] = mapped_column(String(100))
    tipo_doc: Mapped[str | None] = mapped_column(String(50))
    pagado: Mapped[Numeric | None] = mapped_column(Numeric(12, 2))
    saldo: Mapped[Numeric | None] = mapped_column(Numeric(12, 2))
    despacho: Mapped[str | None] = mapped_column(String(100))
    estado: Mapped[str | None] = mapped_column(String(100))
    notas: Mapped[str | None] = mapped_column(Text)

    cliente: Mapped["Cliente"] = relationship(back_populates="pedidos")
    items: Mapped[list["ItemPedido"]] = relationship(back_populates="pedido", cascade="all, delete-orphan")


class ItemPedido(Base):
    __tablename__ = "items_pedido"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id", ondelete="CASCADE"))
    producto: Mapped[str | None] = mapped_column(String(255))
    unidades: Mapped[int | None] = mapped_column(Integer)
    precio_unitario: Mapped[Numeric | None] = mapped_column(Numeric(12, 2))
    total: Mapped[Numeric | None] = mapped_column(Numeric(12, 2))

    pedido: Mapped["Pedido"] = relationship(back_populates="items")


class Interaccion(Base):
    __tablename__ = "interacciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"))
    pedido_id: Mapped[int | None] = mapped_column(ForeignKey("pedidos.id", ondelete="SET NULL"))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    canal: Mapped[str | None] = mapped_column(String(50))  # telefono, whatsapp, web, email
    detalle: Mapped[str | None] = mapped_column(Text)

    cliente: Mapped["Cliente"] = relationship(back_populates="interacciones")
