import math

from webapp.subject_metadata import subject_metadata

def bm25_score(query, doc, doc_freq, avg_doc_len, doc_len):
    if not avg_doc_len:
        return 0
    K = 1.5
    B = 0.75
    score = 0
    for term in query.split():
        tf = doc.get(term, 0)
        df = doc_freq.get(term, 0)
        idf = math.log((len(doc_freq) - df + 0.5) / (df + 0.5)) if df else 0
        denominator = (1 - B) + B * (doc_len / avg_doc_len)
        score += tf * (idf / (K + tf) * (K + tf) / denominator)
    return score

def retrieve_passages(query, subject):
    if subject not in subject_metadata:
        return []
    metadata = subject_metadata[subject]
    documents = metadata.get('documents', {})
    doc_freq = metadata.get('doc_freq', {})
    avg_doc_len = metadata.get('avg_doc_len', 0)
    if not documents or avg_doc_len == 0:
        return []
    results = []
    for doc_id, doc in documents.items():
        if not query:
            continue
        score = bm25_score(query, doc, doc_freq, avg_doc_len, len(doc['text'].split()))
        if score > 0:
            results.append({
                'id': doc_id,
                'text': doc['text'],
                'metadata': {
                    'file': metadata['filename'],
                    'page': doc_id,
                    'chapter': metadata['pages'].get(doc_id, {}).get('chapter', 'N/A')
                }
            })
    return sorted(results, key=lambda x: -x['metadata']['page'])