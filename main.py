import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from faster_whisper import WhisperModel
from docx import Document

app = FastAPI()

# ローカルのWhisperモデルをロード（初回のみ自動ダウンロード）
MODEL_SIZE = "small"
print(f"Loading Whisper model ({MODEL_SIZE})...")
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
print("Model loaded successfully!")

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>キラキラ・ローカル文字起こし</title>
        <style>
            :root {
                --bg-gradient: linear-gradient(135deg, #fbcfe8 0%, #e0e7ff 50%, #ccfbf1 100%);
                --card-bg: rgba(255, 255, 255, 0.85);
                --primary-color: #ec4899;
                --primary-hover: #db2777;
                --text-color: #374151;
                --border-color: #f472b6;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: var(--bg-gradient);
                background-attachment: fixed;
                color: var(--text-color);
                margin: 0;
                padding: 10px;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                box-sizing: border-box;
            }
            .container {
                width: 100%;
                max-width: 820px;
                background: var(--card-bg);
                backdrop-filter: blur(10px);
                padding: 25px;
                border-radius: 20px;
                box-shadow: 0 15px 35px rgba(236, 72, 153, 0.2);
                border: 2px solid rgba(255, 255, 255, 0.6);
                position: relative;
                overflow: hidden;
            }
            /* キラキラ光る背景の演出 */
            .container::before {
                content: "✨ ⭐ 💖 ✨ ⭐";
                position: absolute;
                top: 10px;
                right: 20px;
                font-size: 1.2rem;
                opacity: 0.6;
                animation: sparkle 3s infinite alternate;
            }
            @keyframes sparkle {
                0% { transform: scale(1); opacity: 0.4; }
                100% { transform: scale(1.1); opacity: 0.9; }
            }
            .header-flex {
                display: flex;
                align-items: center;
                gap: 15px;
                border-bottom: 2px dashed #fbcfe8;
                padding-bottom: 12px;
                margin-bottom: 15px;
            }
            .mascot {
                font-size: 2.5rem;
                background: #fdf2f8;
                padding: 10px;
                border-radius: 50%;
                box-shadow: 0 4px 10px rgba(236, 72, 153, 0.15);
                animation: float 2s ease-in-out infinite alternate;
            }
            @keyframes float {
                0% { transform: translateY(0px); }
                100% { transform: translateY(-5px); }
            }
            h2 {
                margin: 0;
                font-size: 1.4rem;
                color: #db2777;
            }
            .subtitle {
                font-size: 0.85rem;
                color: #6b7280;
                margin-top: 3px;
            }
            .drop-zone {
                border: 2px dashed var(--border-color);
                border-radius: 14px;
                padding: 20px;
                text-align: center;
                background: rgba(255, 241, 242, 0.6);
                cursor: pointer;
                transition: all 0.2s;
                margin-bottom: 15px;
            }
            .drop-zone.dragover {
                background: rgba(252, 231, 243, 0.9);
                border-color: #db2777;
                transform: scale(1.01);
            }
            .drop-zone p {
                margin: 0 0 6px;
                color: #4b5563;
                font-weight: 500;
                font-size: 0.95rem;
            }
            .file-info {
                font-weight: bold;
                color: #db2777;
                margin-top: 4px;
                font-size: 0.9rem;
            }
            .btn-container {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
            }
            button {
                background: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%);
                color: white;
                border: none;
                padding: 11px 16px;
                font-size: 0.95rem;
                font-weight: 600;
                border-radius: 10px;
                cursor: pointer;
                transition: all 0.2s;
                flex: 1;
                box-shadow: 0 4px 15px rgba(236, 72, 153, 0.35);
            }
            button:hover {
                opacity: 0.9;
                transform: translateY(-2px);
            }
            button:active {
                transform: translateY(0);
            }
            button.secondary {
                background: linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%);
                box-shadow: 0 4px 15px rgba(139, 92, 246, 0.35);
            }
            button.success {
                background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
                box-shadow: 0 4px 15px rgba(16, 185, 129, 0.35);
            }
            #status {
                font-weight: 600;
                color: #d97706;
                margin-bottom: 8px;
                font-size: 0.9rem;
                min-height: 20px;
                text-align: center;
            }
            textarea {
                width: 100%;
                height: 360px;
                padding: 12px;
                border: 2px solid #fbcfe8;
                border-radius: 10px;
                font-family: inherit;
                font-size: 0.95rem;
                line-height: 1.5;
                resize: vertical;
                box-sizing: border-box;
                background: rgba(255, 255, 255, 0.9);
                color: #1f2937;
            }
            input[type="file"] {
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header-flex">
                <div class="mascot">🎤✨</div>
                <div>
                    <h2>キラキラ・ローカル文字起こし AI</h2>
                    <div class="subtitle">お気に入りの音声をポイッと置いてね！完全ローカル・プライバシー安全安心仕様</div>
                </div>
            </div>
            
            <div class="drop-zone" id="dropZone" onclick="document.getElementById('audioFile').click()">
                <p>🎵 音声ファイルをここにドラッグ＆ドロップしてね！<br><span style="font-size: 0.8rem; color: #6b7280;">（クリックして選択もOK / MP3, WAV, M4A, AACなど対応）</span></p>
                <div class="file-info" id="fileInfo">ファイルが選択されていません</div>
                <input type="file" id="audioFile" accept="audio/*,.mp3,.wav,.m4a,.aac,.flac,.ogg">
            </div>

            <div class="btn-container">
                <button onclick="transcribe()">💖 文字起こしスタート</button>
                <button class="secondary" onclick="copyResult()">📋 結果をコピー</button>
                <button class="success" onclick="downloadWord()">📝 Wordで保存</button>
            </div>

            <div id="status"></div>
            <textarea id="result" placeholder="ここにキラキラな文字起こし結果が表示されるよ…✨"></textarea>
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
                fileInfo.innerText = `✨ 選択中: ${file.name}`;
            }

            async function transcribe() {
                if (!selectedFile) {
                    alert('音声ファイルを選んでね！');
                    return;
                }

                const formData = new FormData();
                formData.append('file', selectedFile);

                status.innerText = '🌟 音声を解析中だよ…！AIががんばって文字にしています！';
                result.value = '';

                try {
                    const response = await fetch('/transcribe', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    if (response.ok) {
                        result.value = data.text;
                        status.innerText = '🎉 文字起こしが完了したよ！やったね！';
                    } else {
                        status.innerText = '💧 エラーが起きちゃいました…';
                        result.value = data.detail;
                    }
                } catch (err) {
                    status.innerText = '💥 通信エラーが発生しました';
                    result.value = err;
                }
            }

            function copyResult() {
                if (!result.value) {
                    alert('コピーするテキストがないよ！');
                    return;
                }
                navigator.clipboard.writeText(result.value).then(() => {
                    alert('✨ クリップボードにコピーしたよ！');
                });
            }

            async function downloadWord() {
                const text = result.value;
                if (!text) {
                    alert('保存するテキストがないよ！');
                    return;
                }

                status.innerText = '📝 Wordファイルを作成中だよ…';

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
                        status.innerText = '🎉 Wordファイルのダウンロードが成功したよ！';
                    } else {
                        status.innerText = '💧 Wordの作成に失敗しました';
                    }
                } catch (err) {
                    status.innerText = '💥 エラーが発生しました';
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    temp_file_path = f"temp_{file.filename}"
    try:
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())

        segments, info = model.transcribe(temp_file_path, beam_size=5, language="ja")
        
        full_text = ""
        for segment in segments:
            full_text += f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n"

        return {"text": full_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.post("/download-word")
async def download_word(data: dict):
    text = data.get("text", "")
    doc = Document()
    doc.add_heading('文字起こし結果', 0)
    doc.add_paragraph(text)
    
    file_path = "temp_output.docx"
    doc.save(file_path)
    
    return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename="文字起こし結果.docx")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
