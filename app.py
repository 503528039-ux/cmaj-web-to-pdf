import os
import time
import subprocess
from flask import Flask, render_template_string, request, send_file
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# ==========================================
# 1. HTML 界面 (增加了侦探面板)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>网页转 PDF (字体侦探版)</title>
    <style>
        :root { --apple-blue: #0071e3; --apple-gray: #f5f5f7; --text: #1d1d1f; }
        body { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif; background: var(--apple-gray); color: var(--text); display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
        .container { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); width: 100%; max-width: 600px; text-align: center; }
        h1 { font-weight: 600; margin-bottom: 20px; }
        .debug-box { background: #333; color: #0f0; padding: 15px; border-radius: 8px; text-align: left; font-family: monospace; font-size: 12px; margin-bottom: 20px; overflow-x: auto; white-space: pre-wrap; }
        input { width: 90%; padding: 15px; border: 1px solid #d2d2d7; border-radius: 12px; font-size: 16px; margin-bottom: 20px; outline: none; }
        button { background: var(--apple-blue); color: white; border: none; padding: 15px 40px; border-radius: 99px; font-size: 16px; cursor: pointer; }
        .loading { display: none; margin-top: 20px; color: #86868b; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 字体侦探面板</h1>
        
        <div class="debug-box">
            <strong>[服务器中文字体列表]:</strong><br>
            {{ font_info }}
            <br>
            <strong>[fonts文件夹检查]:</strong><br>
            {{ file_check }}
        </div>

        <form method="POST" onsubmit="document.getElementById('msg').style.display='block';">
            <input type="text" name="url" placeholder="粘贴网址 (例如 https://mp.weixin.qq.com/...)" required>
            <br>
            <button type="submit">生成并下载</button>
        </form>
        <div class="loading" id="msg">正在生成中，请耐心等待 30 秒...</div>
    </div>
</body>
</html>
"""

# ==========================================
# 2. 核心逻辑
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads')
FONTS_DIR = os.path.join(BASE_DIR, 'fonts')

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def get_system_fonts():
    """侦探函数：询问 Linux 系统到底装了什么字体"""
    try:
        # 1. 检查中文字体
        output = subprocess.getoutput("fc-list :lang=zh")
        if not output:
            output = "❌ 未检测到任何中文字体！系统可能是纯英文环境。"
        
        # 2. 检查 fonts 文件夹里有没有文件
        if os.path.exists(FONTS_DIR):
            files = os.listdir(FONTS_DIR)
            file_check = f"✅ fonts 文件夹存在，包含: {files}"
        else:
            file_check = "❌ 警告: fonts 文件夹不存在！"
            
        return output, file_check
    except Exception as e:
        return f"检测出错: {e}", "未知"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            url = url.strip()
            if url.startswith('ps://'): url = 'htt' + url
            elif not url.startswith('http'): url = 'https://' + url
            try:
                pdf_path = generate_pdf(url)
                return send_file(pdf_path, as_attachment=True)
            except Exception as e:
                return f"生成失败: {str(e)}"

    # 每次打开网页，都运行一次侦探函数
    font_info, file_check = get_system_fonts()
    return render_template_string(HTML_TEMPLATE, font_info=font_info, file_check=file_check)

def generate_pdf(url):
    filename = f"web_page_{int(time.time())}.pdf"
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    
    with sync_playwright() as p:
        # 启动参数优化
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage'] 
        )
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            page.goto(url, wait_until='networkidle', timeout=60000)
            
            # 【动态 CSS】: 这里我们不再写死，而是稍微宽容一点
            # 只要系统里有任何一种黑体，它都应该能匹配上
            page.add_style_tag(content="""
                body, h1, h2, h3, h4, h5, h6, p, div, span, a, li {
                    font-family: 'Noto Sans CJK SC', 'Source Han Sans CN', 'Microsoft YaHei', 'SimHei', sans-serif !important;
                }
            """)
            
            time.sleep(1)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            page.pdf(
                path=filepath,
                format="A4",
                print_background=True,
                margin={"top": "1cm", "bottom": "1cm", "left": "1cm", "right": "1cm"}
            )
        finally:
            browser.close()
            
    return filepath

if __name__ == '__main__':
    app.run(debug=True, port=5001)