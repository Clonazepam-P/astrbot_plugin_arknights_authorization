# astrbot_plugin_arknights_authorization

明日方舟通行证盲盒互动插件（AstrBot）。

## 本次变更重点

- **移除 `pool_state.json` 和 `box_config.json`**。
- 改为通过本地资源目录自动读取盲盒配置与奖品图片。
- 支持用户自行放图并按命名规则生效。

## 资源目录结构

插件会自动创建以下目录：

- `resources/数字盒/`
- `resources/特殊盒/`
- `resources/开出盲盒/`

实际持久化目录优先为：
`/opt/AstrBot/data/plugin_data/astrbot_plugin_arknights_authorization/resources`

## 命名规则（用户自行放图）

以 `数字盒` 为例，`特殊盒` 同理：

```text
resources/数字盒/
  num_vc17/                       # 种类ID（目录名）
    selection.jpg                 # 该种类选择引导图（可选）
    1-山.png                      # 奖品图：<序号>-<名称>.<后缀>
    2-W.jpg
    3-缪尔赛思.webp
```

### 规则说明

1. `num_vc17` 是种类 ID，指令里用它：`/方舟盲盒 选择 num_vc17`
2. 奖品文件名必须满足：`<序号>-<名称>.<jpg|jpeg|png|webp>` 或 `<序号>_<名称>.<...>`
3. 序号用于“可选序号”系统；名称用于开奖文案。
4. `selection.jpg/png`（或 `cover.jpg/png`）会作为该种类引导图。

## 指令

- `/方舟盲盒 注册`
- `/方舟盲盒 钱包`
- `/方舟盲盒 列表`
- `/方舟盲盒 选择 <种类ID>`
- `/方舟盲盒 开 <序号>`
- `/方舟盲盒 状态 [种类ID]`
- `/方舟盲盒 刷新 [种类ID]`
- `/方舟盲盒 管理员 列表|添加|移除|特殊定价`

## 数据持久化

- `data/blindbox.db`：SQLite（钱包 + 每个种类的剩余池/剩余序号状态）
- `data/sessions.json`：用户会话（当前选择的种类）
- `data/runtime_config.json`：价格、管理员等运行配置

> 重载和卸载插件不会清空以上数据。
