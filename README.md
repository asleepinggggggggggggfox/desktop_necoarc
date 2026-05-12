# Desktop Neco-Arc

一个透明悬浮的桌面宠物 AI 语音助手。界面中间显示角色图片，左侧显示用户输入，右侧显示 AI 输出。点击录音按钮后，程序会录音、调用讯飞开放平台在线语音识别，再把识别文本发送给 DeepSeek API 获取回复。

## 当前功能

- 透明、无边框、置顶桌面窗口
- 可拖动窗口位置
- 右键菜单退出程序
- 使用 `plan/Neco-Arc_Remake.png` 作为角色图片
- 用户输入气泡为红色系
- AI 输出气泡为绿色系
- 对话气泡根据文本内容自动扩展
- 初始时隐藏“上一次”内容
- 新一轮输入时，上一次 AI 输出会淡出
- 点击式录音：点一次开始，点一次停止
- 讯飞在线语音识别
- DeepSeek 对话回复

## 项目结构

```text
desktop_necoarc/
  main.py
  config.yaml
  requirements.txt
  README.md
  core/
    audio_recorder.py
    config.py
    conversation_state.py
    deepseek_client.py
    xunfei_speech_to_text.py
  ui/
    bubble_widget.py
    character_widget.py
    main_window.py
  plan/
    api.md
    plan.md
    plan_simple.md
    效果图.png
    Neco-Arc_Remake.png
  temp/
    .gitkeep
```

## 安装依赖

```powershell
python -m pip install -r requirements.txt
```

依赖包括：

- `PySide6`：桌面界面
- `sounddevice`：麦克风录音
- `soundfile`：保存 wav 音频
- `websocket-client`：讯飞 WebSocket 识别
- `requests`：DeepSeek HTTP 请求

## API 配置推荐方式

推荐使用“本地前端 + 云端后端代理”模式：

- 本地桌宠：只保存后端代理地址，不保存 API Key
- 阿里云服务器：保存 DeepSeek 和讯飞 API Key
- 本地录音后把 wav 文件发给服务器
- 服务器完成讯飞识别和 DeepSeek 回复
- 服务器只把识别文本和回复文本返回本地

这样即使本地项目目录被分享出去，也不会泄露 API Key。

当前本地 `config.yaml` 已默认使用代理模式：

```yaml
api_mode: proxy
proxy_base_url: http://127.0.0.1:8000
```

部署到阿里云后，把 `proxy_base_url` 改成你的服务器地址，例如：

```yaml
proxy_base_url: http://你的服务器公网IP:8000
```

如果配置了域名和 HTTPS：

```yaml
proxy_base_url: https://api.your-domain.com
```

## 云端后端代理部署

后端代码在：

```text
backend/proxy_server.py
```

在阿里云服务器上安装依赖：

```bash
python -m pip install -r backend/requirements.txt
```

在服务器上设置环境变量：

```bash
export DEEPSEEK_API_KEY="你的 DeepSeek API Key"
export XUNFEI_APP_ID="你的讯飞 APPID"
export XUNFEI_API_KEY="你的讯飞 APIKey"
export XUNFEI_API_SECRET="你的讯飞 APISecret"
```

临时启动后端服务：

```bash
uvicorn backend.proxy_server:app --host 0.0.0.0 --port 8000
```

这个方式关闭终端后服务会停止。长期运行推荐使用下面的 `systemd` 服务方式。

## 阿里云长期运行方式

推荐把后端部署成 `systemd` 服务，终端关闭后不会停止，服务器重启后也能自动拉起。

假设项目放在：

```bash
/opt/desktop_necoarc
```

创建服务用户：

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin necoarc
```

复制项目并设置权限：

```bash
sudo mkdir -p /opt/desktop_necoarc
sudo cp -r /你的项目路径/* /opt/desktop_necoarc/
sudo chown -R necoarc:necoarc /opt/desktop_necoarc
```

安装虚拟环境和依赖：

```bash
cd /opt/desktop_necoarc
sudo python3 -m venv .venv
sudo ./.venv/bin/python -m pip install -r backend/requirements.txt
sudo chown -R necoarc:necoarc /opt/desktop_necoarc/.venv
```

创建服务器环境变量文件：

```bash
sudo cp deploy/necoarc-proxy.env.example /etc/necoarc-proxy.env
sudo nano /etc/necoarc-proxy.env
```

把里面的占位值改成真实 API Key。

保护环境变量文件：

```bash
sudo chown root:root /etc/necoarc-proxy.env
sudo chmod 600 /etc/necoarc-proxy.env
```

安装 systemd 服务：

```bash
sudo cp deploy/necoarc-proxy.service /etc/systemd/system/necoarc-proxy.service
sudo systemctl daemon-reload
sudo systemctl enable necoarc-proxy
sudo systemctl start necoarc-proxy
```

查看运行状态：

```bash
sudo systemctl status necoarc-proxy
```

查看日志：

```bash
sudo journalctl -u necoarc-proxy -f
```

重启服务：

```bash
sudo systemctl restart necoarc-proxy
```

检查服务状态：

```bash
curl http://127.0.0.1:8000/health
```

返回中应看到：

```json
{
  "ok": true,
  "deepseek_configured": true,
  "xunfei_configured": true
}
```

阿里云安全组需要放行后端端口，例如 `8000`。正式使用建议通过 Nginx 反向代理到 HTTPS。

## 本地直连模式

如果你只是本地调试，也可以使用旧的直连模式：

```yaml
api_mode: direct
```

直连模式下，API 信息可以放在：

```text
plan/api.md
```

格式：

```md
#### 讯飞开放平台
APPID
你的讯飞APPID
APISecret
你的讯飞APISecret
APIKey
你的讯飞APIKey

#### deepseek
你的DeepSeek API Key
```

`plan/api.md` 已加入 `.gitignore`，不要提交到仓库。更推荐使用云端代理模式。

也可以使用环境变量覆盖：

```powershell
$env:DEEPSEEK_API_KEY="..."
$env:XUNFEI_APP_ID="..."
$env:XUNFEI_API_KEY="..."
$env:XUNFEI_API_SECRET="..."
```

## 配置文件

主要配置在：

```text
config.yaml
```

当前默认配置：

```yaml
window_width: 500
window_height: 260
always_on_top: true
character_image: plan/Neco-Arc_Remake.png
api_mode: proxy
proxy_base_url: http://127.0.0.1:8000
deepseek_base_url: https://api.deepseek.com
deepseek_model: deepseek-chat
xunfei_iat_url: wss://iat-api.xfyun.cn/v2/iat
xunfei_language: zh_cn
xunfei_accent: mandarin
sample_rate: 16000
temp_dir: temp
```

## 运行

```powershell
python main.py
```

如果希望后台启动窗口：

```powershell
pythonw main.py
```

## 使用方式

1. 打开程序后会显示桌面宠物窗口。
2. 点击 `录音` 开始说话。
3. 按钮变为 `停止` 后，再点击一次结束录音。
4. 程序进入 `处理中`，会先调用讯飞语音识别，再调用 DeepSeek。
5. 用户识别文本显示在左侧红色气泡。
6. DeepSeek 回复显示在右侧绿色气泡。
7. 下一轮开始时，上一次内容移动到上方区域。

## 常见问题

### Qt platform plugin 报错

项目在 `main.py` 里已经自动设置 PySide6 的 Qt 插件路径。如果仍然出现 Qt platform plugin 错误，可以先确认 PySide6 安装完整：

```powershell
python -c "import PySide6; print(PySide6.__file__)"
```

然后重新安装依赖：

```powershell
python -m pip install --force-reinstall PySide6
```

### 录音失败

请检查：

- Windows 是否允许当前 Python 使用麦克风
- 麦克风是否被其他软件占用
- 默认录音设备是否正常

### 语音识别失败

请检查：

- `plan/api.md` 中讯飞信息是否正确
- 讯飞接口是否开通在线语音听写服务
- 网络是否可访问讯飞 WebSocket 服务

### AI 回复失败

请检查：

- DeepSeek API Key 是否正确
- `deepseek_base_url` 是否为 `https://api.deepseek.com`
- 当前模型名是否可用

## 开发备注

- 窗口大小固定为 `500x260`
- 气泡大小不固定，会根据文本内容在窗口内扩展
- 当前没有全局快捷键，录音通过窗口内按钮切换
- 临时录音文件保存在 `temp/`
- 如果角色图片缺失，会显示内置占位角色
