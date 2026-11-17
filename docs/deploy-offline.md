# 单机离线部署说明

适用：药学部共用 PC，常无外网。全程不依赖外部网络。

## 1. 环境准备

- Python 3.10 及以上（建议 3.10/3.11）。
- 安装依赖（在有网机器下载 wheel 后离线拷贝，或用院内 PyPI 镜像）：
  ```bash
  pip install -r requirements.txt
  ```

## 2. 模型包放置

首次运行需以下离线模型包，按脚本获取后放到 `~/.cache/dmchange/models/`：

| 模型 | 作用 |
|---|---|
| paraformer-zh | 主识别 |
| fsmn-vad | 语音端点检测 |
| ct-punc | 标点恢复 |
| cam++ | 说话人分离 |

获取脚本（有网机器上执行，产出可拷贝的离线包）：

```bash
python scripts/fetch_offline_models.py --out ./offline-models
```

把 `offline-models/` 整个目录拷贝到目标 PC 的 `~/.cache/dmchange/models/`。

## 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填写真实端点与凭据（见 `docs/cli.md`）。凭据不得硬编码。

## 4. 启动自检

```bash
python -m dmchange doctor
```

缺模型包时 doctor 会明确列出缺哪个模型、脚本在哪、下一步做什么，不静默失败。

## 5. 使用

双击桌面图标或运行主程序 → 托盘常驻 → 主窗口「按住说话」→ 松手出草稿 → 确认 → 换人复核 → 写回主数据。

## 6. 无 GPU / 院内语音服务

本机 CPU 识别较慢时，设 `ASR_MODE=openai-compatible` 并配置 `ASR_BASE_URL`，走院内语音服务；切换失败会显式回落本机并提示。

## 7. 升级与回滚

- 升级：替换模型包目录后重跑 doctor；热词包可在界面回滚到旧版本。
- 回滚：保留最近一份模型包与目录快照；旧 change_id 标 superseded，审计链保留可回溯。
