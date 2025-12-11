import os
import time
import subprocess
from flask import Flask, render_template_string, request, send_file
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# ==========================================
# 0. 【核心新增】程序启动时，自动安装字体
# ==========================================
def install_fonts_at_startup():
    print("📦 正在初始化字体环境...")
    try:
        # 1. 确定路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        local_fonts_dir = os.path.join(base_dir, 'fonts')
        
        # Linux 用户字体目录
        system_font_dir = os.path.expanduser("~/.fonts")
        
        # 2. 创建系统目录
        if not os.path.exists(system_font_dir):
            os.makedirs(system_font_dir)
            print(f"📂 创建目录: {system_font_dir}")

        # 3. 拷贝字体 (使用 cp 命令)
        # 注意：这里直接执行 Linux 命令，比 Python 复制更快更稳
        if os.path.exists(local_fonts_dir):
            cmd = f"cp {local_fonts_dir}/* {system_font_dir}/"
            subprocess.run(cmd, shell=True, check=True)
            print(f"✅ 已拷贝字体文件到系统目录")
            
            # 4. 刷新缓存
            subprocess.run("fc-cache -fv", shell=True, check=True)
            print("✅ 字体缓存刷新成功！系统已识别字体。")
        else:
            print("⚠️ 警告: 没找到 fonts 文件夹，跳过字体安装。")

    except Exception as e:
        print(f"❌ 字体安装出错: {e}")

# 启动时立即执行安装
install_fonts_at_startup()


# ==========================================
# 1. HTML 界面
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>网页转 PDF (自动修复版)</title>
    <style>
        :root { --apple-blue: #0071e3; --apple-gray: #f5f5f7; --text: #1d1d1f; }
        body { font-family: "Noto Sans CJK SC", "Source Han Sans CN", -apple-system, sans-serif; background: var(--apple-gray); color: var(--text); display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); width: 100%; max-width: 500px; text-align: center; }
        h1 { font-weight: 600; margin-bottom: 30px; }
        input { width: 90%; padding: 15px; border: 1px solid #d2d2d7; border-radius: 12px; font-size: 16px; margin-bottom: 20px; outline: none; }
        button { background: var(--apple-blue); color: white; border: none; padding: 15px 40px; border-radius: 99px; font-size: 16px; cursor: pointer; }
        .loading { display: none; margin-top: 20px; color: #86868b; }
    </style>
</head>
<body>
    <div class="container">
        <h1>网页转 PDF</h1>
        <form method="POST" onsubmit="document.getElementById('msg').style.display='block';">
            <input type="text" name="url" placeholder="粘贴网址..." required>
            <br>
            <button type="submit">生成并下载</button>
        </form>
        <div class="loading" id="msg">正在生成中，请耐心等待...</div>
    </div>
</body>
</html>
"""

# ==========================================
# 2. 核心逻辑
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads')

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            try:
                pdf_path = generate_pdf(url)
                return send_file(pdf_path, as_attachment=True)
            except Exception as e:
                return f"Error: {e}"
    return render_template_string(HTML_TEMPLATE)

def generate_pdf(url):
    filename = f"web_page_{int(time.time())}.pdf"
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        page.goto(url, wait_until='networkidle', timeout=60000)
        
        # 强制指定字体（精确匹配文件名）
        page.add_style_tag(content="""
            body, h1, h2, h3, h4, h5, h6, p, div, span, a {
                font-family: 'Noto Sans CJK SC', 'Noto Sans SC', sans-serif !important;
            }
        """)
        
        time.sleep(1)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        
        page.pdf(path=filepath, format="A4", print_background=True)
        browser.close()
            
    return filepath

if __name__ == '__main__':
    app.run(debug=True, port=5001)