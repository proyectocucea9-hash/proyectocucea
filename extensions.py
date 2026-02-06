"""
Extensiones de Flask (SQLAlchemy, Login, Mail) - evita importaciones circulares.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, AnonymousUserMixin
from flask_mail import Mail

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()


class AnonymousUser(AnonymousUserMixin):
    """Usuario anónimo con es_administrador=False para evitar AttributeError en plantillas."""
    es_administrador = False


login_manager.anonymous_user = AnonymousUser
