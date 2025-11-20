# -*- coding: utf-8 -*-
"""
tests/unit/test_auth.py
Pruebas unitarias para el módulo de autenticación
"""

import pytest
from werkzeug.security import generate_password_hash, check_password_hash


class TestAuthentication:
    """Pruebas para funcionalidades de autenticación"""
    
    def test_password_hashing(self):
        """Verifica que el hashing de contraseñas funcione correctamente"""
        password = "mi_contraseña_segura"
        hashed = generate_password_hash(password)
        
        # El hash no debe ser igual a la contraseña original
        assert hashed != password
        
        # Debe poder verificar correctamente
        assert check_password_hash(hashed, password) is True
        
        # No debe verificar con contraseña incorrecta
        assert check_password_hash(hashed, "contraseña_incorrecta") is False
    
    def test_password_hash_uniqueness(self):
        """Verifica que cada hash sea único incluso con la misma contraseña"""
        password = "mi_contraseña"
        hash1 = generate_password_hash(password)
        hash2 = generate_password_hash(password)
        
        # Los hashes deben ser diferentes (tienen salt diferente)
        assert hash1 != hash2
        
        # Pero ambos deben verificar correctamente
        assert check_password_hash(hash1, password) is True
        assert check_password_hash(hash2, password) is True
    
    def test_empty_password(self):
        """Verifica manejo de contraseñas vacías"""
        password = ""
        hashed = generate_password_hash(password)
        
        # Debe poder hashear incluso vacío
        assert hashed != password
        assert check_password_hash(hashed, "") is True


class TestUserValidation:
    """Pruebas para validación de datos de usuario"""
    
    def test_valid_email_format(self):
        """Verifica validación de formato de email"""
        valid_emails = [
            "usuario@example.com",
            "test.user@domain.co",
            "admin@skyking.com"
        ]
        
        for email in valid_emails:
            # Lógica básica de validación
            assert "@" in email
            assert "." in email.split("@")[1]
    
    def test_invalid_email_format(self):
    
        invalid_emails = [
            "sin_arroba.com",
            "@sinusuario.com",
            "usuario@",
            "usuario@dominio",
        ]
        
        for email in invalid_emails:
            # Validación mejorada: debe tener @ y algo antes y después
            if "@" not in email:
                is_valid = False
            else:
                parts = email.split("@")
                # Debe haber exactamente un @ y contenido antes y después
                if len(parts) != 2 or not parts[0] or not parts[1]:
                    is_valid = False
                # La parte después del @ debe tener un punto y contenido válido
                elif "." not in parts[1]:
                    is_valid = False
                else:
                    domain_parts = parts[1].split(".")
                    # Verificar que hay contenido antes y después del punto
                    is_valid = all(part for part in domain_parts)
            
            assert is_valid is False
    
    def test_password_strength_requirements(self):
        """Verifica requisitos mínimos de contraseña"""
        # Contraseñas débiles
        weak_passwords = ["123", "abc", "pass"]
        
        for pwd in weak_passwords:
            # Longitud mínima de 6 caracteres
            assert len(pwd) < 6
        
        # Contraseñas aceptables
        strong_passwords = ["password123", "securePass!", "MyP@ssw0rd"]
        
        for pwd in strong_passwords:
            assert len(pwd) >= 6


class TestSessionManagement:
    """Pruebas para manejo de sesiones"""
    
    def test_session_data_structure(self):
        """Verifica estructura de datos de sesión"""
        session_data = {
            'user_id': 1,
            'email': 'usuario@example.com',
            'role': 'cliente',
            'is_authenticated': True
        }
        
        # Verificar campos requeridos
        assert 'user_id' in session_data
        assert 'email' in session_data
        assert 'role' in session_data
        assert 'is_authenticated' in session_data
        
        # Verificar tipos
        assert isinstance(session_data['user_id'], int)
        assert isinstance(session_data['email'], str)
        assert isinstance(session_data['role'], str)
        assert isinstance(session_data['is_authenticated'], bool)
    
    def test_valid_user_roles(self):
        """Verifica roles de usuario válidos"""
        valid_roles = ['cliente', 'operador', 'administrador', 'aliado', 'tecnico']
        
        test_role = 'cliente'
        assert test_role in valid_roles
        
        invalid_role = 'usuario_invalido'
        assert invalid_role not in valid_roles


# Configuración de pytest
@pytest.fixture
def sample_user():
    """Fixture que proporciona datos de usuario de ejemplo"""
    return {
        'id': 1,
        'email': 'test@skyking.com',
        'password_hash': generate_password_hash('password123'),
        'role': 'cliente',
        'full_name': 'Usuario de Prueba',
        'is_active': True
    }


def test_sample_user_fixture(sample_user):
    """Verifica que el fixture funcione correctamente"""
    assert sample_user['id'] == 1
    assert '@' in sample_user['email']
    assert sample_user['is_active'] is True
    assert check_password_hash(sample_user['password_hash'], 'password123')
