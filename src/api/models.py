from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Boolean, Text, ForeignKey, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
# 🟢 Importamos funciones para hashear contraseñas de manera segura
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

db = SQLAlchemy()

# 🟢 Modelo para la tabla de asociación entre notas y etiquetas
class NoteTag(db.Model):
    # 🟢 Definimos el nombre de la tabla explícitamente
    __tablename__ = 'note_tags'

    # 🟢 Definimos las columnas de la relación
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), primary_key=True)

    # 🟢 Podemos añadir campos adicionales a la relación si los necesitamos
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # 🟢 Relaciones con los modelos principales
    note = db.relationship("Note", back_populates="note_tags")
    tag = db.relationship("Tag", back_populates="note_tags")

class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    # 🟢 Aumentamos la longitud del campo password para almacenar el hash (no la contraseña en texto plano)
    password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)

    # 🟢 Relación con las notas: un usuario puede tener muchas notas
    # 🟢 cascade="all, delete-orphan" hace que al eliminar un usuario, también se eliminen sus notas
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")

    # 🟢 Constructor para la clase User que inicializa con email y password
    def __init__(self, email, password):
        self.email = email
        # 🟢 Hasheamos la contraseña al crear el usuario
        self.set_password(password)
        self.is_active = True

    # 🟢 Método para establecer la contraseña (hasheada)
    # 🟢 generate_password_hash crea un hash unidireccional (no se puede revertir)
    def set_password(self, password):
        self.password = generate_password_hash(password)

    # 🟢 Método para verificar si una contraseña coincide con el hash almacenado
    # 🟢 check_password_hash compara la contraseña proporcionada con el hash almacenado
    def check_password(self, password):
        return check_password_hash(self.password, password)

    # 🟢 Método para convertir el objeto a diccionario (JSON)
    # 🟢 NUNCA incluimos la contraseña en la serialización por seguridad
    def serialize(self):
        return {
            "id": self.id,
            "email": self.email,
            "is_active": self.is_active
            # No serializar la contraseña por seguridad
        }

    def serialize_dashboard(self):
        # Obtenemos la última nota por fecha de creación usando order_by
        last_note = Note.query.filter_by(user_id=self.id).order_by(Note.created_at.desc()).first()

        # Serializamos la última nota si existe
        last_note_serialized = last_note.serialize() if last_note else None

        return {
            "id": self.id,
            "nombre": self.email,  # Cambié self.name a self.email ya que User no tiene atributo name
            "last_note": last_note_serialized
        }

class Note(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    # 🟢 Usamos Text en lugar de String para permitir contenido largo
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 🟢 Guardamos automáticamente la fecha de creación
    created_at: Mapped[datetime.datetime] = mapped_column(db.DateTime, default=datetime.datetime.utcnow)
    # 🟢 Clave foránea: vincula cada nota con su propietario (usuario)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'), nullable=False)

    # 🟢 Relaciones:
    # 🟢 back_populates crea una relación bidireccional (desde User podemos acceder a Note y viceversa)
    user = relationship("User", back_populates="notes")

    # 🟢 Relación con la tabla asociativa NoteTag
    note_tags = relationship("NoteTag", back_populates="note", cascade="all, delete-orphan")

    # 🟢 Relación directa con Tag (para facilitar el acceso a las etiquetas)
    # 🟢 viewonly=True indica que es una vista de solo lectura basada en la relación note_tags
    tags = relationship("Tag", secondary="note_tags", viewonly=True, overlaps="note_tags, tag")

    def serialize(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            # 🟢 Convertimos el datetime a string ISO para JSON
            "created_at": self.created_at.isoformat(),
            "user_id": self.user_id,
            # 🟢 Serializamos también las etiquetas asociadas
            "tags": [tag.serialize() for tag in self.tags]
        }

class Tag(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    # 🟢 unique=True asegura que no haya etiquetas duplicadas
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # 🟢 Relación con la tabla asociativa NoteTag
    note_tags = relationship("NoteTag", back_populates="tag", cascade="all, delete-orphan")

    # 🟢 Relación directa con Note (para facilitar el acceso a las notas)
    # 🟢 viewonly=True indica que es una vista de solo lectura basada en la relación note_tags
    notes = relationship("Note", secondary="note_tags", viewonly=True, overlaps="note_tags, note")

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name
        }