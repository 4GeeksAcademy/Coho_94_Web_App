"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
from flask import Flask, request, jsonify, url_for, Blueprint
from api.models import db, User, Note, Tag
from api.utils import generate_sitemap, APIException
from api.cargarexcel import sys, pd
from flask_cors import CORS
# 🟢 Importamos funciones de JWT para autenticación
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

api = Blueprint('api', __name__)

# Allow CORS requests to this API
CORS(api)

# 🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴❤️
# TODOS LOS ENDPOINTS QUE ESTÁN AQUÍ VAN PRECEDIDOS POR /api
# 🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴❤️

# Ruta de prueba (pública)
@api.route('/hello', methods=['GET'])
def handle_hello():
    response_body = {
        "message": "Hello! I'm a message that came from the backend"
    }
    return jsonify(response_body), 200

# 🟢 RUTAS DE AUTENTICACIÓN

# 🟢 Endpoint para registro de usuarios
@api.route('/signup', methods=['POST'])
def signup():
    # 🟢 Obtenemos los datos del cuerpo de la petición (JSON)
    body = request.get_json()

    # 🟢 Validación: aseguramos que se proporcionen email y password
    if not body or not body.get("email") or not body.get("password"):
        return jsonify({"error": "Debes proporcionar email y password"}), 400

    # 🟢 Comprobamos si el usuario ya existe para evitar duplicados
    if User.query.filter_by(email=body["email"]).first():
        return jsonify({"error": "El usuario ya existe"}), 400

    try:
        # 🟢 Creamos un nuevo usuario (la contraseña se hasheará en el constructor)
        new_user = User(
            email=body["email"],
            password=body["password"]
        )
        # 🟢 Añadimos el usuario a la sesión de base de datos
        db.session.add(new_user)
        # 🟢 Guardamos los cambios en la base de datos
        db.session.commit()

        return jsonify({"message": "Usuario creado exitosamente"}), 201

    except Exception as e:
        # 🟢 Si ocurre un error, revertimos los cambios
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# 🟢 Endpoint para inicio de sesión (generación de token JWT)
@api.route('/token', methods=['POST'])
def create_token():
    # 🟢 Obtenemos los datos del cuerpo de la petición
    body = request.get_json()

    # 🟢 Validación de campos requeridos
    if not body or not body.get("email") or not body.get("password"):
        return jsonify({"error": "Debes proporcionar email y password"}), 400

    # 🟢 Buscamos el usuario por email
    user = User.query.filter_by(email=body["email"]).first()

    # 🟢 Validamos que el usuario exista y la contraseña sea correcta
    if not user or not user.check_password(body["password"]):
        return jsonify({"error": "Credenciales incorrectas"}), 401

    # 🟢 Creamos un token JWT con la identidad del usuario (su ID)
    # 🟢 La identidad se recuperará posteriormente con get_jwt_identity()
    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "access_token": access_token,  # 🟢 Token para autenticación
        "user": user.serialize()       # 🟢 Datos del usuario (sin contraseña)
    }), 200

# 🟢 RUTAS PARA NOTAS (PROTEGIDAS)

# 🟢 Obtener todas las notas del usuario actual
@api.route('/notes', methods=['GET'])
# 🟢 jwt_required() protege esta ruta: solo usuarios con token válido pueden acceder
@jwt_required()
def get_user_notes():
    # 🟢 Obtenemos el ID del usuario actual del token JWT
    current_user_id = get_jwt_identity()

    # 🟢 Filtramos para obtener solo las notas del usuario actual (seguridad)
    notes = Note.query.filter_by(user_id=current_user_id).all()
    # 🟢 Convertimos las notas a formato JSON
    notes_serialized = [note.serialize() for note in notes]

    return jsonify(notes_serialized), 200

# 🟢 Crear una nueva nota
@api.route('/notes', methods=['POST'])
@jwt_required()
def create_note():
    # 🟢 Obtenemos el ID del usuario del token JWT
    current_user_id = get_jwt_identity()
    # 🟢 Obtenemos los datos de la petición
    body = request.get_json()

    # 🟢 Validamos campos requeridos
    if not body or not body.get("title") or not body.get("content"):
        return jsonify({"error": "Debes proporcionar título y contenido"}), 400

    try:
        # 🟢 Creamos una nueva nota vinculada al usuario actual
        new_note = Note(
            title=body["title"],
            content=body["content"],
            user_id=current_user_id  # 🟢 Vinculamos la nota al usuario actual
        )

        # 🟢 Procesamos etiquetas si se proporcionan
        if body.get("tags"):
            for tag_name in body["tags"]:
                # 🟢 Buscamos si la etiqueta ya existe
                tag = Tag.query.filter_by(name=tag_name).first()
                # 🟢 Si no existe, la creamos
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                # 🟢 Asociamos la etiqueta a la nota
                new_note.tags.append(tag)

        # 🟢 Guardamos la nota en la base de datos
        db.session.add(new_note)
        db.session.commit()

        # 🟢 Devolvemos la nota creada
        return jsonify(new_note.serialize()), 201

    except Exception as e:
        # 🟢 Si ocurre un error, revertimos los cambios
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# 🟢 Obtener una nota específica
@api.route('/notes/<int:note_id>', methods=['GET'])
@jwt_required()
def get_note(note_id):
    current_user_id = get_jwt_identity()

    # 🟢 Buscamos la nota y verificamos que pertenezca al usuario actual (seguridad)
    # 🟢 Esto evita que un usuario pueda acceder a notas de otros usuarios
    note = Note.query.filter_by(id=note_id, user_id=current_user_id).first()

    if not note:
        return jsonify({"error": "Nota no encontrada"}), 404

    return jsonify(note.serialize()), 200

# 🟢 Actualizar una nota existente
@api.route('/notes/<int:note_id>', methods=['PUT'])
@jwt_required()
def update_note(note_id):
    current_user_id = get_jwt_identity()
    body = request.get_json()

    # 🟢 Verificamos que la nota exista y pertenezca al usuario actual
    note = Note.query.filter_by(id=note_id, user_id=current_user_id).first()

    if not note:
        return jsonify({"error": "Nota no encontrada"}), 404

    try:
        # 🟢 Actualizamos los campos proporcionados
        if body.get("title"):
            note.title = body["title"]
        if body.get("content"):
            note.content = body["content"]

        # 🟢 Actualizamos etiquetas si se proporcionan
        if body.get("tags") is not None:
            # 🟢 Limpiamos etiquetas actuales (relación muchos a muchos)
            note.tags.clear()

            # 🟢 Añadimos las nuevas etiquetas
            for tag_name in body["tags"]:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                note.tags.append(tag)

        # 🟢 Guardamos los cambios
        db.session.commit()

        return jsonify(note.serialize()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# 🟢 Eliminar una nota
@api.route('/notes/<int:note_id>', methods=['DELETE'])
@jwt_required()
def delete_note(note_id):
    current_user_id = get_jwt_identity()

    # 🟢 Verificamos que la nota exista y pertenezca al usuario actual
    note = Note.query.filter_by(id=note_id, user_id=current_user_id).first()

    if not note:
        return jsonify({"error": "Nota no encontrada"}), 404

    try:
        # 🟢 Eliminamos la nota
        db.session.delete(note)
        db.session.commit()

        return jsonify({"message": "Nota eliminada exitosamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# 🟢 RUTAS PARA ETIQUETAS (PROTEGIDAS)

# 🟢 Obtener todas las etiquetas disponibles
@api.route('/tags', methods=['GET'])
@jwt_required()
def get_all_tags():
    # 🟢 Obtenemos todas las etiquetas (son globales, no por usuario)
    tags = Tag.query.all()
    tags_serialized = [tag.serialize() for tag in tags]

    return jsonify(tags_serialized), 200

# 🟢 Obtener notas por etiqueta
@api.route('/tags/<string:tag_name>/notes', methods=['GET'])
@jwt_required()
def get_notes_by_tag(tag_name):
    current_user_id = get_jwt_identity()

    # 🟢 Buscamos la etiqueta por nombre
    tag = Tag.query.filter_by(name=tag_name).first()

    if not tag:
        return jsonify({"error": "Etiqueta no encontrada"}), 404

    # 🟢 Filtramos las notas: solo las del usuario actual con esta etiqueta
    # 🟢 Esto es importante para la seguridad: un usuario solo debe ver sus propias notas
    user_notes_with_tag = [note.serialize() for note in tag.notes if note.user_id == current_user_id]

    return jsonify(user_notes_with_tag), 200