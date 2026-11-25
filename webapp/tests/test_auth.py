from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
import os
import unittest
from webapp.app import app, db, User
from flask import request
from werkzeug.security import check_password_hash
from flask_testing import TestCase

class AuthTest(TestCase):
    def create_app(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'testsecret'
        app.config['TESTING'] = True
        return app

    def setUp(self):
        db.create_all()
        self.user1 = User()
        self.user1.username = 'user1'
        self.user1.set_password('pass1')
        db.session.add(self.user1)
        self.user2 = User()
        self.user2.username = 'user2'
        self.user2.set, 'pass2')
        db.session.add(self.user2)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_user_isolation(self):
        # User 1 creates conversation
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user1.id
        response = self.client.post('/chat', data={'subject': 'math', 'question': 'What is 2+2?'})
        self.assertEqual(response.status_code, 200)
        
        # User 2 tries to access User 1's conversation
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user2.id
        response = self.client.get('/chat')
        self.assertEqual(response.status_code, 403)

    def test_user_owns_own_history(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user1.id
        response = self.client.post('/chat', data={'subject': 'math', 'question': 'What is 2+2?'})
        self.assertEqual(response.status_code, 200)
        
        # Log in again and check history
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user1.id
        response = self.client.get('/chat')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'What is 2+2?', response.data)

    def test_unauthenticated_access_denied(self):
        response = self.client.get('/chat')
        self.assertEqual(response.status_code, 401)

    def test_duplicate_registration(self):
        response = self.client.post('/register', data={'username': 'user1', 'password': 'pass1'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Username already exists', response.data)

    def test_symlink_protection(self):
        # Create symlink for user1's directory
        user_dir = DATA_DIR / "users" / str(self.user1.id)
        symlink_path = DATA_DIR / "users" / "symlink_user1"
        os.symlink(str(user_dir), symlink_path)

        # User1 tries to access symlinked directory
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user1.id
        response = self.client.get('/chat')
        self.assertEqual(response.status_code, 200)

        # User2 tries to access symlinked directory
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user2.id
        response = self.client.get('/chat')
        self.assertEqual(response.status_code, 403)

    def test_path_traversal(self):
        # User1 tries to access ../user2's directory
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user1.id
        response = self.client.get('/chat', data={'subject': '../../user2/math'})
        self.assertEqual(response.status_code, 400)

    def test_invalid_subject(self):
        # User1 tries to use invalid subject with path traversal
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user1.id
        response = self.client.get('/chat', data={'subject': 'math/../../etc/passwd'})
        self.assertEqual(response.status_code, 400)