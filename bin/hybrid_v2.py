#!/usr/bin/env python3
"""Hybrid OCR v2: mac-ocr document + GLM-OCR
Workflow:
1. mac-ocr document → structured text + paragraphs (Neural Engine)
2. Detect pages needing GLM-OCR
3. GLM-OCR → table + formula
4. Merge results → markdown
"""
import subprocess, sys, os, time, json, re, fitz
from pathlib import Path

# Config
MAC_OCR_DEV = os.path.expanduser('~/bin/mac-ocr-dev')
OLLAMA_URL = "http://localhost:11434/api/generate"
GLM_MODEL = "glm-ocr:latest"
GLM_PROMPT = "读取这个页面的所有内容，包括表格、公式和文字。不要停止，提取全部内容。用markdown格式输出。"
MAX_GLM_TOKENS = 16384

def run_mac_ocr_document(img_path):
    """Run mac-ocr document mode, return structured text."""
    result = subprocess.run(
        [MAC_OCR_DEV, 'document', img_path, '--format', 'json'],
        capture_output=True, text=True
    )
    try:
        data = json.loads(result.stdout)
        if isinstance(data, list) and len(data) > 0:
            doc = data[0]
            documents = doc.get('documents', [])
            if documents:
                content = documents[0].get('content', {})
                paragraphs = content.get('paragraphs', [])
                
                # Extract text from paragraphs
                texts = []
                for p in paragraphs:
                    lines = p.get('lines', [])
                    text = ' '.join([l.get('transcript', '') for l in lines])
                    if text.strip():
                        texts.append(text.strip())
                
                full_text = '\n'.join(texts)
                return full_text, len(paragraphs)
    except:
        pass
    return '', 0

def run_mac_ocr_plain(img_path):
    """Fallback: run mac-ocr plain mode."""
    result = subprocess.run(
        ['mac-ocr', img_path, '--format', 'json'],
        capture_output=True, text=True
    )
    try:
        data = json.loads(result.stdout)
        if isinstance(data, list) and len(data) > 0:
            page = data[0]
            text = page.get('text', '')
            obs = page.get('observations', [])
            avg_conf = sum(o.get('confidence', 0) for o in obs) / max(len(obs), 1)
            return text, avg_conf, len(obs)
    except:
        pass
    return '', 0, 0

def run_glm_ocr(img_path):
    """Run GLM-OCR via Ollama, return markdown."""
    import base64, requests
    with open(img_path, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode()
    
    try:
        response = requests.post(OLLAMA_URL, json={
            'model': GLM_MODEL,
            'prompt': GLM_PROMPT,
            'images': [img_b64],
            'stream': False,
            'options': {'num_predict': MAX_GLM_TOKENS, 'temperature': 0, 'num_ctx': 131072}
        }, timeout=180)
        result = response.json()
        return result.get('response', '')
    except Exception as e:
        return f'ERROR: {str(e)}'

def needs_glm_ocr(text):
    """Determine if page needs GLM-OCR based on content."""
    # Has formula patterns
    if re.search(r'[=+\-*/^∫∑∏]|\\frac|\\sqrt|\\sum|\\int|FP|CG|u_max', text):
        return True
    # Has table indicators (multiple numbers in short segments)
    segments = text.split()
    num_segments = sum(1 for s in segments if re.match(r'^\d+\.?\d*$', s))
    if num_segments > 10:
        return True
    # Very short text (might be scan issue)
    if len(text) < 50:
        return True
    return False

def convert_pdf_to_image(pdf_path, page_num, output_path, dpi=200):
    """Convert PDF page to image."""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)
    pix.save(output_path)
    doc.close()

def hybrid_v2(pdf_path, output_dir, start_page=0, end_page=None):
    """Main hybrid OCR workflow v2."""
    os.makedirs(output_dir, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    total = len(doc) if end_page is None else min(end_page, len(doc))
    doc.close()
    
    print(f"=== Hybrid OCR v2: {total} pages ===")
    print(f"PDF: {pdf_path}")
    print(f"Output: {output_dir}")
    print()
    
    results = []
    glm_count = 0
    
    for i in range(start_page, total):
        start_time = time.time()
        
        # Convert to image
        img_path = f'/tmp/_hybrid_v2_p{i}.png'
        convert_pdf_to_image(pdf_path, i, img_path)
        
        # Step 1: mac-ocr document mode (structured)
        doc_text, num_paragraphs = run_mac_ocr_document(img_path)
        
        # Fallback to plain if document mode fails
        if not doc_text:
            doc_text, conf, num_obs = run_mac_ocr_plain(img_path)
        
        # Step 2: Check if needs GLM-OCR
        use_glm = needs_glm_ocr(doc_text)
        
        glm_text = ''
        if use_glm:
            glm_text = run_glm_ocr(img_path)
            glm_count += 1
        
        # Step 3: Choose best output
        if use_glm and glm_text and not glm_text.startswith('ERROR'):
            # GLM-OCR output might have better table/formula
            # But keep document mode structure
            final_text = f"{doc_text}\n\n--- GLM-OCR Table/Formula ---\n\n{glm_text}"
            source = 'hybrid'
        else:
            final_text = doc_text
            source = 'document'
        
        # Save page
        page_file = os.path.join(output_dir, f'page_{i+1:04d}.md')
        with open(page_file, 'w') as f:
            f.write(f'# Page {i+1}\n\n{final_text}\n')
        
        elapsed = time.time() - start_time
        
        entry = {
            'page': i + 1,
            'source': source,
            'paragraphs': num_paragraphs,
            'chars': len(final_text),
            'elapsed': round(elapsed, 1)
        }
        results.append(entry)
        
        # Progress
        status = '📊 GLM+DOC' if use_glm else '📝 DOC'
        print(f'[{i+1}/{total}] {elapsed:.1f}s {status} paras={num_paragraphs} chars={len(final_text)}', flush=True)
        
        # Cleanup
        os.remove(img_path)
        
        # Estimate remaining
        if len(results) > 5:
            avg = sum(r['elapsed'] for r in results[-5:]) / 5
            remaining = (total - i - 1) * avg
            print(f'  Est. remaining: {remaining/60:.1f} min', flush=True)
    
    # Combine all pages
    combined_path = os.path.join(output_dir, 'full_book.md')
    with open(combined_path, 'w') as out:
        for i in range(total):
            page_file = os.path.join(output_dir, f'page_{i+1:04d}.md')
            if os.path.exists(page_file):
                with open(page_file) as f:
                    out.write(f.read() + '\n\n')
    
    # Save stats
    stats_path = os.path.join(output_dir, 'stats.json')
    with open(stats_path, 'w') as f:
        json.dump({
            'total_pages': total,
            'glm_pages': glm_count,
            'doc_pages': total - glm_count,
            'results': results
        }, f, indent=2)
    
    print(f'\n=== Done! ===')
    print(f'Total: {total} pages')
    print(f'Document mode: {total - glm_count} pages')
    print(f'GLM-OCR: {glm_count} pages')
    print(f'Output: {combined_path}')

if __name__ == '__main__':
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else '/Users/mac/Downloads/石油化工设计手册_第三卷_化工单元过程_修订版_下_王子宗主编,_Zizong_Wang,_王子宗主编,_王子宗_2015,_2015.pdf'
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '/Users/mac/ocr-output/石油化工手册_hybrid_v2'
    start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    end = int(sys.argv[4]) if len(sys.argv) > 4 else None
    hybrid_v2(pdf_path, output_dir, start, end)
