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

## API 配置

API 信息放在：

```text
plan/api.md
```

当前程序会从该文件读取：

- 讯飞开放平台 `APPID`
- 讯飞开放平台 `APIKey`
- 讯飞开放平台 `APISecret`
- DeepSeek API Key

`plan/api.md` 已加入 `.gitignore`，不要提交到仓库。

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
