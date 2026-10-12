# StudyPet AI

StudyPet 是一个 Windows 学习桌宠：把任务、专注计时、提醒、学习统计和 AI 陪伴放在一只可拖动的桌面伙伴里。

![StudyPet icon](resources/icon/studypet_icon.png)

## 功能

- 像素风桌宠：待机喝咖啡、专注读书、开心轻跳、趴桌休息。
- 左键随机问候；双击打开功能首页。
- 右键直达今日任务、专注计时、提醒、学习统计、AI 聊天和设置，也可切换桌宠状态。
- 任务、专注记录与提醒均保存在本机；提醒会置顶显示，须点击“我已处理”才会结束。
- 支持 OpenAI 兼容接口与 Ollama；API 密钥保存于 Windows 凭据管理器，不写入项目文件。
- 已提供 Windows 发布版和桌面启动快捷方式。

## 使用

开发环境：

```powershell
python -m pip install -r requirements.txt
python main.py
```

构建 Windows 发布版：

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

构建完成后，从 `release\StudyPet\StudyPet.exe` 启动。Windows 桌面快捷方式可指向此文件，并会使用 StudyPet 专属图标。

## 数据与隐私

程序会在运行位置创建 `data\` 文件夹：

```text
data/
  settings.json
  records/studypet.db
  logs/
```

开发运行时，它位于项目根目录；发布版运行时，它位于 `StudyPet.exe` 所在文件夹。该目录已被 `.gitignore` 排除，可以整体备份或迁移，但不应上传至 GitHub。

AI 配置中的服务商、地址与模型会写入本地设置；密钥通过系统凭据管理器保存。未配置 AI 时，其余功能仍可正常使用。

## 项目资源

- `resources/images/`：桌宠当前四种状态的透明 PNG 主姿势图。
- `resources/icon/studypet.ico`：Windows 程序、窗口和托盘使用的图标。
- `release/`、`build/`、`data/`：本地生成内容，均不会被 Git 跟踪。
