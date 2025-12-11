import os
import time
from flask import Flask, render_template_string, request, send_file
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# ==========================================
# 1. 这里是 HTML 界面代码
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>网页转 PDF 工具</title>
    <style>
        :root { --apple-blue: #0071e3; --apple-gray: #f5f5f7; --text: #1d1d1f; }
        body { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif; background: var(--apple-gray); color: var(--text); display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); width: 100%; max-width: 500px; text-align: center; }
        h1 { font-weight: 600; margin-bottom: 30px; }
        input { width: 90%; padding: 15px; border: 1px solid #d2d2d7; border-radius: 12px; font-size: 16px; margin-bottom: 20px; outline: none; }
        input:focus { border-color: var(--apple-blue); box-shadow: 0 0 0 4px rgba(0,113,227,0.1); }
        button { background: var(--apple-blue); color: white; border: none; padding: 15px 40px; border-radius: 99px; font-size: 16px; cursor: pointer; }
        button:hover { opacity: 0.9; }
        .loading { display: none; margin-top: 20px; color: #86868b; }
    </style>
</head>
<body>
    <div class="container">
        <h1>网页转 PDF</h1>
        <form method="POST" onsubmit="document.getElementById('msg').style.display='block';">
            <input type="text" name="url" placeholder="粘贴网址 (例如 https://www.apple.com.cn)" required>
            <br>
            <button type="submit">生成并下载</button>
        </form>
        <div class="loading" id="msg">正在启动浏览器生成 PDF，请稍候...</div>
    </div>
</body>
</html>
"""

# ==========================================
# 2. 这里是 Python 后端逻辑
# ==========================================

# 获取当前脚本所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads')
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            # === 自动修复网址逻辑 ===
            url = url.strip() # 去除首尾空格
            if url.startswith('ps://'): # 修复你刚才遇到的 ps:// 错误
                url = 'htt' + url
            elif not url.startswith('http'): # 如果忘记写 http，自动补全
                url = 'https://' + url
            # ====================

            try:
                pdf_path = generate_pdf(url)
                return send_file(pdf_path, as_attachment=True)
            except Exception as e:
                return f"❌ 出错啦: {str(e)}"
    
    return render_template_string(HTML_TEMPLATE)

def generate_pdf(url):
    print(f"🚀 收到任务: {url}")
    filename = f"web_page_{int(time.time())}.pdf"
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 这里的 viewport 决定了网页是以“桌面版”还是“手机版”渲染
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            # 访问页面
            page.goto(url, wait_until='networkidle', timeout=60000)
            time.sleep(2) # 等待动态内容加载
            
            # 打印 PDF
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
    print("应用已启动，请在浏览器访问 http://127.0.0.1:5001")
    app.run(debug=True, port=5001)