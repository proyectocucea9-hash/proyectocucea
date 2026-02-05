"""
Extensiones de Flask (SQLAlchemy, Login) - evita importaciones circulares.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, AnonymousUserMixin

db = SQLAlchemy()
login_manager = LoginManager()


class AnonymousUser(AnonymousUserMixin):
    """Usuario anónimo con es_administrador=False para evitar AttributeError en plantillas."""
    es_administrador = False


login_manager.anonymous_user = AnonymousUser
