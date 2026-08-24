# 授权网页采集器（政务电脑 · 网页界面）

面向已经拿到采集许可的场景：在政务电脑上，对**已登录的业务网页**做自动采集。  
优先抽 DOM（表格、字段），页面是图片/扫描件/canvas 时再走 OCR。

方案边界、硬件选型和两条采集架构（软件 RPA / CH9329）见 **[docs/采集盒子方案总结.md](docs/采集盒子方案总结.md)**。

这不是燕云那种「通用黑盒反射 OS」，也不改对方系统、不碰库、不绕登录。

## 适用边界

- 有书面/系统授权，许可里写清操作人、目的、URL 范围、有效期
- 目标是浏览器里的网页（内网办事、查询、列表、详情）
- 账号由工作人员自己登录；采集器只挂到这台已登录的浏览器
- 默认只读：翻页、查询、抽取可以；回写业务数据默认拒绝

不要用它做未授权采集、键盘记录、注入或绕过认证。

## 在政务电脑上怎么跑

1. 工作人员用日常浏览器打开业务系统并完成登录（含 UK、短信、扫码）。
2. 用**同一用户目录**启动带调试端口的 Chrome / 国产 Chromium 内核浏览器：

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/gov-chrome-profile"
```

3. 把许可里的 `allowed_url_prefixes` 写成该内网地址前缀。
4. 按页面写任务 YAML：点查询、等表格、抽字段；扫描件用 `ocr_selector`。
5. 执行：

```bash
awc run --permit configs/permit.json --task configs/tasks/your_task.yaml --mode cdp --out ./out
```

没有 Playwright 时，可先用仓库自带的本地 HTML 样例验证抽取逻辑：

```bash
python -m pip install -e ".[dev]"
awc run --permit configs/permit.example.json --task configs/tasks/demo_gov_list.yaml --mode html --ocr-text "许可编号 DEMO-2026-001"
```

## 采集策略

| 页面情况 | 做法 |
|---|---|
| 普通 HTML 表格/表单 | CSS / XPath / `table` 策略，稳定且可对账 |
| 图片、扫描件、印章、套打 | 对元素截图后 OCR |
| 验证码、UK、短信 | 停下来等人，不要猜、不要破解 |
| 翻页 | `paginate` + `next_selector`，每页都记审计 |

## 项目结构

```
src/awcollector/   许可、审计、DOM 抽取、OCR 接口、流水线、CLI
configs/           许可样例、任务剧本
fixtures/          本地演示页（不是真实政务系统）
tests/             许可门禁、表格抽取、端到端 html 模式
```

## 下一步（上真实内网时再加）

- 为每一个业务系统写一个 adapter，不要做万能采集器
- 选择器自愈、关键字段人工抽检
- 离线 OCR（PaddleOCR / RapidOCR），数据不出政务网
- 把 agent 做成盒子：开机自检、看门狗、只上报已批准的内网接口
