import os
import json
import requests
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash
from datetime import datetime

app = Flask(__name__)

# Simulate user database
users = {
    "user1": {
        "id": 1,
        "username": "user1",
        "password_hash": generate_password_hash("password1")
    },
    "user2": {
        "id": 2,
        "username": "user2",
        "password_hash": generate_password_hash("password2")
    }
}

# Simulate test dataset
test_subject_data = {
    "test_subject": {
        "files": [
            "page-0001.txt": "This is a relevant passage about mathematics.",
            "page-0002.txt": "This is an unrelated passage about biology.",
            "page-0003.txt": "This is a duplicate of page-0001.txt.",
            "page-0004.txt": "This is a Telugu passage: సంఖ్యా వ్యవస్థలు సంఖ్యలను వర్ణించడానికి ఉపయోగించే విధానాలు ఉంటాయి.",
            "page-0005.txt": "This is a Hindi passage: संख्या प्रणाली संख्याओं को वर्णित करने के विधियां होती हैं।"
        ]
    }
}

# Test BM25 ranking
@app.route('/test-bm25', methods=['GET'])
def test_bm25():
    query = request.args.get('query', 'mathematics')
    subject = 'test_subject'
    
    # Simulate retrieval
    results = []
    for file, content in test_subject_data[subject]['files'].items():
        
        # Simple relevance scoring (replace with BM25 implementation)
        score = content.count(query)
        results.append({
            'file': file,
            'content': content,
            'score': score
        })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return jsonify(results)

# Test multi-user isolation
@app.route('/test-isolation', methods=['GET'])
def test_isolation():
    user_id = request.args.get('user_id', '1')
    subject = request.args.get('subject', 'test_subject')
    
    # Simulate user-specific data
    user_data = {
        "1": {
            "conversations": {
                "test_subject": [
                    "Question: What is mathematics?\nAnswer: Mathematics is the study of numbers and shapes.\nSources: test_subject/page-0001.txt"
                ]
            }
        },
        "2": {
            "conversations": {
                "test_subject": [
                    "Question: What is biology?\nAnswer: Biology is the study of living organisms.\nSources: test_subject/page-0002.txt"
                ]
            }
        }
    }
    
    return jsonify(user_data.get(user_id, {}))

# Test edge cases
@app.route('/test-edge-cases', methods=['GET'])
def test_edge_cases():
    query = request.args.get('query', 'mathematics')
    subject = request.args, get('subject', 'invalid_subject')
    
    # Simulate edge case scenarios
    results = []
    if subject not in test_subject_data:
        results.append({'error': 'Subject not found'})
    else:
        for file, content in test_subject_data[subject]['files'].items():
            if not content.strip():
                results.append({'file': file, 'error': 'Empty file'})
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)