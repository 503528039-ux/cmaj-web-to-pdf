import os
import time
import subprocess
from flask import Flask, render_template_string, request, send_file
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# ==========================================
# 0. 启动时自动安装字体 (保留这个功能，防止乱码)
# ==========================================
def install_fonts_at_startup():
    print("📦 正在初始化字体环境...")
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        local_fonts_dir = os.path.join(base_dir, 'fonts')
        system_font_dir = os.path.expanduser("~/.fonts")
        
        if not os.path.exists(system_font_dir):
            os.makedirs(system_font_dir)

        if os.path.exists(local_fonts_dir):
            subprocess.run(f"cp {local_fonts_dir}/* {system_font_dir}/", shell=True)
            subprocess.run("fc-cache -fv", shell=True)
            print("✅ 字体安装成功")
        else:
            print("⚠️ 未找到 fonts 文件夹，跳过安装")
    except Exception as e:
        print(f"❌ 字体安装出错: {e}")

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
    <title>网页转 PDF (高保真还原版)</title>
    <style>
        :root { --apple-blue: #0071e3; --apple-gray: #f5f5f7; --text: #1d1d1f; }
        body { font-family: "Noto Sans CJK SC", -apple-system, sans-serif; background: var(--apple-gray); color: var(--text); display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); width: 100%; max-width: 500px; text-align: center; }
        h1 { font-weight: 600; margin-bottom: 30px; }
        input { width: 90%; padding: 15px; border: 1px solid #d2d2d7; border-radius: 12px; font-size: 16px; margin-bottom: 20px; outline: none; }
        button { background: var(--apple-blue); color: white; border: none; padding: 15px 40px; border-radius: 99px; font-size: 16px; cursor: pointer; }
        .loading { display: none; margin-top: 20px; color: #86868b; }
    </style>
</head>
<body>
    <div class="container">
        <h1>网页转 PDF (原貌还原)</h1>
        <form method="POST" onsubmit="document.getElementById('msg').style.display='block';">
            <input type="text" name="url" placeholder="粘贴网址..." required>
            <br>
            <button type="submit">生成并下载</button>
        </form>
        <div class="loading" id="msg">正在高保真渲染，可能需要 30 秒...</div>
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
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        # 1. 设置更大的视口，确保网页认为是“桌面电脑”在访问
        context = browser.new_context(
            viewport={'width': 1600, 'height': 1200},
            device_scale_factor=2 # 类似于 Retina 屏幕，图片更清晰
        )
        page = context.new_page()
        
        print(f"🚀 访问: {url}")
        page.goto(url, wait_until='networkidle', timeout=60000)
        
        # 2. 【关键】强制模拟“屏幕显示” (解决排版错乱的核心)
        # 这会让网页觉得它还在屏幕上，而不是在打印机里
        page.emulate_media(media="screen")
        
        # 注入字体样式 (双保险)
        page.add_style_tag(content="""
            body, h1, h2, h3, h4, h5, h6, p, div, span, a {
                font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif !important;
            }
            /* 隐藏一些常见的浮动广告 */
            .ad-banner, .popup, .cookie-consent { display: none !important; }
        """)
        
        # 滚动页面以触发懒加载
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        page.evaluate("window.scrollTo(0, 0)") # 滚回去，准备截图
        time.sleep(1)
        
        print("🖨️ 生成 PDF...")
        page.pdf(
            path=filepath,
            format="A4",
            print_background=True, # 必须开启背景打印
            scale=0.6,             # 【关键】缩放 60% 以便把宽屏内容塞进 A4 纸，避免挤压
            margin={"top": "0.5cm", "bottom": "0.5cm", "left": "0.5cm", "right": "0.5cm"}
        )
        browser.close()
            
    return filepath

if __name__ == '__main__':
    app.run(debug=True, port=5001)