import json
import random
from pathlib import Path
from typing import Dict, List

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register


@register("astrbot_plugin_arknights_authorization", "codex", "明日方舟通行证盲盒互动插件", "1.0.0")
class ArknightsBlindBoxPlugin(Star):
    """明日方舟通行证盲盒互动插件。"""

    def __init__(self, context: Context):
        super().__init__(context)
        self.base_dir = Path(__file__).resolve().parent
        self.data_dir = self.base_dir / "data"
        self.config_path = self.data_dir / "box_config.json"
        self.state_path = self.data_dir / "pool_state.json"
        self.session_path = self.data_dir / "sessions.json"

        self.config: Dict[str, dict] = {}
        self.pool_state: Dict[str, List[str]] = {}
        self.sessions: Dict[str, str] = {}

    async def initialize(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_default_config()
        self._load_all()
        self._ensure_pools_initialized()
        logger.info("[arknights_blindbox] 插件初始化完成。")

    @filter.command("方舟盲盒")
    async def arknights_blindbox(self, event: AstrMessageEvent):
        """明日方舟通行证盲盒：列表/选择/开启。"""
        args = self._extract_command_args(event.message_str)
        if not args:
            yield event.plain_result(self._build_help_text())
            return

        action = args[0].lower()
        if action in {"列表", "list", "types"}:
            yield event.plain_result(self._build_category_list_text())
            return

        if action in {"选择", "select"}:
            if len(args) < 2:
                yield event.plain_result("请指定盲盒种类ID，例如：/方舟盲盒 选择 vc17")
                return
            category_id = args[1]
            if category_id not in self.config:
                yield event.plain_result(f"不存在种类 `{category_id}`。\n\n{self._build_category_list_text()}")
                return

            session_key = self._build_session_key(event)
            self.sessions[session_key] = category_id
            self._save_json(self.session_path, self.sessions)

            category = self.config[category_id]
            remain_count = len(self.pool_state.get(category_id, []))
            slots = int(category.get("slots", 0))
            tip_text = (
                f"你已选择【{category.get('name', category_id)}】\n"
                f"当前剩余奖品数：{remain_count}\n"
                f"可选盲盒序号：1 ~ {slots}\n"
                "请发送指令：/方舟盲盒 开 <序号>"
            )
            image = category.get("selection_image", "")
            for result in self._build_results_with_optional_image(event, tip_text, image):
                yield result
            return

        if action in {"开", "开启", "open"}:
            if len(args) < 2:
                yield event.plain_result("请提供序号，例如：/方舟盲盒 开 3")
                return
            if not args[1].isdigit():
                yield event.plain_result("序号必须是数字，例如：/方舟盲盒 开 3")
                return

            session_key = self._build_session_key(event)
            category_id = self.sessions.get(session_key)
            if not category_id:
                yield event.plain_result("你还没有选择盲盒种类，请先发送：/方舟盲盒 选择 <种类ID>")
                return
            if category_id not in self.config:
                yield event.plain_result("当前会话中的种类已失效，请重新选择。")
                return

            box_no = int(args[1])
            category = self.config[category_id]
            slots = int(category.get("slots", 0))
            if box_no < 1 or box_no > slots:
                yield event.plain_result(f"序号超出范围，请输入 1 ~ {slots} 之间的数字。")
                return

            if not self.pool_state.get(category_id):
                self.pool_state[category_id] = list(category.get("items", {}).keys())

            draw_pool = self.pool_state[category_id]
            selected_item_id = random.choice(draw_pool)
            draw_pool.remove(selected_item_id)
            self._save_json(self.state_path, self.pool_state)

            item = category.get("items", {}).get(selected_item_id, {})
            item_name = item.get("name", selected_item_id)
            item_image = item.get("image", "")

            remain_count = len(draw_pool)
            reset_tip = ""
            if remain_count == 0:
                self.pool_state[category_id] = list(category.get("items", {}).keys())
                self._save_json(self.state_path, self.pool_state)
                reset_tip = "\n奖池已抽空，已自动重置。"

            msg = (
                f"你选择了第 {box_no} 号盲盒，开启结果：\n"
                f"所属种类：{category.get('name', category_id)}\n"
                f"奖品名称：{item_name}\n"
                f"当前奖池剩余：{remain_count}{reset_tip}"
            )
            for result in self._build_results_with_optional_image(event, msg, item_image):
                yield result
            return

        if action in {"状态", "status"}:
            if len(args) < 2:
                session_key = self._build_session_key(event)
                category_id = self.sessions.get(session_key)
                if not category_id:
                    yield event.plain_result("请使用：/方舟盲盒 状态 <种类ID> 或先选择种类后再查看状态。")
                    return
            else:
                category_id = args[1]

            if category_id not in self.config:
                yield event.plain_result(f"不存在种类 `{category_id}`。")
                return

            remain_count = len(self.pool_state.get(category_id, []))
            total_count = len(self.config[category_id].get("items", {}))
            yield event.plain_result(
                f"【{self.config[category_id].get('name', category_id)}】奖池状态：{remain_count}/{total_count}"
            )
            return

        yield event.plain_result(self._build_help_text())

    def _extract_command_args(self, raw_message: str) -> List[str]:
        text = (raw_message or "").strip()
        if not text:
            return []
        parts = [p for p in text.split() if p]
        if not parts:
            return []

        first = parts[0].lstrip("/")
        if first == "方舟盲盒":
            return parts[1:]
        return parts

    def _build_help_text(self) -> str:
        return (
            "明日方舟通行证盲盒指令：\n"
            "1) /方舟盲盒 列表\n"
            "2) /方舟盲盒 选择 <种类ID>\n"
            "3) /方舟盲盒 开 <序号>\n"
            "4) /方舟盲盒 状态 [种类ID]"
        )

    def _build_category_list_text(self) -> str:
        if not self.config:
            return "当前没有可用的盲盒种类，请先配置 data/box_config.json"

        lines = ["可用盲盒种类："]
        for category_id, category in self.config.items():
            name = category.get("name", category_id)
            slots = category.get("slots", 0)
            total = len(category.get("items", {}))
            remain = len(self.pool_state.get(category_id, []))
            lines.append(f"- {category_id}: {name}（格子数: {slots}，奖池: {remain}/{total}）")
        lines.append("\n使用：/方舟盲盒 选择 <种类ID>")
        return "\n".join(lines)

    def _build_session_key(self, event: AstrMessageEvent) -> str:
        room = str(getattr(event, "group_id", "") or getattr(event, "session_id", "") or "private")
        user = str(getattr(event, "user_id", "") or getattr(event, "sender_id", "") or "unknown")
        return f"{room}:{user}"

    def _build_results_with_optional_image(self, event: AstrMessageEvent, text: str, image: str):
        image = (image or "").strip()
        if image and hasattr(event, "image_result"):
            # 为兼容不同适配器，图片与文字分开发送，确保文字说明不会丢失。
            return [event.image_result(image), event.plain_result(text)]
        if image:
            return [event.plain_result(f"{text}\n图片：{image}")]
        return [event.plain_result(text)]

    def _load_all(self):
        self.config = self._load_json(self.config_path, default={})
        self.pool_state = self._load_json(self.state_path, default={})
        self.sessions = self._load_json(self.session_path, default={})

    def _ensure_pools_initialized(self):
        changed = False
        for category_id, category in self.config.items():
            if category_id not in self.pool_state or not isinstance(self.pool_state[category_id], list):
                self.pool_state[category_id] = list(category.get("items", {}).keys())
                changed = True
        if changed:
            self._save_json(self.state_path, self.pool_state)

    def _ensure_default_config(self):
        if self.config_path.exists():
            return
        default_config = {
            "vc17": {
                "name": "2024音律联觉通行证盲盒",
                "slots": 14,
                "selection_image": "https://example.com/ak-vc17-selection.jpg",
                "items": {
                    "vc17-01": {
                        "name": "山 通行证卡套",
                        "image": "https://example.com/ak-vc17-01.jpg"
                    },
                    "vc17-02": {
                        "name": "W 通行证卡套",
                        "image": "https://example.com/ak-vc17-02.jpg"
                    },
                    "vc17-03": {
                        "name": "缪尔赛思 通行证卡套",
                        "image": "https://example.com/ak-vc17-03.jpg"
                    }
                }
            },
            "anniv": {
                "name": "周年系列通行证盲盒",
                "slots": 12,
                "selection_image": "https://example.com/ak-anniv-selection.jpg",
                "items": {
                    "anniv-01": {
                        "name": "阿米娅 通行证卡套",
                        "image": "https://example.com/ak-anniv-01.jpg"
                    },
                    "anniv-02": {
                        "name": "能天使 通行证卡套",
                        "image": "https://example.com/ak-anniv-02.jpg"
                    }
                }
            }
        }
        self._save_json(self.config_path, default_config)

    def _load_json(self, path: Path, default):
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as ex:
            logger.warning(f"[arknights_blindbox] 读取 {path.name} 失败：{ex}")
            return default

    def _save_json(self, path: Path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def terminate(self):
        self._save_json(self.state_path, self.pool_state)
        self._save_json(self.session_path, self.sessions)
        logger.info("[arknights_blindbox] 插件已卸载，状态已保存。")
