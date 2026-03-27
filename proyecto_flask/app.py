import json
import os
from flask import send_file, flash
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash
import re
from flask_sqlalchemy import SQLAlchemy
from utils.validaciones import validar_email, validar_telefono, validar_edad, validar_nombre, validar_apellidos, validar_nombre_apellidos_diferentes, validar_password

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-clave-temporal-cambiar-en-produccion')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usuarios.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# ------------------ MODELO ------------------

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nombre = db.Column(db.String(80), nullable=False)
    apellidos = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    edad = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Usuario {self.nombre} {self.apellidos}>'


# ------------------ RUTAS ------------------

# ------------------ EXPORTAR USUARIOS A JSON ------------------
@app.route('/exportar_json')
def exportar_json():
    usuarios = Usuario.query.all()
    usuarios_dict = []
    for u in usuarios:
        usuarios_dict.append({
            'email': u.email,
            'nombre': u.nombre,
            'apellidos': u.apellidos,
            'password': u.password,
            'telefono': u.telefono,
            'edad': u.edad
        })
    ruta_export = os.path.join(app.root_path, 'usuarios_export.json')
    with open(ruta_export, 'w', encoding='utf-8') as f:
        json.dump(usuarios_dict, f, ensure_ascii=False, indent=4)
    return send_file(ruta_export, as_attachment=True)

# ------------------ IMPORTAR USUARIOS DESDE JSON ------------------
@app.route('/importar_json', methods=['GET', 'POST'])
def importar_json():
    if request.method == 'POST':
        if 'archivo' not in request.files:
            flash('No se envió ningún archivo.')
            return redirect(request.url)
        archivo = request.files['archivo']
        if archivo.filename == '':
            flash('No se seleccionó ningún archivo.')
            return redirect(request.url)
        if archivo and archivo.filename.endswith('.json'):
            try:
                usuarios_lista = json.load(archivo)
                nuevos = 0
                for u in usuarios_lista:
                    if not Usuario.query.filter_by(email=u['email']).first():
                        # Si la contraseña no está hasheada, aplicar hash
                        pwd = u['password']
                        if not pwd.startswith(('pbkdf2:sha', 'scrypt:')):
                            pwd = generate_password_hash(pwd)
                        nuevo = Usuario(
                            email=u['email'],
                            nombre=u['nombre'],
                            apellidos=u['apellidos'],
                            password=pwd,
                            telefono=u['telefono'],
                            edad=u['edad']
                        )
                        db.session.add(nuevo)
                        nuevos += 1
                db.session.commit()
                flash(f"Importados {nuevos} usuarios nuevos desde JSON.")
            except Exception as e:
                db.session.rollback()
                flash(f"Error al importar: {str(e)}")
            return redirect(url_for('tabla'))
        else:
            flash('El archivo debe ser un JSON válido.')
            return redirect(request.url)
    return render_template('importar_json.html')

@app.route("/")
def menu():
    return render_template("menu.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    errores = []
    datos = {}
    
    if request.method == "POST":
        try:
            email = request.form.get("email", "").strip().lower()
            telefono = request.form.get("telefono", "").strip()
            prefijo = request.form.get("prefijo", "").strip()
            edad = request.form.get("edad", "").strip()
            nombre = request.form.get("nombre", "").strip()
            apellidos = request.form.get("apellidos", "").strip()
            password = request.form.get("password", "").strip()

            # Verificar que no estén vacíos
            if not all([email, telefono, edad, nombre, apellidos, password]):
                errores.append("Todos los campos son obligatorios")
                return render_template("form.html", errores=errores, datos={"email": email, "telefono": telefono, "prefijo": prefijo, "edad": edad, "nombre": nombre, "apellidos": apellidos})

            # Validar que el prefijo no esté vacío
            if not prefijo:
                errores.append("Debes seleccionar un país para el teléfono")
                return render_template("form.html", errores=errores, datos={"email": email, "telefono": telefono, "prefijo": prefijo, "edad": edad, "nombre": nombre, "apellidos": apellidos})

            # Guardar datos para prellenar el formulario
            datos = {"email": email, "telefono": telefono, "prefijo": prefijo, "edad": edad, "nombre": nombre, "apellidos": apellidos}

            # VALIDACIONES
            if not validar_nombre(nombre):
                errores.append("Nombre inválido (solo se permiten letras)")

            if not validar_apellidos(apellidos):
                errores.append("Apellidos inválidos (solo se permiten letras)")

            if not validar_nombre_apellidos_diferentes(nombre, apellidos):
                errores.append("Nombre y apellidos no pueden ser iguales")

            if not validar_email(email):
                errores.append("Email inválido")

            if not validar_telefono(telefono):
                errores.append("Teléfono inválido (debe tener entre 8 y 15 dígitos)")

            if not validar_edad(edad):
                errores.append("Edad inválida")

            if not validar_password(password):
                errores.append("Contraseña inválida. Mínimo 8 caracteres, al menos letra y número")

            # Construir teléfono completo con prefijo (si se proporciona)
            telefono_guardar = telefono
            if prefijo:
                telefono_guardar = f"{prefijo} {telefono}" if not telefono.startswith(prefijo) else telefono

            # Verificar si email ya existe
            if Usuario.query.filter_by(email=email).first():
                errores.append("Email ya registrado")

            # Verificar si nombre+apellidos ya existen (nombres únicos)
            if Usuario.query.filter_by(nombre=nombre, apellidos=apellidos).first():
                errores.append("Ya existe un usuario con el mismo nombre y apellidos")
            
            # Si hay errores, mostrar el formulario nuevamente
            if errores:
                return render_template("form.html", errores=errores, datos=datos)

            # Capitalizar nombre y apellidos
            nombre = nombre.title()
            apellidos = apellidos.title()

            nuevo_usuario = Usuario(
                email=email,
                nombre=nombre,
                apellidos=apellidos,
                password=generate_password_hash(password),
                telefono=telefono_guardar,
                edad=int(edad)
            )

            db.session.add(nuevo_usuario)
            db.session.commit()

            return redirect(url_for("tabla"))
            
        except ValueError as e:
            errores.append("Error al procesar los datos. Verifica que la edad sea un número válido")
            return render_template("form.html", errores=errores, datos=datos)
        except Exception as e:
            db.session.rollback()
            errores.append("Error al registrar usuario. Por favor intenta de nuevo")
            return render_template("form.html", errores=errores, datos=datos)

    return render_template("form.html", errores=[], datos=datos)


@app.route("/usuarios")
def tabla():
    usuarios = Usuario.query.all()
    paises = {
        '+34': 'España',
        '+1': 'USA/Canadá',
        '+44': 'Reino Unido',
        '+33': 'Francia',
        '+49': 'Alemania',
        '+39': 'Italia',
        '+31': 'Países Bajos',
        '+43': 'Austria',
        '+41': 'Suiza',
        '+55': 'Brasil',
        '+52': 'México',
        '+54': 'Argentina',
        '+56': 'Chile',
        '+57': 'Colombia',
        '+51': 'Perú',
        '+61': 'Australia',
        '+81': 'Japón',
        '+86': 'China',
        '+91': 'India',
        '+82': 'Corea del Sur'
    }
    usuarios_con_pais = []
    for u in usuarios:
        match = re.match(r'^(\+\d{1,3})', u.telefono.strip())
        prefijo = match.group(1) if match else None
        pais = paises.get(prefijo, 'Desconocido')
        usuarios_con_pais.append({
            'id': u.id,
            'email': u.email,
            'nombre': u.nombre,
            'apellidos': u.apellidos,
            'telefono': u.telefono,
            'edad': u.edad,
            'pais': pais
        })
    return render_template("tabla.html", usuarios=usuarios_con_pais)


@app.route("/eliminar/<int:id>")
def eliminar(id):
    try:
        usuario = db.get_or_404(Usuario, id)
        db.session.delete(usuario)
        db.session.commit()
        return redirect(url_for("tabla"))
    except Exception as e:
        db.session.rollback()
        return redirect(url_for("tabla"))


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    try:
        usuario = db.get_or_404(Usuario, id)

        if request.method == "POST":
            try:
                email = request.form.get("email", "").strip().lower()
                nombre = request.form.get("nombre", "").strip()
                apellidos = request.form.get("apellidos", "").strip()
                telefono = request.form.get("telefono", "").strip()
                prefijo = request.form.get("prefijo", "").strip()
                edad = request.form.get("edad", "").strip()
                password = request.form.get("password", "").strip()
                
                # Verificar que los campos requeridos no estén vacíos
                if not all([email, nombre, apellidos, telefono, edad]):
                    errores = ["Todos los campos son obligatorios"]
                    return render_template("form.html", errores=errores, usuario=usuario)
                
                # Validaciones
                errores = []
                if not validar_nombre(nombre):
                    errores.append("Nombre inválido (solo se permiten letras)")
                if not validar_apellidos(apellidos):
                    errores.append("Apellidos inválidos (solo se permiten letras)")
                if not validar_nombre_apellidos_diferentes(nombre, apellidos):
                    errores.append("Nombre y apellidos no pueden ser iguales")
                if not validar_email(email):
                    errores.append("Email inválido")
                if not validar_telefono(telefono):
                    errores.append("Teléfono inválido")
                if not validar_edad(edad):
                    errores.append("Edad inválida")

                if password and not validar_password(password):
                    errores.append("Contraseña inválida. Mínimo 8 caracteres, al menos letra y número")
                
                # Verificar email duplicado (si cambió)
                if email != usuario.email and Usuario.query.filter_by(email=email).first():
                    errores.append("Email ya registrado")

                # Verificar nombre+apellidos duplicados con otro usuario (si cambió)
                mismo_nombre_apellidos = Usuario.query.filter_by(nombre=nombre, apellidos=apellidos).first()
                if mismo_nombre_apellidos and mismo_nombre_apellidos.id != usuario.id:
                    errores.append("Ya existe un usuario con el mismo nombre y apellidos")
                
                if errores:
                    return render_template("form.html", errores=errores, usuario=usuario)
                
                # Capitalizar nombre y apellidos
                nombre = nombre.title()
                apellidos = apellidos.title()
                
                # Construir teléfono completo con prefijo (si viene)
                telefono_guardar = telefono
                if prefijo:
                    telefono_guardar = f"{prefijo} {telefono}" if not telefono.startswith(prefijo) else telefono

                usuario.email = email
                usuario.nombre = nombre
                usuario.apellidos = apellidos
                usuario.telefono = telefono_guardar
                usuario.edad = int(edad)
                
                # Si el usuario escribió una nueva contraseña, actualizar
                if password:
                    usuario.password = generate_password_hash(password)

                db.session.commit()
                return redirect(url_for("tabla"))
                
            except ValueError:
                errores = ["Error al procesar los datos. Verifica que la edad sea un número válido"]
                return render_template("form.html", errores=errores, usuario=usuario)
            except Exception as e:
                db.session.rollback()
                errores = ["Error al actualizar usuario. Por favor intenta de nuevo"]
                return render_template("form.html", errores=errores, usuario=usuario)

        return render_template("form.html", usuario=usuario)
        
    except Exception as e:
        return "Usuario no encontrado", 404


# ------------------ MAIN ------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)