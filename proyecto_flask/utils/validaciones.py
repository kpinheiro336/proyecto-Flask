import re

def validar_email(email):
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email)

def validar_nombre(nombre):
    # Solo letras, espacios y acentos
    return re.match(r"^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+$", nombre) and len(nombre.strip()) > 0

def validar_apellidos(apellidos):
    # Solo letras, espacios y acentos
    return re.match(r"^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+$", apellidos) and len(apellidos.strip()) > 0

def validar_nombre_apellidos_diferentes(nombre, apellidos):
    # Verificar que nombre y apellidos no sean idénticos (ignorando mayúsculas)
    return nombre.strip().lower() != apellidos.strip().lower()

def validar_telefono(telefono):
    # Eliminar guiones, espacios y paréntesis
    telefono_limpio = telefono.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
    # Verificar que tenga entre 8 y 15 dígitos (rango internacional)
    return telefono_limpio.isdigit() and 8 <= len(telefono_limpio) <= 15


def validar_password(password):
    # mínimo 8 caracteres, al menos una letra y un número
    if len(password) < 8:
        return False
    if not re.search(r"[A-Za-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True

def validar_edad(edad):
    try:
        edad_int = int(edad)
        return 1 <= edad_int <= 120
    except ValueError:
        return False