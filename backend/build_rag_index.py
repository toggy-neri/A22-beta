import os
import argparse
import json
from typing import List, Dict
from rag_service import get_rag_service, RAGService

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), "rag_data")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

def load_text_file(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def load_json_file(file_path: str) -> List[Dict]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if 'documents' in data:
            return data['documents']
        elif 'texts' in data:
            return [{'content': t} for t in data['texts']]
        else:
            return [data]
    return []

def load_csv_file(file_path: str) -> List[Dict]:
    import csv
    documents = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            content = row.get('content', '') or row.get('text', '') or row.get('body', '')
            if content:
                documents.append({
                    'content': content,
                    'metadata': {k: v for k, v in row.items() if k not in ['content', 'text', 'body']}
                })
    return documents

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        if end < len(text):
            last_period = chunk.rfind('。')
            last_newline = chunk.rfind('\n')
            last_space = chunk.rfind(' ')
            
            split_pos = max(last_period, last_newline, last_space)
            if split_pos > start + chunk_size // 2:
                chunk = text[start:split_pos + 1]
                end = split_pos + 1
        
        chunks.append(chunk.strip())
        start = end - overlap if end < len(text) else end
    
    return [c for c in chunks if c]

def load_documents_from_directory(directory: str) -> List[Dict]:
    documents = []
    
    if not os.path.exists(directory):
        print(f"[build_rag] Directory not found: {directory}")
        return documents
    
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        
        if not os.path.isfile(file_path):
            continue
        
        print(f"[build_rag] Processing: {filename}")
        
        try:
            if filename.endswith('.txt'):
                content = load_text_file(file_path)
                chunks = chunk_text(content)
                for i, chunk in enumerate(chunks):
                    documents.append({
                        'content': chunk,
                        'metadata': {
                            'source': filename,
                            'chunk': i,
                            'total_chunks': len(chunks)
                        }
                    })
            
            elif filename.endswith('.json'):
                items = load_json_file(file_path)
                for item in items:
                    content = item.get('content', '') or item.get('text', '') or item.get('body', '')
                    if content:
                        chunks = chunk_text(content)
                        for i, chunk in enumerate(chunks):
                            metadata = item.get('metadata', {})
                            metadata['source'] = filename
                            metadata['chunk'] = i
                            documents.append({
                                'content': chunk,
                                'metadata': metadata
                            })
            
            elif filename.endswith('.csv'):
                items = load_csv_file(file_path)
                for item in items:
                    documents.append(item)
            
            elif filename.endswith('.md'):
                content = load_text_file(file_path)
                chunks = chunk_text(content)
                for i, chunk in enumerate(chunks):
                    documents.append({
                        'content': chunk,
                        'metadata': {
                            'source': filename,
                            'chunk': i,
                            'total_chunks': len(chunks)
                        }
                    })
        
        except Exception as e:
            print(f"[build_rag] Error processing {filename}: {e}")
    
    return documents

def build_index(data_dir: str, clear_existing: bool = False):
    rag = get_rag_service()
    
    if clear_existing:
        print("[build_rag] Clearing existing collection...")
        rag.clear_collection()
    
    documents = load_documents_from_directory(data_dir)
    
    if not documents:
        print(f"[build_rag] No documents found in {data_dir}")
        print("[build_rag] Creating sample data directory and example file...")
        create_sample_data(data_dir)
        return
    
    print(f"[build_rag] Found {len(documents)} document chunks to index")
    
    contents = [doc['content'] for doc in documents]
    metadatas = [doc.get('metadata', {}) for doc in documents]
    
    batch_size = 100
    total_added = 0
    
    for i in range(0, len(contents), batch_size):
        batch_contents = contents[i:i + batch_size]
        batch_metadatas = metadatas[i:i + batch_size]
        batch_ids = [f"doc_{i + j}" for j in range(len(batch_contents))]
        
        added = rag.add_documents(batch_contents, batch_metadatas, batch_ids)
        total_added += added
        print(f"[build_rag] Indexed batch {i // batch_size + 1}: {added} documents")
    
    print(f"[build_rag] Total documents indexed: {total_added}")
    print(f"[build_rag] Collection now contains: {rag.get_document_count()} documents")

def create_sample_data(data_dir: str):
    os.makedirs(data_dir, exist_ok=True)
    
    sample_file = os.path.join(data_dir, "sample_knowledge.txt")
    sample_content = """心理健康基础知识

一、什么是心理健康？
心理健康是指个体在心理、情感和行为方面的良好状态。一个心理健康的人能够正常地学习、工作和生活，能够与他人建立和维持良好的人际关系，能够适应环境的变化，并能够有效地应对生活中的压力和挑战。

二、常见心理问题
1. 焦虑症：表现为过度担忧、紧张不安，可能伴有心悸、出汗等身体症状。
2. 抑郁症：表现为持续的情绪低落、兴趣减退、精力下降，严重时可能出现自伤想法。
3. 压力过大：长期处于高压状态可能导致身心疲惫、失眠、注意力不集中等问题。

三、心理调适方法
1. 规律作息：保持充足的睡眠，定时起床和就寝。
2. 适度运动：每周进行3-5次中等强度的有氧运动，如散步、游泳、瑜伽等。
3. 社交活动：与家人朋友保持联系，分享自己的感受和想法。
4. 放松训练：学习深呼吸、冥想、渐进性肌肉放松等技巧。
5. 寻求帮助：当感到无法独自应对时，及时寻求专业心理咨询师的帮助。

四、何时需要寻求专业帮助
1. 情绪问题持续两周以上且影响日常生活
2. 出现自伤或自杀的想法
3. 无法控制的焦虑或恐慌发作
4. 严重的睡眠障碍
5. 物质滥用问题

五、心理咨询的意义
心理咨询是一种专业的心理帮助方式，通过与咨询师的交谈，帮助来访者了解自己的问题，学习应对技巧，改善心理状态。心理咨询不是只有"有问题"的人才需要，任何希望提升自我认知、改善人际关系的人都可以从中受益。
"""
    
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(sample_content)
    
    print(f"[build_rag] Created sample file: {sample_file}")

def main():
    parser = argparse.ArgumentParser(description='Build RAG vector database from documents')
    parser.add_argument('--data-dir', type=str, default=DEFAULT_DATA_DIR,
                        help=f'Directory containing documents to index (default: {DEFAULT_DATA_DIR})')
    parser.add_argument('--clear', action='store_true',
                        help='Clear existing collection before indexing')
    parser.add_argument('--query', type=str, default=None,
                        help='Query the knowledge base after building')
    parser.add_argument('--list', action='store_true',
                        help='List all documents in the collection')
    
    args = parser.parse_args()
    
    if args.list:
        rag = get_rag_service()
        docs = rag.list_documents()
        print(f"\n[build_rag] Listing {len(docs)} documents:")
        for doc in docs[:10]:
            print(f"  - {doc['id']}: {doc['content'][:100]}...")
        if len(docs) > 10:
            print(f"  ... and {len(docs) - 10} more")
        return
    
    build_index(args.data_dir, args.clear)
    
    if args.query:
        rag = get_rag_service()
        context = rag.get_context_for_query(args.query)
        print(f"\n[build_rag] Query: {args.query}")
        print(f"[build_rag] Context:\n{context}")

if __name__ == "__main__":
    main()
