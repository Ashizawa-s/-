import os
import math
import soundfile as sf
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from faster_whisper import WhisperModel
from docx import Document

app = FastAPI()

MODEL_SIZE = "small"
print(f"Loading Whisper model ({MODEL_SIZE})...")
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
print("Model loaded successfully!")

def format_time(seconds: float) -> str:
    m = math.floor(seconds / 60)
    s = math.floor(seconds % 60)
    return f"{m:02d}:{s:02d}"

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>ローカル音声文字起こしシステム</title>
        <style>
            :root {
                --bg-color: #f1f5f9;
                --card-bg: #ffffff;
                --primary-color: #2563eb;
                --primary-hover: #1d4ed8;
                --text-color: #1e293b;
                --border-color: #cbd5e1;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-color);
                margin: 0;
                padding: 15px;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                box-sizing: border-box;
            }
            .container {
                width: 100%;
                max-width: 800px;
                background: var(--card-bg);
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                border: 1px solid #e2e8f0;
            }
            .header-flex {
                border-bottom: 2px solid #f1f5f9;
                padding-bottom: 12px;
                margin-bottom: 20px;
            }
            h2 {
                margin: 0;
                font-size: 1.4rem;
                color: #0f172a;
            }
            .subtitle {
                font-size: 0.85rem;
                color: #64748b;
                margin-top: 4px;
            }
            .drop-zone {
                border: 2px dashed var(--border-color);
                border-radius: 8px;
                padding: 22px;
                text-align: center;
                background: #f8fafc;
                cursor: pointer;
                transition: all 0.2s;
                margin-bottom: 15px;
            }
            .drop-zone.dragover {
                background: #eff6ff;
                border-color: var(--primary-color);
            }
            .drop-zone p {
                margin: 0 0 6px;
                color: #475569;
                font-weight: 500;
                font-size: 0.95rem;
            }
            .file-info {
                font-weight: bold;
                color: var(--primary-color);
                margin-top: 4px;
                font-size: 0.9rem;
            }
            .btn-container {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
            }
            button {
                background-color: var(--primary-color);
                color: white;
                border: none;
                padding: 10px 16px;
                font-size: 0.95rem;
                font-weight: 600;
                border-radius: 6px;
                cursor: pointer;
                transition: background-color 0.2s;
                flex: 1;
            }
            button:hover {
                background-color: var(--primary-hover);
            }
            button.secondary {
                background-color: #475569;
            }
            button.secondary:hover {
                background-color: #334155;
            }
            button.success {
                background-color: #0d9488;
            }
            button.success:hover {
                background-color: #0f766e;
            }
            #status {
                font-weight: 600;
                color: #d97706;
                margin-bottom: 8px;
                font-size: 0.9rem;
                min-height: 20px;
            }
            textarea {
                width: 100%;
                height: 380px;
                padding: 12px;
                border: 1px solid var(--border-color);
                border-radius: 6px;
                font-family: inherit;
                font-size: 0.95rem;
                line-height: 1.5;
                resize: vertical;
                box-sizing: border-box;
                background: #fdfdfd;
                color: #1e293b;
            }
            input[type="file"] {
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header-flex">
                <h2>ローカル音声文字起こしシステム</h2>
                <div class="subtitle">音声ファイルを左右チャンネルに分離して正確に文字起こしします</div>
            </div>
            
            <div class="drop-zone" id="dropZone" onclick="document.getElementById('audioFile').click()">
                <p>音声ファイルをここにドラッグ＆ドロップしてください<br><span style="font-size: 0.8rem; color: #64748b;">（クリックしてファイル選択も可能 / MP3, WAVなど）</span></p>
                <div class="file-info" id="fileInfo">ファイルが選択されていません</div>
                <input type="file" id="audioFile" accept="audio/*,.mp3,.wav,.m4a,.aac,.flac,.ogg">
            </div>

            <div class="btn-container">
                <button onclick="transcribe()">文字起こし開始</button>
                <button class="secondary" onclick="copyResult()">結果をコピー</button>
                <button class="success" onclick="downloadWord()">Wordで保存</button>
            </div>

            <div id="status"></div>
            <textarea id="result" placeholder="ここに文字起こし結果が表示されます..."></textarea>
        </div>

        <script>
            const dropZone = document.getElementById('dropZone');
            const fileInput = document.getElementById('audioFile');
            const fileInfo = document.getElementById('fileInfo');
            const status = document.getElementById('status');
            const result = document.getElementById('result');
            let selectedFile = null;

            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    dropZone.classList.add('dragover');
                }, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    dropZone.classList.remove('dragover');
                }, false);
            });

            dropZone.addEventListener('drop', (e) => {
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    fileInput.files = files;
                    handleFileSelection(files[0]);
                }
            }, false);

            fileInput.addEventListener('change', () => {
                if (fileInput.files.length > 0) {
                    handleFileSelection(fileInput.files[0]);
                }
            });

            function handleFileSelection(file) {
                selectedFile = file;
                fileInfo.innerText = `選択中: ${file.name}`;
            }

            async function transcribe() {
                if (!selectedFile) {
                    alert('音声ファイルを選択してください');
                    return;
                }

                const formData = new FormData();
                formData.append('file', selectedFile);

                status.innerText = '左右チャンネルを分離して文字起こし中... しばらくお待ちください';
                result.value = '';

                try {
                    const response = await fetch('/transcribe', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    if (response.ok) {
                        result.value = data.text;
                        status.innerText = '文字起こしが完了しました';
                    } else {
                        status.innerText = 'エラーが発生しました';
                        result.value = data.detail;
                    }
                } catch (err) {
                    status.innerText = '通信エラーが発生しました';
                    result.value = err;
                }
            }

            function copyResult() {
                if (!result.value) {
                    alert('コピーするテキストがありません');
                    return;
                }
                navigator.clipboard.writeText(result.value).then(() => {
                    alert('クリップボードにコピーしました');
                });
            }

            async function downloadWord() {
                const text = result.value;
                if (!text) {
                    alert('保存するテキストがありません');
                    return;
                }

                status.innerText = 'Wordファイルを作成中...';

                try {
                    const response = await fetch('/download-word', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: text })
                    });

                    if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = '文字起こし結果.docx';
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                        status.innerText = 'Wordファイルのダウンロードが完了しました';
                    } else {
                        status.innerText = 'Wordの作成に失敗しました';
                    }
                } catch (err) {
                    status.innerText = 'エラーが発生しました';
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    temp_file_path = f"temp_{file.filename}"
    ap_file_path = "temp_ap.wav"
    customer_file_path = "temp_customer.wav"
    
    try:
        content = await file.read()
        with open(temp_file_path, "wb") as buffer:
            buffer.write(content)

        # 音声データを読み込み、ステレオ分離を試みる
        data, samplerate = sf.read(temp_file_path)
        
        all_segments = []

        if data.ndim == 2 and data.shape[1] >= 2:
            # ステレオの場合：Lチャンネル(AP)とRチャンネル(客)に分ける
            sf.write(ap_file_path, data[:, 0], samplerate)
            sf.write(customer_file_path, data[:, 1], samplerate)

            ap_segments, _ = model.transcribe(ap_file_path, beam_size=5, language="ja")
            for seg in ap_segments:
                if len(seg.text.strip()) > 0:
                    all_segments.append({"start": seg.start, "speaker": "AP", "text": seg.text.strip()})

            customer_segments, _ = model.transcribe(customer_file_path, beam_size=5, language="ja")
            for seg in customer_segments:
                if len(seg.text.strip()) > 0:
                    all_segments.append({"start": seg.start, "speaker": "客", "text": seg.text.strip()})
        else:
            # モノラルの場合（フォールバック）
            segments, _ = model.transcribe(temp_file_path, beam_size=5, language="ja")
            for seg in segments:
                if len(seg.text.strip()) > 0:
                    all_segments.append({"start": seg.start, "speaker": "不明", "text": seg.text.strip()})

        # 時間順にソート
        all_segments.sort(key=lambda x: x["start"])

        full_text = f"対象ファイル: {file.filename}\n\n"
        for seg in all_segments:
            time_tag = format_time(seg["start"])
            full_text += f"[{time_tag}] {seg['speaker']}: {seg['text']}\n"

        return {"text": full_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        for p in [temp_file_path, ap_file_path, customer_file_path]:
            if os.path.exists(p):
                os.remove(p)

@app.post("/download-word")
async def download_word(data: dict):
    text = data.get("text", "")
    doc = Document()
    doc.add_heading('通話文字起こしログ', 0)
    doc.add_paragraph(text)
    
    file_path = "temp_output.docx"
    doc.save(file_path)
    
    return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename="文字起こし結果.docx")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
