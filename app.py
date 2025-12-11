import os
import time
import base64
from flask import Flask, render_template_string, request, send_file
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# ==========================================
# 1. HTML 界面 (无需修改)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>网页转 PDF 工具 (内存优化版)</title>
    <style>
        :root { --apple-blue: #0071e3; --apple-gray: #f5f5f7; --text: #1d1d1f; }
        body { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif; background: var(--apple-gray); color: var(--text); display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); width: 100%; max-width: 500px; text-align: center; }
        h1 { font-weight: 600; margin-bottom: 30px; }
        input { width: 90%; padding: 15px; border: 1px solid #d2d2d7; border-radius: 12px; font-size: 16px; margin-bottom: 20px; outline: none; }
        button { background: var(--apple-blue); color: white; border: none; padding: 15px 40px; border-radius: 99px; font-size: 16px; cursor: pointer; }
        button:hover { opacity: 0.9; }
        .loading { display: none; margin-top: 20px; color: #86868b; }
    </style>
</head>
<body>
    <div class="container">
        <h1>网页转 PDF</h1>
        <form method="POST" onsubmit="document.getElementById('msg').style.display='block';">
            <input type="text" name="url" placeholder="粘贴网址 (例如 https://mp.weixin.qq.com/...)" required>
            <br>
            <button type="submit">生成并下载</button>
        </form>
        <div class="loading" id="msg">正在启动浏览器渲染...这可能需要 15-30 秒</div>
    </div>
</body>
</html>
"""

# ==========================================
# 2. 核心逻辑 (关键修改部分)
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads')
# 确保这里的文件名和你上传到 GitHub 的一模一样！
FONT_PATH = os.path.join(BASE_DIR, 'fonts', 'NotoSansCJKsc-Regular.otf') 

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

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
                # 打印详细错误到日志，方便排查
                print(f"❌ 严重错误: {e}")
                return f"服务器撑不住了或发生错误: {str(e)}"
    return render_template_string(HTML_TEMPLATE)

def get_font_base64_lazy():
    """
    【懒加载优化】
    只有在真正生成 PDF 的那一刻才读取文件，
    防止程序一启动就因为内存不够而崩溃。
    """
    try:
        if not os.path.exists(FONT_PATH):
            print(f"⚠️ 警告: 依然找不到字体文件: {FONT_PATH}")
            return None
        
        print("📥 正在临时读取字体文件到内存...")
        with open(FONT_PATH, "rb") as f:
            # 读取并编码
            data = base64.b64encode(f.read()).decode("utf-8")
            print("✅ 字体读取成功")
            return data
    except Exception as e:
        print(f"⚠️ 读取字体失败: {e}")
        return None

def generate_pdf(url):
    print(f"🚀 收到任务: {url}")
    filename = f"web_page_{int(time.time())}.pdf"
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    
    # 1. 临时获取字体数据 (用完会自动释放内存)
    font_data = get_font_base64_lazy()
    
    font_css = ""
    if font_data:
        font_css = f"""
        @font-face {{
            font-family: 'MyCustomFont';
            src: url(data:font/otf;base64,{font_data}) format('opentype');
        }}
        body, h1, h2, h3, h4, h5, h6, p, div, span, a, li, strong, b {{
            font-family: 'MyCustomFont', sans-serif !important;
        }}
        """

    with sync_playwright() as p:
        # 添加参数优化内存使用
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage'] # 关键优化：防止内存溢出
        )
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            page.goto(url, wait_until='networkidle', timeout=60000)
            
            if font_css:
                print("💉 正在注入字体样式...")
                page.add_style_tag(content=font_css)
                time.sleep(1) # 给浏览器一点时间解析字体
            
            # 简单滚动一下，触发懒加载
            page.evaluate("window.scrollTo(0, 500)")
            time.sleep(1)
            
            print("🖨️ 开始生成 PDF...")
            page.pdf(
                path=filepath,
                format="A4",
                print_background=True,
                margin={"top": "1cm", "bottom": "1cm", "left": "1cm", "right": "1cm"}
            )
            print("✅ PDF 生成完毕")
        finally:
            browser.close()
            
    return filepath

if __name__ == '__main__':
    app.run(debug=True, port=5001)